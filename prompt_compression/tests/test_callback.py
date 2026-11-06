import asyncio
import logging
import time

import pytest
from fastapi import HTTPException

from prompt_compression.pipeline import PromptPipeline
from prompt_compression.prompt_compression_callback import PromptCompressionCallback

from .fakes import StubCompressor, StubDetector
from .test_pipeline import LONG, settings

SECRET_TEXT = "my email is jane.doe@example.com " + LONG


def make_callback(detector=None, **overrides):
    pipeline_settings = settings(**overrides)
    pipeline = PromptPipeline(
        settings=pipeline_settings, detector=detector or StubDetector(["PRIVATE-NOTE"]), compressor=StubCompressor()
    )
    return PromptCompressionCallback(pipeline=pipeline, settings=pipeline_settings)


def request(content, metadata=None):
    data = {"model": "mock", "messages": [{"role": "user", "content": content}]}
    if metadata is not None:
        data["metadata"] = metadata
    return data


def run(callback, data, call_type="acompletion"):
    return asyncio.run(callback.async_pre_call_hook(user_api_key_dict=None, cache=None, data=data, call_type=call_type))


def test_compresses_and_writes_metadata():
    data = run(make_callback(), request("plain " + LONG))
    summary = data["metadata"]["prompt_compression"]
    assert summary["status"] == "ok" and summary["category"] == "general"
    assert summary["tokens_after"] < summary["tokens_before"] and summary["compression_ratio"] > 1
    assert data["metadata"]["spend_logs_metadata"]["prompt_compression"] == summary
    assert data["messages"][0]["content"] != "plain " + LONG


def test_summary_describes_the_routes_and_segments():
    summary = run(make_callback(), request("plain " + LONG))["metadata"]["prompt_compression"]
    assert summary["mode"] == "enforce" and summary["routes"] == ["narrative"] and summary["history_dropped"] == 0
    assert summary["segments"]["compressed_blocks"] == 1 and summary["kept"] == {}


def test_shadow_mode_reports_what_would_happen_but_sends_the_original():
    data = run(make_callback(mode="shadow"), request("plain " + LONG))
    summary = data["metadata"]["prompt_compression"]
    assert summary["status"] == "shadow" and summary["mode"] == "shadow"
    assert summary["tokens_after"] < summary["tokens_before"]          # the saving it would have made
    assert data["messages"][0]["content"] == "plain " + LONG            # but the provider gets the original


def test_shadow_mode_log_line_says_so(caplog):
    with caplog.at_level(logging.INFO, logger="prompt_compression"):
        run(make_callback(mode="shadow"), request("plain " + LONG))
    assert "shadow, original sent" in caplog.text


def test_sensitive_request_reaches_model_unchanged():
    data = run(make_callback(), request(SECRET_TEXT))
    assert data["messages"][0]["content"] == SECRET_TEXT
    assert data["metadata"]["prompt_compression"]["category"] == "sensitive"


def test_fail_open_when_the_sensitivity_model_is_unavailable(caplog):
    callback = make_callback(detector=StubDetector(unavailable=True))
    original = request("plain " + LONG)
    with caplog.at_level(logging.WARNING, logger="prompt_compression"):
        data = run(callback, request("plain " + LONG))
    assert data["messages"] == original["messages"]
    assert data["metadata"]["prompt_compression"]["status"] == "error"
    assert "fail_mode=open" in caplog.text


def test_fail_closed_rejects_request():
    callback = make_callback(detector=StubDetector(unavailable=True), fail_mode="closed")
    with pytest.raises(HTTPException) as excinfo:
        run(callback, request("plain " + LONG))
    assert excinfo.value.status_code == 503


def test_timeout_fails_open():
    class SlowDetector(StubDetector):
        def check(self, text):
            time.sleep(1.0)
            return super().check(text)

    callback = make_callback(detector=SlowDetector(), timeout_s=0.1)
    data = run(callback, request("plain " + LONG))
    assert data["messages"][0]["content"] == "plain " + LONG
    assert "timeout" in data["metadata"]["prompt_compression"]["error"]


def test_disabled_by_env_flag():
    data = run(make_callback(enabled=False), request("plain " + LONG))
    assert data["messages"][0]["content"] == "plain " + LONG
    assert "prompt_compression" not in data.get("metadata", {})


@pytest.mark.parametrize("metadata", [{"prompt_compression": False}, {"disable_prompt_compression": True}])
def test_per_request_opt_out(metadata):
    data = run(make_callback(), request("plain " + LONG, metadata=dict(metadata)))
    assert data["messages"][0]["content"] == "plain " + LONG
    summary = data["metadata"]["prompt_compression"]
    assert summary["status"] == "skipped" and summary["reason"] == "request_opt_out"


def test_a_tiny_request_is_skipped_by_the_gate():
    detector = StubDetector()
    data = run(make_callback(detector=detector, min_tokens=50), request("hi there"))
    summary = data["metadata"]["prompt_compression"]
    assert summary["status"] == "skipped" and summary["reason"] == "below_min_size"
    assert detector.checked == []                       # the pipeline never ran


def test_non_chat_calls_are_ignored():
    data = {"model": "mock", "input": "plain " + LONG}
    assert run(make_callback(), data, call_type="aembedding") == data


def test_logs_never_contain_prompt_text(caplog):
    marker = "UNIQUE-PROMPT-MARKER-7731"
    with caplog.at_level(logging.DEBUG, logger="prompt_compression"):
        run(make_callback(), request(f"plain {marker} " + LONG))
        run(make_callback(detector=StubDetector(unavailable=True)), request(f"{marker} " + LONG))
    assert caplog.records
    assert marker not in caplog.text
