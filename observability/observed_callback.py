"""LiteLLM proxy callback: the prompt_compression hook plus observability.

Registered in litellm_config.yaml instead of the plain hook:
    litellm_settings:
      callbacks: [..., "observability.observed_callback.observed_prompt_compression_instance"]

Behaviour is the parent's (classify -> route -> compress, fail open/closed); this
subclass only observes it:
  - one `prompt.pipeline` span per request, child of LiteLLM's OTel V2 server span,
    with the pipeline's own `prompt.classify` / `prompt.route` / `prompt.compress`
    spans under it; LiteLLM adds the provider-call span to the same trace
  - prompt_pipeline_* Prometheus metrics (observability/metrics.py)
  - JSON log events with trace_id and request_id (observability/logs.py)
  - Langfuse attribution through request metadata (hashed user id, category tag)
No message text is exported: only salted hashes, lengths, token counts and labels.
"""

import logging
import sys
import time
from pathlib import Path

# LiteLLM loads this file by path, so make the gateway packages importable by name.
_GATEWAY_DIR = str(Path(__file__).resolve().parent.parent)
if _GATEWAY_DIR not in sys.path:
    sys.path.insert(0, _GATEWAY_DIR)

from fastapi import HTTPException  # noqa: E402
from opentelemetry import trace  # noqa: E402
from opentelemetry.trace import Status, StatusCode  # noqa: E402

from observability import metrics as m  # noqa: E402
from observability.logs import configure_logging, event, request_id_var  # noqa: E402
from observability.privacy import fingerprint, hash_id, scrub  # noqa: E402
from observability.settings import ObservabilitySettings  # noqa: E402
from prompt_compression.pipeline import _text_parts  # noqa: E402
from prompt_compression.sensitivity import GENERAL_CATEGORY  # noqa: E402
from prompt_compression.texts import count_tokens  # noqa: E402
from prompt_compression.prompt_compression_callback import (  # noqa: E402
    CHAT_CALL_TYPES,
    METADATA_KEY,
    PromptCompressionCallback,
)

logger = logging.getLogger("observability")
tracer = trace.get_tracer("observability")

# Only these categories may ever have text attached, and only with OBS_CAPTURE_TEXT=true.
TEXT_CAPTURE_LABELS = frozenset({GENERAL_CATEGORY})
MODEL_SOURCES = frozenset({"model"})


def failure_reason(error: str) -> str:
    """Map the parent's error string to a low-cardinality reason."""
    error = error or ""
    if error.startswith("timeout"):
        return "timeout"
    if error.startswith("pipeline init failed"):
        return "init_failed"
    if "ClassifierUnavailable" in error:
        return "classifier_unavailable"
    return "pipeline_error"


def _metadata(data: dict) -> dict:
    for key in ("metadata", "litellm_metadata"):
        if isinstance(data.get(key), dict):
            return data[key]
    data["metadata"] = {}
    return data["metadata"]


def _span_ids(span) -> tuple:
    context = span.get_span_context() if span is not None else None
    if context is None or not context.is_valid:
        return None, None
    return format(context.trace_id, "032x"), format(context.span_id, "016x")


