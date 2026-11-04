import asyncio
import dataclasses
import logging
import time

import pytest
from fastapi import HTTPException

from prompt_compression.labels import LESS_IMPORTANT, SENSITIVE
from prompt_compression.pipeline import PromptPipeline
from prompt_compression.prompt_compression_callback import PromptCompressionCallback

from .fakes import StubClassifier, StubCompressor
from .test_pipeline import LONG, settings

SECRET_TEXT = "my email is jane.doe@example.com " + LONG


def make_callback(classifier=None, **overrides):
    pipeline_settings = settings(**overrides)
    pipeline = PromptPipeline(
        settings=pipeline_settings,
        classifier=classifier or StubClassifier({"CHAT": LESS_IMPORTANT, "jane.doe": SENSITIVE}),
        compressor=StubCompressor(),
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
    data = run(make_callback(), request("CHAT " + LONG))
    summary = data["metadata"]["prompt_compression"]
    assert summary["status"] == "ok"
    assert summary["category"] == LESS_IMPORTANT
    assert summary["tokens_after"] < summary["tokens_before"]
    assert summary["compression_ratio"] > 1
    assert data["metadata"]["spend_logs_metadata"]["prompt_compression"] == summary
    assert data["messages"][0]["content"] != "CHAT " + LONG


def test_sensitive_request_reaches_model_unchanged():
    data = run(make_callback(), request(SECRET_TEXT))
    assert data["messages"][0]["content"] == SECRET_TEXT
    assert data["metadata"]["prompt_compression"]["category"] == SENSITIVE


def test_fail_open_when_classifier_unavailable(caplog):
    callback = make_callback(classifier=StubClassifier({}, unavailable=True))
    original = request("CHAT " + LONG)
    with caplog.at_level(logging.WARNING, logger="prompt_compression"):
        data = run(callback, request("CHAT " + LONG))
    assert data["messages"] == original["messages"]
    assert data["metadata"]["prompt_compression"]["status"] == "error"
    assert "fail_mode=open" in caplog.text


def test_fail_closed_rejects_request():
    callback = make_callback(classifier=StubClassifier({}, unavailable=True), fail_mode="closed")
    with pytest.raises(HTTPException) as excinfo:
        run(callback, request("CHAT " + LONG))
    assert excinfo.value.status_code == 503


def test_timeout_fails_open():
    class SlowClassifier(StubClassifier):
        def classify(self, text):
            time.sleep(1.0)
            return super().classify(text)

    callback = make_callback(classifier=SlowClassifier({}), timeout_s=0.1)
    data = run(callback, request("CHAT " + LONG))
    assert data["messages"][0]["content"] == "CHAT " + LONG
    assert "timeout" in data["metadata"]["prompt_compression"]["error"]


def test_disabled_by_env_flag():
    callback = make_callback(enabled=False)
    data = run(callback, request("CHAT " + LONG))
    assert data["messages"][0]["content"] == "CHAT " + LONG
    assert "prompt_compression" not in data.get("metadata", {})


@pytest.mark.parametrize("metadata", [{"prompt_compression": False}, {"disable_prompt_compression": True}])
def test_per_request_opt_out(metadata):
    data = run(make_callback(), request("CHAT " + LONG, metadata=dict(metadata)))
    assert data["messages"][0]["content"] == "CHAT " + LONG
    assert data["metadata"]["prompt_compression"]["status"] == "skipped"


def test_non_chat_calls_are_ignored():
    data = {"model": "mock", "input": "CHAT " + LONG}
    assert run(make_callback(), data, call_type="aembedding") == data


def test_logs_never_contain_prompt_text(caplog):
    marker = "UNIQUE-PROMPT-MARKER-7731"
    with caplog.at_level(logging.DEBUG, logger="prompt_compression"):
        run(make_callback(), request(f"CHAT {marker} " + LONG))
        run(make_callback(classifier=StubClassifier({}, unavailable=True)), request(f"{marker} " + LONG))
    assert caplog.records
    assert marker not in caplog.text
