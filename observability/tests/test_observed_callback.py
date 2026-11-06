import asyncio
import dataclasses
import io
import json
import logging
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from opentelemetry import trace
from prometheus_client import REGISTRY

from observability import metrics as m
from observability.logs import JsonFormatter, LOGGER_NAMES
from observability.observed_callback import ObservedPromptCompressionCallback, failure_reason
from observability.settings import ObservabilitySettings
from prompt_compression.sensitivity import GENERAL_CATEGORY, SENSITIVE_CATEGORY
from prompt_compression.pipeline import PromptPipeline
from prompt_compression.tests.fakes import StubCompressor, StubDetector
from prompt_compression.tests.test_pipeline import LONG, settings as pipeline_settings

SECRET_EMAIL = "jane.doe@example.com"
SECRET_MARKER = "UNIQUE-SENSITIVE-MARKER-4471"
SENSITIVE_TEXT = f"my email is {SECRET_EMAIL} and my note is {SECRET_MARKER} " + LONG
SENSITIVE_KEYWORDS = ("PRIVATE-NOTE",)

PIPELINE_SPANS = {"prompt.pipeline", "prompt.classify", "prompt.route", "prompt.compress"}
EXPECTED_METRICS = {
    "prompt_pipeline_requests_total", "prompt_pipeline_messages_total", "prompt_pipeline_duration_seconds_count",
    "prompt_pipeline_tokens_before_total", "prompt_pipeline_tokens_after_total", "prompt_pipeline_tokens_saved_total",
    "prompt_pipeline_compression_ratio_count", "prompt_pipeline_classifier_latency_seconds_count",
    "prompt_pipeline_compress_latency_seconds_count", "prompt_pipeline_classifier_cache_total",
}


def obs_settings(**overrides):
    values = dict(enabled=True, service_name="test", otlp_logs_endpoint="", log_json=True, capture_text=False,
                  hash_salt="test-salt", compute_device="cpu", cpu_hourly_rate_usd=0.10, gpu_hourly_rate_usd=0.0,
                  max_model_label_values=5)
    values.update(overrides)
    return ObservabilitySettings(**values)


def make_callback(detector=None, obs=None, **pipeline_overrides):
    p_settings = pipeline_settings(**pipeline_overrides)
    pipeline = PromptPipeline(settings=p_settings, detector=detector or StubDetector(SENSITIVE_KEYWORDS),
                              compressor=StubCompressor())
    return ObservedPromptCompressionCallback(pipeline=pipeline, settings=p_settings, obs_settings=obs or obs_settings())


def request(content, request_id="req-1", model="mock-echo", **extra):
    return {"model": model, "litellm_call_id": request_id, "messages": [{"role": "user", "content": content}],
            "metadata": {}, **extra}


def user(user_id="user-42", team_id="team-7"):
    return SimpleNamespace(user_id=user_id, team_id=team_id, parent_otel_span=None)


def run(callback, data, user_api_key_dict=None, call_type="acompletion"):
    """Run the hook inside a server span, the way LiteLLM's OTel V2 does."""
    async def go():
        with trace.get_tracer("test").start_as_current_span("POST /v1/chat/completions"):
            return await callback.async_pre_call_hook(user_api_key_dict or user(), None, data, call_type)
    return asyncio.run(go())


@pytest.fixture
def captured_logs():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    loggers = [logging.getLogger(name) for name in LOGGER_NAMES]
    for logger in loggers:
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    yield stream
    for logger in loggers:
        logger.removeHandler(handler)


def sample(name, **labels):
    return REGISTRY.get_sample_value(name, labels) or 0.0


def test_emits_one_trace_with_pipeline_spans(spans):
    run(make_callback(), request("CHAT " + LONG))
    finished = {s.name: s for s in spans.get_finished_spans()}
    assert PIPELINE_SPANS <= set(finished)
    server = finished["POST /v1/chat/completions"]
    trace_ids = {s.context.trace_id for s in spans.get_finished_spans()}
    assert trace_ids == {server.context.trace_id}
    pipeline = finished["prompt.pipeline"]
    assert pipeline.parent.span_id == server.context.span_id
    for child in ("prompt.classify", "prompt.route", "prompt.compress"):
        assert finished[child].parent.span_id == pipeline.context.span_id
    classify = finished["prompt.classify"].attributes
    assert classify["prompt.classifier.label"] == GENERAL_CATEGORY
    assert {"prompt.classifier.score", "prompt.classifier.source", "prompt.classifier.cache_hit"} <= set(classify)
    route_attrs = finished["prompt.route"].attributes
    assert route_attrs["prompt.route.units"] >= 1 and list(route_attrs["prompt.route.routes"]) == ["narrative"]


