"""LiteLLM proxy hook: [redact] -> gate -> segment and classify -> route -> actions -> reassemble, for every chat request.

This file is the redaction guardrail, the gate (opt-out, size, admission, timeout) and the "Fail open" branch: any
timeout or pipeline error sends the original prompt (or rejects the request with HTTP 503 when
PROMPT_COMPRESSION_FAIL_MODE=closed). The stages after the gate are in pipeline.py.

Registered in config.yaml as
    litellm_settings:
      callbacks: ["prompt_compression.prompt_compression_callback.prompt_compression_instance"]

Built on CustomLogger.async_pre_call_hook (litellm 1.106.0), which the proxy awaits before the provider call and whose
returned dict replaces the request. Only data["messages"] is changed, so streaming and non-streaming responses behave
exactly as without the hook.

Order of work for one request (PROJECT_AUDIT_REPORT.md, F-02/F-03/F-04/F-15S):
  1. redaction guardrail (REDACT_SENSITIVE=true): every message and role, before the opt-out and the size gate, in shadow
     mode too; an error rejects the request (503) whatever the fail mode, because the guardrail must not fail open
  2. cheap gate checks on the event loop (call type, enabled, opt-out)
  3. admission: at most PROMPT_COMPRESSION_MAX_CONCURRENCY pipelines per worker; a request that finds them all busy is
     sent unchanged ("skipped: busy") instead of queueing into a timeout
  4. in a bounded worker pool: token-count gate (below_min_size / too_large), then the pipeline under a deadline of 90%
     of PROMPT_COMPRESSION_TIMEOUT_S. Model work checks the deadline, so a request that runs out of time stops at its
     next model call instead of running on in the background and holding the model locks
  5. asyncio.wait_for(PROMPT_COMPRESSION_TIMEOUT_S) stays as the backstop

Logs never contain prompt text: only category, scores, model names, token counts and ratio. The summary is written to
the request metadata under "prompt_compression"; a copy with only the latest PROMPT_COMPRESSION_SPEND_LOG_MESSAGES
per-message entries goes to "spend_logs_metadata" so spend-log rows stay bounded.
"""

import asyncio
import concurrent.futures
import contextvars
import logging
import os
import sys
import threading
from pathlib import Path

# LiteLLM loads this file by path, so make the package importable by name.
_GATEWAY_DIR = str(Path(__file__).resolve().parent.parent)
if _GATEWAY_DIR not in sys.path:
    sys.path.insert(0, _GATEWAY_DIR)

from fastapi import HTTPException  # noqa: E402
from litellm.integrations.custom_logger import CustomLogger  # noqa: E402

from prompt_compression import gate  # noqa: E402
from prompt_compression.deadline import Deadline, DeadlineExceeded  # noqa: E402
from prompt_compression.gate import CHAT_CALL_TYPES, METADATA_KEY  # noqa: E402,F401  (re-exported for observability)
from prompt_compression.pipeline import PromptPipeline  # noqa: E402
from prompt_compression.redaction import redact_messages  # noqa: E402
from prompt_compression.settings import PipelineSettings  # noqa: E402

REDACTION_KEY = "prompt_redaction"
# Share of the timeout the pipeline's own deadline gets: it then finishes (partly compressed) before the backstop fires.
_DEADLINE_SHARE = 0.9

logger = logging.getLogger("prompt_compression")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(os.getenv("PROMPT_COMPRESSION_LOG_LEVEL", "INFO").upper())
    logger.propagate = False


def _metadata_dict(data: dict) -> dict:
    key = "litellm_metadata" if "litellm_metadata" in data and "metadata" not in data else "metadata"
    metadata = data.get(key)
    if not isinstance(metadata, dict):
        metadata = {}
        data[key] = metadata
    return metadata


def _write_metadata(data: dict, summary: dict, key: str = METADATA_KEY, spend_log_messages: int = 8) -> None:
    metadata = _metadata_dict(data)
    metadata[key] = summary
    # spend_logs_metadata is one of the StandardLoggingMetadata keys, so it reaches spend logs and log callbacks. It gets
    # the request-level figures plus the latest `spend_log_messages` per-message entries: the full list grows with the
    # conversation and would bloat every spend row.
    spend_logs_metadata = dict(metadata.get("spend_logs_metadata") or {})
    spend_summary = dict(summary)
    if isinstance(summary.get("messages"), list):
        entries = summary["messages"]
        kept = entries[-spend_log_messages:] if spend_log_messages > 0 else []
        spend_summary["messages"] = kept
        if len(kept) < len(entries):
            spend_summary["messages_omitted"] = len(entries) - len(kept)
    spend_logs_metadata[key] = spend_summary
    metadata["spend_logs_metadata"] = spend_logs_metadata


