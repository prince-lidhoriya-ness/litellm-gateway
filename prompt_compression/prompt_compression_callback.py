"""LiteLLM proxy hook: classify -> route -> compress every chat/completions request.

Registered in config.yaml as
    litellm_settings:
      callbacks: ["prompt_compression.prompt_compression_callback.prompt_compression_instance"]

Built on CustomLogger.async_pre_call_hook (litellm 1.106.0), which the proxy
awaits before the provider call and whose returned dict replaces the request.
Only data["messages"] is changed, so streaming and non-streaming responses
behave exactly as without the hook.

Logs never contain prompt text: only category, scores, model names, token
counts and ratio. The same summary is written to the request metadata under
"prompt_compression" and "spend_logs_metadata" so it shows up in LiteLLM logs.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# LiteLLM loads this file by path, so make the package importable by name.
_GATEWAY_DIR = str(Path(__file__).resolve().parent.parent)
if _GATEWAY_DIR not in sys.path:
    sys.path.insert(0, _GATEWAY_DIR)

from fastapi import HTTPException  # noqa: E402
from litellm.integrations.custom_logger import CustomLogger  # noqa: E402

from prompt_compression.pipeline import PromptPipeline  # noqa: E402
from prompt_compression.settings import PipelineSettings  # noqa: E402

logger = logging.getLogger("prompt_compression")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(os.getenv("PROMPT_COMPRESSION_LOG_LEVEL", "INFO").upper())
    logger.propagate = False

CHAT_CALL_TYPES = frozenset({"completion", "acompletion"})
METADATA_KEY = "prompt_compression"


def _metadata_dicts(data: dict) -> list[dict]:
    return [data[key] for key in ("metadata", "litellm_metadata") if isinstance(data.get(key), dict)]


def _opted_out(data: dict) -> bool:
    """Per-request opt-out: metadata {"prompt_compression": false} or {"disable_prompt_compression": true}."""
    for metadata in _metadata_dicts(data):
        if metadata.get(METADATA_KEY) is False or str(metadata.get(METADATA_KEY)).lower() == "false":
            return True
        if metadata.get("disable_prompt_compression") in (True, "true", "True"):
            return True
    return False


def _write_metadata(data: dict, summary: dict) -> None:
    key = "litellm_metadata" if "litellm_metadata" in data and "metadata" not in data else "metadata"
    metadata = data.get(key)
    if not isinstance(metadata, dict):
        metadata = {}
        data[key] = metadata
    metadata[METADATA_KEY] = summary
    # spend_logs_metadata is one of the StandardLoggingMetadata keys, so it reaches spend logs and log callbacks.
    spend_logs_metadata = dict(metadata.get("spend_logs_metadata") or {})
    spend_logs_metadata[METADATA_KEY] = summary
    metadata["spend_logs_metadata"] = spend_logs_metadata


class PromptCompressionCallback(CustomLogger):
    def __init__(self, pipeline: PromptPipeline | None = None, settings: PipelineSettings | None = None):
        super().__init__()
        self.settings = settings or PipelineSettings.from_env()
        self._pipeline = pipeline
        self._pipeline_error: Exception | None = None
        if self.settings.enabled and self.settings.eager_load and pipeline is None:
            self._build_pipeline(load=True)

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

    async def async_pre_call_hook(self, user_api_key_dict, cache, data: dict, call_type):
        if call_type not in CHAT_CALL_TYPES or not isinstance(data.get("messages"), list):
            return data
        if not self.settings.enabled:
            return data
        if _opted_out(data):
            _write_metadata(data, {"status": "skipped", "reason": "request_opt_out"})
            logger.info("prompt compression skipped: per-request opt-out")
            return data

        pipeline = self._build_pipeline(load=False)
        if pipeline is None:
            return self._fail(data, "pipeline init failed", self._pipeline_error)

        try:
            new_messages, report = await asyncio.wait_for(
                asyncio.to_thread(pipeline.process, data["messages"]), timeout=self.settings.timeout_s
            )
        except asyncio.TimeoutError as exc:
            return self._fail(data, f"timeout after {self.settings.timeout_s}s", exc)
        except Exception as exc:
            return self._fail(data, "pipeline error", exc)

        summary = {"status": "ok", **report.as_metadata()}
        data["messages"] = new_messages
        _write_metadata(data, summary)
        logger.info(
            "prompt compression: category=%s tokens_before=%d tokens_after=%d ratio=%.3f elapsed_ms=%.1f "
            "classifier=%s messages=%s",
            report.request_category, report.tokens_before, report.tokens_after, report.ratio, report.elapsed_ms,
            report.classifier_model,
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