def test_expected_metric_names_are_exported():
    run(make_callback(), request("CHAT " + LONG))
    names = {s.name for metric in REGISTRY.collect() for s in metric.samples}
    assert EXPECTED_METRICS <= names


def test_token_counts_before_and_after_are_recorded(spans, captured_logs):
    before_counter = sample("prompt_pipeline_tokens_before_total", model="mock-echo", label=GENERAL_CATEGORY)
    after_counter = sample("prompt_pipeline_tokens_after_total", model="mock-echo", label=GENERAL_CATEGORY)
    data = run(make_callback(), request("CHAT " + LONG))
    summary = data["metadata"]["prompt_compression"]
    assert summary["tokens_after"] < summary["tokens_before"]

    attrs = next(s for s in spans.get_finished_spans() if s.name == "prompt.pipeline").attributes
    assert attrs["prompt.tokens.before"] == summary["tokens_before"]
    assert attrs["prompt.tokens.after"] == summary["tokens_after"]
    assert attrs["prompt.compression_ratio"] == summary["compression_ratio"]
    compress = next(s for s in spans.get_finished_spans() if s.name == "prompt.compress").attributes
    assert compress["prompt.tokens.before"] > compress["prompt.tokens.after"]

    assert sample("prompt_pipeline_tokens_before_total", model="mock-echo", label=GENERAL_CATEGORY) - before_counter == summary["tokens_before"]
    assert sample("prompt_pipeline_tokens_after_total", model="mock-echo", label=GENERAL_CATEGORY) - after_counter == summary["tokens_after"]

    completed = [json.loads(line) for line in captured_logs.getvalue().splitlines()
                 if '"prompt_pipeline.completed"' in line]
    assert completed and completed[-1]["tokens_before"] == summary["tokens_before"]
    assert completed[-1]["tokens_after"] == summary["tokens_after"]


def test_sensitive_prompt_text_never_exported(spans, captured_logs):
    callback = make_callback(obs=obs_settings(capture_text=True))  # even with text capture on
    data = run(callback, request(SENSITIVE_TEXT, request_id="req-sens"))
    assert data["messages"][0]["content"] == SENSITIVE_TEXT  # unchanged for the model
    asyncio.run(callback.async_log_success_event(
        {"standard_logging_object": {"id": "req-sens", "metadata": {"spend_logs_metadata": data["metadata"]["spend_logs_metadata"]}},
         "litellm_params": {"metadata": {}}}, None, 0, 1))

    exported = []
    for span in spans.get_finished_spans():
        exported.append(json.dumps(dict(span.attributes), default=str))
        exported.extend(json.dumps(dict(e.attributes or {}), default=str) for e in span.events)
    exported.append(captured_logs.getvalue())
    exported.extend(json.dumps(s.labels) for metric in REGISTRY.collect() for s in metric.samples)
    blob = "\n".join(exported)
    assert captured_logs.getvalue()  # something was logged
    for secret in (SECRET_EMAIL, SECRET_MARKER, "my email is"):
        assert secret not in blob
    attrs = next(s for s in spans.get_finished_spans() if s.name == "prompt.pipeline").attributes
    assert attrs["prompt.category"] == SENSITIVE_CATEGORY
    assert len(attrs["prompt.message.0.sha256"]) == 16
    assert attrs["prompt.message.0.chars"] == len(SENSITIVE_TEXT)
    assert "prompt.message.0.text_before" not in attrs