def _protected_indexes(data: dict) -> frozenset:
    """Message indexes the context-engineering stage (context_engineering/callback.py, which runs before this hook)
    asks to keep verbatim: its compaction summary. Missing or malformed hints mean nothing is protected."""
    for metadata in gate.metadata_dicts(data):
        hints = (metadata.get("context_engineering") or {}).get("hints") if isinstance(
            metadata.get("context_engineering"), dict) else None
        if isinstance(hints, dict) and isinstance(hints.get("protected_indexes"), list):
            return frozenset(i for i in hints["protected_indexes"] if isinstance(i, int) and not isinstance(i, bool))
    return frozenset()


class PromptCompressionCallback(CustomLogger):
    def __init__(self, pipeline: PromptPipeline | None = None, settings: PipelineSettings | None = None):
        super().__init__()
        self.settings = settings or PipelineSettings.from_env()
        self._pipeline = pipeline
        self._pipeline_error: Exception | None = None
        # Pipelines run in this pool, never in asyncio's shared default executor. `_in_flight` counts pipelines whose
        # worker thread has not finished yet (a timed-out one still counts until it stops), which is what admission
        # control compares with max_concurrency.
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.settings.max_concurrency, thread_name_prefix="prompt-pipeline"
        )
        self._in_flight = 0
        self._in_flight_lock = threading.Lock()
        if self.settings.enabled and self.settings.eager_load and pipeline is None:
            self._build_pipeline(load=True)

    @property
    def in_flight(self) -> int:
        return self._in_flight

    def _build_pipeline(self, load: bool) -> PromptPipeline | None:
        if self._pipeline is None and self._pipeline_error is None:
            try:
                self._pipeline = PromptPipeline(settings=self.settings)
            except Exception as exc:
                self._pipeline_error = exc
                logger.warning("prompt compression disabled: pipeline init failed error=%s", type(exc).__name__)
                return None
        if load and self._pipeline is not None:
            try:
                self._pipeline.load()
            except Exception as exc:
                # Remembered by the classifier/compressor; requests then follow the fail mode.
                logger.warning(
                    "prompt compression model load failed at startup; requests will fail %s: error=%s: %s",
                    self.settings.fail_mode, type(exc).__name__, str(exc)[:200],
                )
        return self._pipeline

    def _fail(self, data: dict, reason: str, exc: BaseException | None) -> dict:
        detail = f"{reason}: {type(exc).__name__}" if exc is not None else reason
        _write_metadata(data, {"status": "error", "error": detail, "fail_mode": self.settings.fail_mode})
        if self.settings.fail_mode == "closed":
            logger.error("prompt compression failed, rejecting request (fail_mode=closed): %s", detail)
            raise HTTPException(status_code=503, detail={"error": f"prompt compression unavailable: {reason}"})
        logger.warning("prompt compression failed, sending original prompt (fail_mode=open): %s", detail)
        return data

    def _skip(self, data: dict, reason: str) -> dict:
        _write_metadata(data, {"status": "skipped", "reason": reason})
        logger.info("prompt compression skipped: %s", reason)
        return data

    # ---- redaction guardrail -------------------------------------------------------------------------------------

    async def _redact(self, data: dict) -> None:
        try:
            messages, count, names = await asyncio.wait_for(
                asyncio.to_thread(redact_messages, data["messages"]), timeout=self.settings.timeout_s
            )
        except Exception as exc:
            # Never fail open: an unredacted prompt is exactly what this guardrail exists to stop.
            _write_metadata(data, {"status": "error", "error": f"redaction failed: {type(exc).__name__}"}, REDACTION_KEY)
            logger.error("redaction failed, rejecting request: error=%s", type(exc).__name__)
            raise HTTPException(status_code=503, detail={"error": "sensitive-data redaction unavailable"})
        data["messages"] = messages
        _write_metadata(data, {"status": "ok", "redactions": count, "rules": names}, REDACTION_KEY)
        if count:
            logger.info("redaction: spans=%d rules=%s", count, names)

    # ---- admission -----------------------------------------------------------------------------------------------

    def _admit(self) -> bool:
        with self._in_flight_lock:
            if self._in_flight >= self.settings.max_concurrency:
                return False
            self._in_flight += 1
            return True

    def _release(self, _future=None) -> None:
        with self._in_flight_lock:
            self._in_flight -= 1

    def _work(self, pipeline: PromptPipeline, messages: list, deadline: Deadline, protected: frozenset = frozenset()):
        """Runs in the worker pool: the token-count gate, then the pipeline."""
        decision = gate.size_check(messages, self.settings)
        if not decision.allow:
            return decision, None, None
        if protected:
            new_messages, report = pipeline.process(messages, deadline=deadline, protected=protected)
        else:
            new_messages, report = pipeline.process(messages, deadline=deadline)
        return decision, new_messages, report

    # ---- the hook ------------------------------------------------------------------------------------------------

    async def async_pre_call_hook(self, user_api_key_dict, cache, data: dict, call_type):
        if not gate.is_chat(data, call_type):
            return data
        # Stage 0, the redaction guardrail: independent of the compression switch, the opt-out and the size gate.
        if self.settings.redact_sensitive:
            await self._redact(data)

        # Stage 1, the gate: disabled, per-request opt-out (the token checks run in the worker, below).
        decision = gate.check(data, call_type, self.settings, count_tokens=False)
        if not decision.allow:
            if not decision.silent:
                return self._skip(data, decision.reason)
            return data

        pipeline = self._build_pipeline(load=False)
        if pipeline is None:
            return self._fail(data, "pipeline init failed", self._pipeline_error)

        if not self._admit():
            return self._skip(data, "busy")
        deadline = Deadline(self.settings.timeout_s * _DEADLINE_SHARE)
        context = contextvars.copy_context()          # trace context and request id reach the worker thread
        try:
            future = self._executor.submit(context.run, self._work, pipeline, data["messages"], deadline,
                                           _protected_indexes(data))
        except BaseException:
            self._release()
            raise
        future.add_done_callback(self._release)
        try:
            decision, new_messages, report = await asyncio.wait_for(
                asyncio.wrap_future(future), timeout=self.settings.timeout_s
            )
        except (asyncio.TimeoutError, DeadlineExceeded) as exc:
            return self._fail(data, f"timeout after {self.settings.timeout_s}s", exc)
        except Exception as exc:
            return self._fail(data, "pipeline error", exc)

        if not decision.allow:
            return self._skip(data, decision.reason)

        # Shadow mode runs the whole pipeline and reports what it would have sent, but the provider gets the original
        # prompt. tokens_after in the summary is then the hypothetical figure, and status is "shadow", not "ok".
        shadow = self.settings.mode == "shadow"
        summary = {"status": "shadow" if shadow else "ok", **report.as_metadata()}
        if not shadow:
            data["messages"] = new_messages
        _write_metadata(data, summary, spend_log_messages=self.settings.spend_log_messages)
        logger.info(
            "prompt compression%s: category=%s intent=%s tokens_before=%d tokens_after=%d ratio=%.3f elapsed_ms=%.1f "
            "compress_calls=%d stopped=%s classifier=%s messages=%s",
            " (shadow, original sent)" if shadow else "",
            report.request_category, report.intent, report.tokens_before, report.tokens_after, report.ratio,
            report.elapsed_ms, report.compress_calls, report.compress_stopped, report.classifier_model,
            [
                {k: m[k] for k in ("index", "role", "category", "score", "source", "rule_hits", "action") if k in m}
                for m in report.messages
            ],
        )
        return data

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        # Confirms the summary survived into LiteLLM's standard logging payload (no prompt text).
        payload = kwargs.get("standard_logging_object") or {}
        spend_logs_metadata = (payload.get("metadata") or {}).get("spend_logs_metadata") or {}
        summary = spend_logs_metadata.get(METADATA_KEY)
        if summary:
            logger.info(
                "litellm log payload: model=%s stream=%s prompt_compression.category=%s compression_ratio=%s status=%s",
                payload.get("model"), payload.get("stream"), summary.get("category"),
                summary.get("compression_ratio"), summary.get("status"),
            )


_instance: PromptCompressionCallback | None = None


def __getattr__(name: str):
    # Built on first access (LiteLLM's getattr on the config path), not at import, so a
    # wrapping callback such as observability.observed_callback can import this module
    # without loading the models a second time.
    global _instance
    if name == "prompt_compression_instance":
        if _instance is None:
            _instance = PromptCompressionCallback()
        return _instance
    raise AttributeError(name)
