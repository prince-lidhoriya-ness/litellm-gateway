"""Regression tests for the observability findings in PROJECT_AUDIT_REPORT.md (F-13, F-18S, F-22S, F-23)."""

import asyncio
import hashlib
import json
import logging

from observability.logs import configure_logging
from observability.privacy import derive_salt, fingerprint, hash_id
from observability.settings import ObservabilitySettings

from .test_observed_callback import LONG, captured_logs, make_callback, obs_settings, run  # noqa: F401


def prompt_span(exporter):
    return next(s for s in exporter.get_finished_spans() if s.name == "prompt.pipeline")


def long_chat(turns):
    messages = []
    for i in range(turns):
        messages.append({"role": "user", "content": f"CHAT question {i} " + LONG})
        messages.append({"role": "assistant", "content": f"answer {i} " + LONG})
    messages.append({"role": "user", "content": "CHAT final " + LONG})
    return messages


def test_f23_long_conversations_keep_request_attributes_and_cap_message_attributes(spans):
    data = {"model": "mock-echo", "litellm_call_id": "req-long", "metadata": {}, "messages": long_chat(30)}
    run(make_callback(obs=obs_settings(max_span_messages=10)), data)
    attrs = prompt_span(spans).attributes
    for key in ("prompt.status", "prompt.tokens.before", "prompt.tokens.after", "prompt.cost.estimate_usd", "prompt.intent"):
        assert key in attrs
    labelled = {key.split(".")[2] for key in attrs if key.startswith("prompt.message.")}
    assert len(labelled) == 10 and "60" in labelled             # the latest messages are the ones shown
    assert attrs["prompt.messages.attributes_omitted"] == 51
    assert len(attrs) <= 128


def test_f22s_provider_error_messages_are_hashed_not_logged(captured_logs):  # noqa: F811
    leaked = "prompt fragment: my secret plan for Q3"
    kwargs = {"standard_logging_object": {"id": "req-err", "error_information": {
        "error_class": "BadRequestError", "error_code": "400", "error_message": leaked}}}
    asyncio.run(make_callback().async_log_failure_event(kwargs, None, 0, 1))
    line = [json.loads(l) for l in captured_logs.getvalue().splitlines() if '"llm.request.failed"' in l][-1]
    assert leaked not in captured_logs.getvalue() and "error_message" not in line
    assert line["error_message_hash"] == fingerprint(leaked, "test-salt") and line["error_message_chars"] == len(leaked)


def test_f18s_hashes_are_keyed_hmacs():
    assert hash_id("alice", "k1") != hash_id("alice", "k2")
    assert hash_id("alice", "k1") != hashlib.sha256(b"k1alice").hexdigest()[:16]     # not sha256(salt + value)
    assert hash_id(None, "k") is None and len(fingerprint("text", "k")) == 16


def test_f18s_salt_falls_back_to_a_key_derived_from_litellm_salt_key(monkeypatch):
    monkeypatch.delenv("OBS_HASH_SALT", raising=False)
    monkeypatch.setenv("LITELLM_SALT_KEY", "sk-test-salt")
    settings = ObservabilitySettings.from_env()
    assert settings.hash_salt == derive_salt("sk-test-salt") and settings.hash_salt_source == "LITELLM_SALT_KEY"
    assert settings.hash_salt != "sk-test-salt"
    monkeypatch.setenv("OBS_HASH_SALT", "explicit")
    assert ObservabilitySettings.from_env().hash_salt == "explicit"
    monkeypatch.delenv("OBS_HASH_SALT")
    monkeypatch.delenv("LITELLM_SALT_KEY")
    assert ObservabilitySettings.from_env().hash_salt == ""


def test_f13_log_level_follows_the_environment(monkeypatch):
    import observability.logs as logs

    monkeypatch.setattr(logs, "_configured", False)
    monkeypatch.setenv("PROMPT_COMPRESSION_LOG_LEVEL", "WARNING")
    previous = {name: logging.getLogger(name).level for name in logs.LOGGER_NAMES}
    try:
        configure_logging(ObservabilitySettings.from_env())
        assert all(logging.getLogger(name).level == logging.WARNING for name in logs.LOGGER_NAMES)
    finally:
        for name, level in previous.items():
            logging.getLogger(name).setLevel(level)