def test_text_capture_only_for_allowed_labels_and_only_when_enabled(spans):
    run(make_callback(), request("CHAT " + LONG))
    off = next(s for s in spans.get_finished_spans() if s.name == "prompt.pipeline").attributes
    assert "prompt.message.0.text_before" not in off
    spans.clear()
    run(make_callback(obs=obs_settings(capture_text=True)), request("CHAT " + LONG))
    on = next(s for s in spans.get_finished_spans() if s.name == "prompt.pipeline").attributes
    assert on["prompt.message.0.text_before"].startswith("CHAT")
    assert len(on["prompt.message.0.text_after"]) < len(on["prompt.message.0.text_before"])
    spans.clear()
    run(make_callback(obs=obs_settings(capture_text=True)), request("PRIVATE-NOTE " + LONG))
    sensitive = next(s for s in spans.get_finished_spans() if s.name == "prompt.pipeline").attributes
    assert "prompt.message.0.text_before" not in sensitive


def test_metric_labels_are_low_cardinality():
    callback = make_callback()
    for i in range(30):
        run(callback, request("CHAT " + LONG, request_id=f"req-unique-{i}", model=f"model-{i}"), user(f"user-{i}", f"team-{i}"))
    values = set()
    for metric in REGISTRY.collect():
        if not metric.name.startswith("prompt_pipeline"):
            continue
        for s in metric.samples:
            assert set(s.labels) - {"le"} <= m.ALLOWED_LABELS, (metric.name, s.labels)
            values.update(v for k, v in s.labels.items() if k != "le")
    assert not any(v.startswith(("req-unique-", "user-", "team-")) for v in values)
    models = {s.labels["model"] for metric in REGISTRY.collect() if metric.name == "prompt_pipeline_requests"
              for s in metric.samples if "model" in s.labels}
    assert "other" in models and len(models) <= 6  # max_model_label_values=5 plus "other"


def test_user_ids_are_hashed_for_langfuse(spans):
    data = run(make_callback(), request("CHAT " + LONG, metadata={"trace_user_id": "alice@example.com"}), user(None, None))
    assert data["metadata"]["trace_user_id"] != "alice@example.com"
    assert len(data["metadata"]["trace_user_id"]) == 16
    assert "prompt_category:general" in data["metadata"]["tags"]
    data = run(make_callback(), request("CHAT " + LONG), user("user-42"))
    assert data["metadata"]["trace_user_id"] not in ("user-42", None)


def test_fail_open_is_counted_and_logged(spans, captured_logs):
    before = sample("prompt_pipeline_failures_total", mode="open", reason="classifier_unavailable")
    data = run(make_callback(detector=StubDetector(unavailable=True)), request("CHAT " + LONG))
    assert data["messages"][0]["content"] == "CHAT " + LONG
    assert sample("prompt_pipeline_failures_total", mode="open", reason="classifier_unavailable") == before + 1
    span = next(s for s in spans.get_finished_spans() if s.name == "prompt.pipeline")
    assert [e.name for e in span.events] == ["prompt_compression.fail_open"]
    assert '"prompt_pipeline.fail_open"' in captured_logs.getvalue()


def test_fail_closed_is_counted_and_reraised(spans):
    before = sample("prompt_pipeline_failures_total", mode="closed", reason="classifier_unavailable")
    with pytest.raises(HTTPException):
        run(make_callback(detector=StubDetector(unavailable=True), fail_mode="closed"), request("CHAT " + LONG))
    assert sample("prompt_pipeline_failures_total", mode="closed", reason="classifier_unavailable") == before + 1
    span = next(s for s in spans.get_finished_spans() if s.name == "prompt.pipeline")
    assert span.status.status_code.name == "ERROR"


def test_every_log_line_has_trace_and_request_id(captured_logs):
    run(make_callback(), request("CHAT " + LONG, request_id="req-log-1"))
    lines = [json.loads(line) for line in captured_logs.getvalue().splitlines()]
    assert lines
    for line in lines:
        assert line["trace_id"] and len(line["trace_id"]) == 32
        assert line["request_id"] == "req-log-1"
        assert line["event"]