class ObservedPromptCompressionCallback(PromptCompressionCallback):
    def __init__(self, pipeline=None, settings=None, obs_settings: ObservabilitySettings | None = None):
        self.obs = obs_settings or ObservabilitySettings.from_env()
        if self.obs.enabled:
            configure_logging(self.obs)
            if not self.obs.hash_salt:
                event(logger, "observability.config_warning", logging.WARNING,
                      detail="OBS_HASH_SALT is empty; user and message hashes are unsalted")
        super().__init__(pipeline=pipeline, settings=settings)

    # ----- startup -------------------------------------------------------------------

    def _build_pipeline(self, load: bool):
        if not self.obs.enabled:
            return super()._build_pipeline(load)
        pipeline = super()._build_pipeline(load=False)
        if load and pipeline is not None:
            # Same loads as the parent, timed per component.
            for component, target in (("classifier", pipeline.detector), ("compressor", pipeline.compressor)):
                started = time.perf_counter()
                try:
                    target.load()
                except Exception as exc:
                    m.MODEL_LOADED.labels(component).set(0)
                    event(logger, "model.load_failed", logging.WARNING, component=component,
                          error_class=type(exc).__name__, fail_mode=self.settings.fail_mode)
                    continue
                seconds = round(time.perf_counter() - started, 3)
                m.MODEL_LOAD_SECONDS.labels(component).set(seconds)
                m.MODEL_LOADED.labels(component).set(1)
                event(logger, "model.loaded", component=component, model=target.model_name, load_seconds=seconds)
        return pipeline

    # ----- request -------------------------------------------------------------------

    async def async_pre_call_hook(self, user_api_key_dict, cache, data: dict, call_type):
        if not self.obs.enabled or call_type not in CHAT_CALL_TYPES or not isinstance(data.get("messages"), list):
            return await super().async_pre_call_hook(user_api_key_dict, cache, data, call_type)

        token = request_id_var.set(data.get("litellm_call_id"))
        model = m.bounded_model(data.get("model"), self.obs.max_model_label_values)
        originals = {
            index: "\n".join(text for _, text in _text_parts(message))
            for index, message in enumerate(data["messages"])
            if _text_parts(message)
        }
        # Under OTel V2 the server span is already current; otherwise attach to the auth span.
        parent_context = None
        if not trace.get_current_span().get_span_context().is_valid:
            parent = getattr(user_api_key_dict, "parent_otel_span", None)
            if parent is not None:
                parent_context = trace.set_span_in_context(parent)

        started = time.perf_counter()
        try:
            with tracer.start_as_current_span("prompt.pipeline", context=parent_context) as span:
                span.set_attributes({
                    "litellm.request_id": data.get("litellm_call_id") or "",
                    "prompt.request.model": model,
                    "prompt.request.stream": bool(data.get("stream")),
                    "prompt.request.messages": len(data["messages"]),
                })
                try:
                    result = await super().async_pre_call_hook(user_api_key_dict, cache, data, call_type)
                except HTTPException:
                    self._record_rejected(span, data, model, started)
                    raise
                self._record(span, result if isinstance(result, dict) else data, model, originals, started,
                             user_api_key_dict)
                return result
        finally:
            request_id_var.reset(token)

    def _record_rejected(self, span, data: dict, model: str, started: float) -> None:
        summary = _metadata(data).get(METADATA_KEY) or {}
        reason = failure_reason(summary.get("error", ""))
        elapsed = time.perf_counter() - started
        m.FAILURES.labels("closed", reason).inc()
        m.REQUESTS.labels(model, "none", "rejected").inc()
        m.PIPELINE_DURATION.labels("rejected").observe(elapsed)
        span.add_event("prompt_compression.fail_closed", {"reason": reason})
        span.set_status(Status(StatusCode.ERROR, f"fail_closed:{reason}"))
        event(logger, "prompt_pipeline.fail_closed", logging.WARNING, reason=reason, model=model,
              duration_ms=round(elapsed * 1000, 1))

    def _record(self, span, data: dict, model: str, originals: dict, started: float, user_api_key_dict) -> None:
        metadata = _metadata(data)
        summary = metadata.get(METADATA_KEY) or {}
        status = summary.get("status") or ("disabled" if not self.settings.enabled else "none")
        category = summary.get("category") or "none"
        elapsed = time.perf_counter() - started
        m.REQUESTS.labels(model, category, status).inc()
        m.PIPELINE_DURATION.labels(status).observe(elapsed)

        user_hash = hash_id(getattr(user_api_key_dict, "user_id", None) or data.get("user"), self.obs.hash_salt)
        team_hash = hash_id(getattr(user_api_key_dict, "team_id", None), self.obs.hash_salt)
        attributes = {
            "prompt.status": status,
            "prompt.category": category,
            "prompt.fail_mode": self.settings.fail_mode,
            "prompt.duration_ms": round(elapsed * 1000, 1),
        }
        if user_hash:
            attributes["enduser.id_hash"] = user_hash
        if team_hash:
            attributes["prompt.team_hash"] = team_hash
        log_fields = {"status": status, "category": category, "model": model, "duration_ms": round(elapsed * 1000, 1),
                      "user_hash": user_hash, "team_hash": team_hash}

        if status == "error":
            reason = failure_reason(summary.get("error", ""))
            m.FAILURES.labels("open", reason).inc()
            span.add_event("prompt_compression.fail_open", {"reason": reason})
            attributes["prompt.failure_reason"] = reason
            event(logger, "prompt_pipeline.fail_open", logging.WARNING, reason=reason, **log_fields)
        elif status in ("ok", "shadow"):
            self._record_ok(summary, model, category, originals, data["messages"], attributes, log_fields,
                            applied=status == "ok")

        span.set_attributes(attributes)
        self._attribute_in_langfuse(metadata, category, user_hash, attributes)
        if status != "error":
            event(logger, "prompt_pipeline.completed", **log_fields)

    def _record_ok(self, summary: dict, model: str, category: str, originals: dict, new_messages: list,
                   attributes: dict, log_fields: dict, applied: bool = True) -> None:
        # applied=False is shadow mode: the pipeline ran but the provider got the original prompt, so the token
        # figures are what compression *would* have saved and go to their own counter.
        before = int(summary.get("tokens_before") or 0)
        after = int(summary.get("tokens_after") or 0)
        ratio = float(summary.get("compression_ratio") or 1.0)
        if applied:
            m.TOKENS_BEFORE.labels(model, category).inc(before)
            m.TOKENS_AFTER.labels(model, category).inc(after)
            m.TOKENS_SAVED.labels(model, category).inc(max(0, before - after))
            m.COMPRESSION_RATIO.labels(category).observe(ratio)
        else:
            m.SHADOW_TOKENS_SAVED.labels(model, category).inc(max(0, before - after))

        classify_seconds = compress_seconds = 0.0
        for message in summary.get("messages") or []:
            label = message.get("category")
            if label is None:
                continue
            m.MESSAGES.labels(label, message.get("action", "unknown"), message.get("source", "unknown")).inc()
            for rule in message.get("rule_hits") or []:
                m.RULE_HITS.labels(rule).inc()
            if message.get("redactions"):
                m.REDACTIONS.labels(label).inc(message["redactions"])
            if message.get("cache_hit"):
                m.CLASSIFIER_CACHE.labels("hit").inc()
            elif message.get("source") != "empty":
                m.CLASSIFIER_CACHE.labels("miss").inc()
                classify_seconds += (message.get("classify_ms") or 0) / 1000
                m.CLASSIFIER_LATENCY.labels(label).observe((message.get("classify_ms") or 0) / 1000)
                if message.get("source") in MODEL_SOURCES and message.get("score") is not None:
                    m.TOP_SCORE.labels(label).observe(message["score"])
            if message.get("compress_ms"):
                compress_seconds += message["compress_ms"] / 1000
                m.COMPRESS_LATENCY.labels(label).observe(message["compress_ms"] / 1000)

            index = message["index"]
            text = originals.get(index, "")
            attributes[f"prompt.message.{index}.label"] = label
            attributes[f"prompt.message.{index}.sha256"] = fingerprint(text, self.obs.hash_salt)
            attributes[f"prompt.message.{index}.chars"] = len(text)
            attributes[f"prompt.message.{index}.tokens_before"] = int(message.get("tokens_before") or count_tokens(text))
            attributes[f"prompt.message.{index}.tokens_after"] = int(message.get("tokens_after") or 0)
            # `index` is the message's position in the original request; history trimming can shift it in the result.
            result_index = message.get("new_index", index)
            if applied and self.obs.capture_text and label in TEXT_CAPTURE_LABELS and result_index < len(new_messages):
                after_text = "\n".join(t for _, t in _text_parts(new_messages[result_index]))
                attributes[f"prompt.message.{index}.text_before"] = scrub(text)
                attributes[f"prompt.message.{index}.text_after"] = scrub(after_text)

        rate = self.obs.hourly_rate_usd / 3600
        cost = round((classify_seconds + compress_seconds) * rate, 10)
        for component, seconds in (("classifier", classify_seconds), ("compressor", compress_seconds)):
            if seconds:
                m.COMPUTE_SECONDS.labels(component).inc(seconds)
                m.ESTIMATED_COMPUTE_COST.labels(component).inc(seconds * rate)
        attributes.update({
            "prompt.tokens.before": before,
            "prompt.tokens.after": after,
            "prompt.tokens.saved": max(0, before - after),
            "prompt.compression_ratio": ratio,
            "prompt.cost.estimate_usd": cost,
            "prompt.cost.is_estimate": True,
        })
        log_fields.update({"tokens_before": before, "tokens_after": after, "compression_ratio": ratio,
                           "classify_ms": round(classify_seconds * 1000, 1),
                           "compress_ms": round(compress_seconds * 1000, 1), "estimated_compute_cost_usd": cost})

    def _attribute_in_langfuse(self, metadata: dict, category: str, user_hash: str | None, attributes: dict) -> None:
        # langfuse_otel maps these metadata keys to user.id / langfuse.trace.tags / trace metadata.
        if user_hash:
            metadata["trace_user_id"] = user_hash
        elif "trace_user_id" in metadata:
            metadata["trace_user_id"] = hash_id(metadata["trace_user_id"], self.obs.hash_salt)
        tags = [t for t in (metadata.get("tags") or []) if isinstance(t, str)]
        metadata["tags"] = list(dict.fromkeys(tags + [f"prompt_category:{category}"]))
        trace_metadata = dict(metadata.get("trace_metadata") or {})
        trace_metadata.update({k.removeprefix("prompt."): v for k, v in attributes.items()
                               if k in ("prompt.category", "prompt.status", "prompt.tokens.before",
                                        "prompt.tokens.after", "prompt.compression_ratio", "prompt.cost.estimate_usd")})
        metadata["trace_metadata"] = trace_metadata

    # ----- provider call result ------------------------------------------------------

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        await super().async_log_success_event(kwargs, response_obj, start_time, end_time)
        if self.obs.enabled:
            self._log_provider_result(kwargs, start_time, end_time, failed=False)

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        if self.obs.enabled:
            self._log_provider_result(kwargs, start_time, end_time, failed=True)

    def _log_provider_result(self, kwargs: dict, start_time, end_time, failed: bool) -> None:
        payload = kwargs.get("standard_logging_object") or {}
        litellm_metadata = (kwargs.get("litellm_params") or {}).get("metadata") or {}
        trace_id, span_id = _span_ids(litellm_metadata.get("litellm_parent_otel_span"))
        payload_metadata = payload.get("metadata") or {}
        summary = (payload_metadata.get("spend_logs_metadata") or {}).get(METADATA_KEY) or {}
        fields = {
            "trace_id": trace_id,
            "span_id": span_id,
            "request_id": payload.get("id") or kwargs.get("litellm_call_id"),
            "model": payload.get("model_group") or payload.get("model"),
            "provider": payload.get("custom_llm_provider"),
            "stream": bool(payload.get("stream")),
            "status": "failure" if failed else "success",
            "prompt_tokens": payload.get("prompt_tokens"),
            "completion_tokens": payload.get("completion_tokens"),
            "total_tokens": payload.get("total_tokens"),
            "response_cost_usd": payload.get("response_cost"),
            "latency_ms": _ms(payload.get("startTime"), payload.get("endTime")),
            "ttft_ms": _ms(payload.get("startTime"), payload.get("completionStartTime")) if payload.get("stream") else None,
            "category": summary.get("category"),
            "compression_ratio": summary.get("compression_ratio"),
            "user_api_key_hash": (payload_metadata.get("user_api_key_hash") or "")[:16] or None,
        }
        if failed:
            error = payload.get("error_information") or {}
            fields.update({"error_class": error.get("error_class"), "error_code": error.get("error_code"),
                           "error_message": error.get("error_message")})
        event(logger, "llm.request.failed" if failed else "llm.request.completed",
              logging.WARNING if failed else logging.INFO, **fields)


def _ms(start, end):
    try:
        return round((float(end) - float(start)) * 1000, 1)
    except (TypeError, ValueError):
        return None


_instance: ObservedPromptCompressionCallback | None = None


def __getattr__(name: str):
    # Built on first access by LiteLLM's config loader, so importing this module (tests) loads no models.
    global _instance
    if name == "observed_prompt_compression_instance":
        if _instance is None:
            _instance = ObservedPromptCompressionCallback()
        return _instance
    raise AttributeError(name)
