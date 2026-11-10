"""LiteLLM proxy hook for the context-engineering stage. Registered before the prompt-compression hook:

    litellm_settings:
      callbacks: [..., "context_engineering.callback.context_engineering_instance",
                  "observability.observed_callback.observed_prompt_compression_instance"]

LiteLLM awaits each callback's async_pre_call_hook in list order and passes the returned dict on, so the compression
stage receives the request this stage produced, together with its hints in metadata["context_engineering"]["hints"].

Gate: not a chat call / disabled (silent), per-request opt-out (metadata {"context_engineering": false} or
{"disable_context_engineering": true}), fewer than CONTEXT_ENGINEERING_MIN_TOKENS estimated tokens.
Fail mode: a timeout or an error forwards the original request (open) or rejects it with HTTP 503 (closed).
Shadow mode: everything runs and is reported, the original request is forwarded and no hints are written, so the
compression stage behaves exactly as without this stage.
Logs and metadata never contain prompt text: counts, refs, indexes, category names and decisions only.
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

# LiteLLM loads this file by path, so make the gateway packages importable by name.
_GATEWAY_DIR = str(Path(__file__).resolve().parent.parent)
if _GATEWAY_DIR not in sys.path:
    sys.path.insert(0, _GATEWAY_DIR)

from fastapi import HTTPException  # noqa: E402
from litellm.integrations.custom_logger import CustomLogger  # noqa: E402

from context_engineering import metrics as m  # noqa: E402
from context_engineering import tokens as tk  # noqa: E402
from context_engineering.engine import ContextEngine  # noqa: E402
from context_engineering.settings import ContextSettings  # noqa: E402

logger = logging.getLogger("context_engineering")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(os.getenv("CONTEXT_ENGINEERING_LOG_LEVEL", "INFO").upper())
    logger.propagate = False

CHAT_CALL_TYPES = frozenset({"completion", "acompletion"})
METADATA_KEY = "context_engineering"


def _metadata(data: dict) -> dict:
    key = "litellm_metadata" if "litellm_metadata" in data and "metadata" not in data else "metadata"
    metadata = data.get(key)
    if not isinstance(metadata, dict):
        metadata = {}
        data[key] = metadata
    return metadata


def opted_out(data: dict) -> bool:
    for key in ("metadata", "litellm_metadata"):
        metadata = data.get(key)
        if not isinstance(metadata, dict):
            continue
        value = metadata.get(METADATA_KEY)
        if value is False or str(value).lower() == "false":
            return True
        if metadata.get("disable_context_engineering") in (True, "true", "True"):
            return True
    return False


SPEND_LOG_RECORDS = 16


def write_metadata(data: dict, summary: dict) -> None:
    metadata = _metadata(data)
    metadata[METADATA_KEY] = summary
    # spend_logs_metadata reaches LiteLLM spend logs and every logging callback (the summary holds no prompt text).
    # Per-item lists grow with the conversation, so the spend-log copy keeps the latest SPEND_LOG_RECORDS of each.
    spend_summary = dict(summary)
    for key in ("masked", "history", "decisions"):
        items = summary.get(key)
        if isinstance(items, list) and len(items) > SPEND_LOG_RECORDS:
            spend_summary[key] = items[-SPEND_LOG_RECORDS:]
            spend_summary[f"{key}_omitted"] = len(items) - SPEND_LOG_RECORDS
    spend_logs_metadata = dict(metadata.get("spend_logs_metadata") or {})
    spend_logs_metadata[METADATA_KEY] = spend_summary
    metadata["spend_logs_metadata"] = spend_logs_metadata


def redaction_enabled() -> bool:
    """The compression stage's redaction guardrail switch (REDACT_SENSITIVE). When it is on, this stage redacts too,
    before anything is stored or copied into a stub or summary; the guardrail then finds nothing left to redact."""
    return (os.getenv("REDACT_SENSITIVE") or "").strip().lower() in ("1", "true", "yes", "on")


def _provider_label(data: dict) -> str:
    try:
        import litellm

        return str(litellm.get_llm_provider(str(data.get("model") or ""))[1] or "unknown")[:40]
    except Exception:
        return "unknown"


class ContextEngineeringCallback(CustomLogger):
    def __init__(self, engine: ContextEngine | None = None, settings: ContextSettings | None = None):
        super().__init__()
        self.settings = settings or (engine.settings if engine is not None else ContextSettings.from_env())
        self._engine = engine
        self._engine_error: Exception | None = None

    @property
    def engine(self) -> ContextEngine | None:
        if self._engine is None and self._engine_error is None:
            try:
                self._engine = ContextEngine(settings=self.settings)
            except Exception as exc:
                self._engine_error = exc
                logger.warning("context engineering disabled: engine init failed error=%s", type(exc).__name__)
        return self._engine

    def _fail(self, data: dict, reason: str, exc: BaseException | None) -> dict:
        detail = f"{reason}: {type(exc).__name__}" if exc is not None else reason
        write_metadata(data, {"status": "error", "error": detail, "fail_mode": self.settings.fail_mode})
        m.FAILURES.labels(self.settings.fail_mode, reason.split(" ")[0]).inc()
        m.REQUESTS.labels("error", "none").inc()
        if self.settings.fail_mode == "closed":
            logger.error("context engineering failed, rejecting request (fail_mode=closed): %s", detail)
            raise HTTPException(status_code=503, detail={"error": f"context engineering unavailable: {reason}"})
        logger.warning("context engineering failed, sending the original request (fail_mode=open): %s", detail)
        return data

    @staticmethod
    def _work(engine: ContextEngine, messages: list, model: str, tools, max_tokens, data: dict):
        """Runs in a worker thread: optional redaction (see redaction_enabled), then the engine."""
        if redaction_enabled():
            from prompt_compression.redaction import redact_messages

            messages, _, _ = redact_messages(messages)
        return engine.process(messages, model, tools, max_tokens, data)

    async def async_pre_call_hook(self, user_api_key_dict, cache, data: dict, call_type):
        if call_type not in CHAT_CALL_TYPES or not isinstance(data.get("messages"), list) or not self.settings.enabled:
            return data
        if opted_out(data):
            write_metadata(data, {"status": "skipped", "reason": "request_opt_out"})
            return data
        estimate = tk.messages_tokens(data["messages"]) + tk.tools_tokens(data.get("tools"))
        if estimate < self.settings.min_tokens:
            write_metadata(data, {"status": "skipped", "reason": "below_min_size", "tokens": estimate})
            m.REQUESTS.labels("skipped", "none").inc()
            return data
        engine = self.engine
        if engine is None:
            return self._fail(data, "engine init failed", self._engine_error)

        started = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    self._work, engine, data["messages"], str(data.get("model") or ""), data.get("tools"),
                    data.get("max_tokens") or data.get("max_completion_tokens"), data,
                ),
                timeout=self.settings.timeout_s,
            )
        except asyncio.TimeoutError as exc:
            return self._fail(data, f"timeout after {self.settings.timeout_s}s", exc)
        except Exception as exc:
            return self._fail(data, "engine error", exc)

        report = result.report
        shadow = self.settings.mode == "shadow"
        report.status = "shadow" if shadow else "ok"
        if not shadow:
            data["messages"] = result.messages
            if result.tools is not data.get("tools") and result.tools is not None:
                data["tools"] = result.tools
            if result.breakpoints and not data.get("cache_control_injection_points"):
                data["cache_control_injection_points"] = result.breakpoints
                m.BREAKPOINTS.labels(_provider_label(data)).inc()
            for sha, source in result.pending_summaries:
                if engine.summarizer is not None:
                    engine.summarizer.schedule(sha, source)
        else:
            report.hints = {}
        summary = report.as_metadata()
        write_metadata(data, summary)
        self._record(report, shadow, time.perf_counter() - started)
        logger.info(
            "context engineering%s: tokens_before=%d tokens_after=%d utilization=%.2f->%.2f pressure=%s caching=%s "
            "masked=%d history=%s summary=%s stages_failed=%s elapsed_ms=%.1f",
            " (shadow, original sent)" if shadow else "", report.tokens_before, report.tokens_after,
            report.utilization_before, report.utilization_after, report.pressure, report.caching, len(report.masked),
            [h.action for h in report.history], report.summary_source or "-", report.stages_failed, report.elapsed_ms,
        )
        return data

    def _record(self, report, shadow: bool, seconds: float) -> None:
        m.REQUESTS.labels(report.status, report.pressure).inc()
        m.DURATION.labels(report.status).observe(seconds)
        m.UTILIZATION.labels("before").observe(report.utilization_before)
        m.UTILIZATION.labels("after").observe(report.utilization_after)
        for pattern in report.volatile_prefix:
            m.VOLATILE_PREFIX.labels(pattern).inc()
        for failed in report.stages_failed:
            m.STAGE_UNDONE.labels(failed.split(":")[0]).inc()
        saved_mask = sum(r.tokens_before - r.tokens_after for r in report.masked)
        saved_history = max(0, report.tokens_saved - saved_mask)
        counter = m.SHADOW_TOKENS_SAVED if shadow else m.TOKENS_SAVED
        if saved_mask:
            counter.labels("masking").inc(saved_mask)
        if saved_history:
            counter.labels("history").inc(saved_history)
        if not shadow:
            for category, tokens in report.by_category_before.items():
                m.TOKENS_BEFORE.labels(category).inc(tokens)
            for category, tokens in report.by_category_after.items():
                m.TOKENS_AFTER.labels(category).inc(tokens)
        for record in report.masked:
            m.MASKED.labels(record.reason).inc()
        for record in report.history:
            m.HISTORY_TURNS.labels(record.action).inc()

    # ----- provider result: prompt-cache reads/writes and tokenizer calibration -----------------------------------

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            self._log_usage(kwargs, response_obj)
        except Exception as exc:     # never let accounting break the response path
            logger.debug("context engineering usage capture failed: %s", type(exc).__name__)

    def _log_usage(self, kwargs: dict, response_obj) -> None:
        payload = kwargs.get("standard_logging_object") or {}
        metadata = (payload.get("metadata") or {}).get("spend_logs_metadata") or {}
        summary = metadata.get(METADATA_KEY) or {}
        if not summary or summary.get("status") not in ("ok", "shadow"):
            return
        usage = getattr(response_obj, "usage", None)
        if usage is None and isinstance(response_obj, dict):
            usage = response_obj.get("usage")
        if usage is None:
            return
        provider = str(payload.get("custom_llm_provider") or "unknown")[:40]
        prompt_tokens = _get(usage, "prompt_tokens") or 0
        details = _get(usage, "prompt_tokens_details")
        cached = _get(details, "cached_tokens") or _get(usage, "cache_read_input_tokens") or 0
        written = _get(usage, "cache_creation_input_tokens") or 0
        if prompt_tokens:
            m.PROVIDER_PROMPT_TOKENS.labels(provider).inc(prompt_tokens)
        if cached:
            m.PROVIDER_CACHED_TOKENS.labels(provider).inc(cached)
        if written:
            m.PROVIDER_CACHE_WRITE_TOKENS.labels(provider).inc(written)
        # Calibrate against what was actually sent: this stage's estimate minus what compression then removed.
        estimate = int(summary.get("tokens_after") or 0)
        compression = metadata.get("prompt_compression") or {}
        if compression.get("status") == "ok":
            estimate -= max(0, int(compression.get("tokens_before") or 0) - int(compression.get("tokens_after") or 0))
        if summary.get("status") == "ok" and estimate > 0 and prompt_tokens:
            tk.CALIBRATION.record(summary.get("model") or "", estimate, int(prompt_tokens))
        logger.info("context engineering usage: provider=%s prompt_tokens=%s cached_tokens=%s cache_write_tokens=%s",
                    provider, prompt_tokens, cached, written)


def _get(obj, name):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


_instance: ContextEngineeringCallback | None = None


def __getattr__(name: str):
    # Built on first access (LiteLLM's getattr on the config path), not at import.
    global _instance
    if name == "context_engineering_instance":
        if _instance is None:
            _instance = ContextEngineeringCallback()
        return _instance
    raise AttributeError(name)