def test_provider_result_log_carries_trace_tokens_and_cost(captured_logs):
    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("POST /v1/chat/completions") as server:
        trace_id = format(server.get_span_context().trace_id, "032x")
    kwargs = {
        "standard_logging_object": {
            "id": "req-9", "model_group": "obs-priced-llama", "custom_llm_provider": "ollama", "stream": True,
            "prompt_tokens": 40, "completion_tokens": 12, "total_tokens": 52, "response_cost": 0.00052,
            "startTime": 100.0, "completionStartTime": 100.2, "endTime": 101.0,
            "metadata": {"user_api_key_hash": "a" * 64, "spend_logs_metadata": {"prompt_compression": {"category": "critical"}}},
        },
        "litellm_params": {"metadata": {"litellm_parent_otel_span": server}},
    }
    asyncio.run(make_callback().async_log_success_event(kwargs, None, 100.0, 101.0))
    line = [json.loads(l) for l in captured_logs.getvalue().splitlines() if '"llm.request.completed"' in l][-1]
    assert line["trace_id"] == trace_id and line["request_id"] == "req-9"
    assert (line["prompt_tokens"], line["completion_tokens"], line["response_cost_usd"]) == (40, 12, 0.00052)
    assert (line["latency_ms"], line["ttft_ms"]) == (1000.0, 200.0)
    assert line["user_api_key_hash"] == "a" * 16


def test_failure_reason_mapping():
    assert failure_reason("timeout after 10.0s: TimeoutError") == "timeout"
    assert failure_reason("pipeline init failed: ValueError") == "init_failed"
    assert failure_reason("pipeline error: ClassifierUnavailable") == "classifier_unavailable"
    assert failure_reason("pipeline error: RuntimeError") == "pipeline_error"


def test_disabled_observability_is_the_plain_hook(spans):
    data = run(make_callback(obs=obs_settings(enabled=False)), request("CHAT " + LONG))
    assert data["metadata"]["prompt_compression"]["status"] == "ok"
    assert "prompt.pipeline" not in {s.name for s in spans.get_finished_spans()}


def test_shadow_mode_savings_go_to_their_own_counter_and_the_prompt_is_unchanged(spans):
    shadow_before = sample("prompt_pipeline_shadow_tokens_saved_total", model="mock-echo", label=GENERAL_CATEGORY)
    applied_before = sample("prompt_pipeline_tokens_saved_total", model="mock-echo", label=GENERAL_CATEGORY)
    requests_before = sample("prompt_pipeline_requests_total", model="mock-echo", label=GENERAL_CATEGORY, status="shadow")
    data = run(make_callback(mode="shadow"), request("CHAT " + LONG))
    summary = data["metadata"]["prompt_compression"]
    assert summary["status"] == "shadow" and data["messages"][0]["content"] == "CHAT " + LONG
    saved = summary["tokens_before"] - summary["tokens_after"]
    assert saved > 0
    assert sample("prompt_pipeline_shadow_tokens_saved_total", model="mock-echo", label=GENERAL_CATEGORY) - shadow_before == saved
    assert sample("prompt_pipeline_tokens_saved_total", model="mock-echo", label=GENERAL_CATEGORY) == applied_before
    assert sample("prompt_pipeline_requests_total", model="mock-echo", label=GENERAL_CATEGORY, status="shadow") - requests_before == 1


def test_history_trimming_keeps_span_attributes_on_the_original_message_indexes(spans):
    callback = make_callback(
        obs=obs_settings(capture_text=True), routes=frozenset({"narrative", "history"}),
        history_max_tokens=300, history_keep_messages=3,
    )
    data = {"model": "mock-echo", "litellm_call_id": "req-hist", "metadata": {}, "messages": [
        {"role": "user", "content": "CHAT first " + LONG},
        {"role": "assistant", "content": "reply " + LONG},
        {"role": "user", "content": "CHAT second " + LONG},
        {"role": "assistant", "content": "reply again " + LONG},
        {"role": "user", "content": "CHAT third " + LONG},
    ]}
    result = run(callback, data)
    summary = result["metadata"]["prompt_compression"]
    assert summary["history_dropped"] == 2 and len(result["messages"]) == 3
    attrs = next(s for s in spans.get_finished_spans() if s.name == "prompt.pipeline").attributes
    assert attrs["prompt.message.4.label"] == GENERAL_CATEGORY          # original index of the latest user message
    assert "prompt.message.4.text_after" in attrs and "prompt.message.0.label" not in attrs
