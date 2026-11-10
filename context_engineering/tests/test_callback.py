"""The LiteLLM hook: gate, opt-out, shadow, fail open / closed, metadata, breakpoints, provider usage capture."""

import asyncio
import itertools
import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from context_engineering import callback as cb
from context_engineering import tokens as tk
from context_engineering.engine import ContextEngine
from context_engineering.store import MemoryStore

from .builders import agent_conversation, log_output, long_chat, settings


def make(**overrides):
    s = settings(**overrides)
    return cb.ContextEngineeringCallback(engine=ContextEngine(s, store=MemoryStore()), settings=s)


def agent_request(model="gpt-4o-mini", **extra):
    counter = itertools.count()
    return {"model": model, "messages": agent_conversation(10, output=lambda: log_output(120, tag=f"s{next(counter)}")),
            **extra}


def run(callback, data, call_type="acompletion"):
    return asyncio.run(callback.async_pre_call_hook(user_api_key_dict=None, cache=None, data=data, call_type=call_type))


def test_enforce_mode_replaces_messages_and_writes_metadata():
    data = agent_request()
    original = [dict(m) for m in data["messages"]]
    out = run(make(), data)
    summary = out["metadata"]["context_engineering"]
    assert summary["status"] == "ok" and summary["tokens_after"] < summary["tokens_before"] and summary["masked"]
    assert out["messages"] != original
    assert out["metadata"]["spend_logs_metadata"]["context_engineering"]["status"] == "ok"


def test_metadata_never_contains_message_text():
    data = agent_request()
    secret_line = data["messages"][3]["content"].splitlines()[5]
    out = run(make(), data)
    assert secret_line not in str(out["metadata"]["context_engineering"])


def test_spend_log_copy_is_bounded():
    data = agent_request()
    data["messages"] = agent_conversation(40, output=lambda c=itertools.count(): log_output(60, tag=f"z{next(c)}"))
    out = run(make(observation_keep_recent=0, observation_batch=1), data)
    full = out["metadata"]["context_engineering"]["masked"]
    spend = out["metadata"]["spend_logs_metadata"]["context_engineering"]
    assert len(full) > cb.SPEND_LOG_RECORDS and len(spend["masked"]) == cb.SPEND_LOG_RECORDS
    assert spend["masked_omitted"] == len(full) - cb.SPEND_LOG_RECORDS


def test_shadow_mode_reports_but_forwards_the_original_and_no_hints():
    chat = long_chat(14)
    data = {"model": "m", "messages": [dict(m) for m in chat]}
    out = run(make(mode="shadow", compaction_enabled=True, window_tokens=8000), data)
    summary = out["metadata"]["context_engineering"]
    assert summary["status"] == "shadow" and summary["tokens_after"] < summary["tokens_before"]
    assert out["messages"] == chat and summary["hints"] == {}


@pytest.mark.parametrize("call_type", ["embeddings", "aimage_generation"])
def test_non_chat_calls_pass_through_untouched(call_type):
    data = agent_request()
    assert "metadata" not in run(make(), data, call_type)


def test_disabled_passes_through_silently():
    data = agent_request()
    out = run(make(enabled=False), data)
    assert "metadata" not in out


@pytest.mark.parametrize("metadata", [{"context_engineering": False}, {"context_engineering": "false"},
                                      {"disable_context_engineering": True}])
def test_per_request_opt_out(metadata):
    data = agent_request(metadata=dict(metadata))
    messages = [dict(m) for m in data["messages"]]
    out = run(make(), data)
    assert out["metadata"]["context_engineering"] == {"status": "skipped", "reason": "request_opt_out"}
    assert out["messages"] == messages


def test_small_requests_are_skipped():
    data = {"model": "m", "messages": [{"role": "user", "content": "hi"}]}
    out = run(make(min_tokens=1000), data)
    assert out["metadata"]["context_engineering"]["reason"] == "below_min_size"


def test_engine_error_fails_open_with_the_original_request():
    callback = make()

    def boom(*args, **kwargs):
        raise RuntimeError("bug")
    callback._engine.process = boom
    data = agent_request()
    messages = [dict(m) for m in data["messages"]]
    out = run(callback, data)
    assert out["messages"] == messages and out["metadata"]["context_engineering"]["status"] == "error"


def test_timeout_fails_open():
    callback = make(timeout_s=0.05)

    def slow(*args, **kwargs):
        time.sleep(0.5)
    callback._engine.process = slow
    out = run(callback, agent_request())
    assert out["metadata"]["context_engineering"]["error"].startswith("timeout")


def test_fail_closed_rejects_with_503():
    callback = make(fail_mode="closed")

    def boom(*args, **kwargs):
        raise RuntimeError("bug")
    callback._engine.process = boom
    with pytest.raises(HTTPException) as info:
        run(callback, agent_request())
    assert info.value.status_code == 503


def test_engine_init_failure_follows_the_fail_mode(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("cannot build")
    monkeypatch.setattr(cb, "ContextEngine", broken)
    callback = cb.ContextEngineeringCallback(settings=settings())
    out = run(callback, agent_request())
    assert out["metadata"]["context_engineering"]["error"].startswith("engine init failed")


def test_breakpoints_are_added_to_anthropic_requests_only():
    system = " ".join(f"Rule {i}: be careful with step {i}." for i in range(400))
    anthropic = agent_request(model="anthropic/claude-sonnet-4-5")
    anthropic["messages"][0] = {"role": "system", "content": system}
    openai = agent_request(model="gpt-4o-mini")
    openai["messages"][0] = {"role": "system", "content": system}
    assert run(make(), anthropic)["cache_control_injection_points"] == [{"location": "message", "role": "system"}]
    assert "cache_control_injection_points" not in run(make(), openai)
    existing = agent_request(model="anthropic/claude-sonnet-4-5",
                             cache_control_injection_points=[{"location": "message", "role": "user"}])
    existing["messages"][0] = {"role": "system", "content": system}
    assert run(make(), existing)["cache_control_injection_points"] == [{"location": "message", "role": "user"}]


def test_redaction_is_applied_before_anything_is_stored(monkeypatch):
    monkeypatch.setenv("REDACT_SENSITIVE", "true")
    callback = make()
    data = agent_request()
    data["messages"][3] = {**data["messages"][3], "content": data["messages"][3]["content"] + "\ncontact jane.doe@example.com"}
    out = run(callback, data)
    record = next(r for r in out["metadata"]["context_engineering"]["masked"] if r["index"] == 3)
    stored = callback._engine.store.get(record["ref"])
    assert "jane.doe@example.com" not in stored["content"] and "[EMAIL]" in stored["content"]


def usage_kwargs(summary, compression=None, provider="anthropic"):
    spend = {"context_engineering": summary}
    if compression:
        spend["prompt_compression"] = compression
    return {"standard_logging_object": {"custom_llm_provider": provider, "metadata": {"spend_logs_metadata": spend}}}


def test_provider_cache_reads_and_writes_are_captured_and_calibration_learns(monkeypatch):
    calibration = tk.Calibration(min_samples=1)
    monkeypatch.setattr(tk, "CALIBRATION", calibration)
    usage = SimpleNamespace(prompt_tokens=1300, prompt_tokens_details=SimpleNamespace(cached_tokens=900),
                            cache_creation_input_tokens=200)
    response = SimpleNamespace(usage=usage)
    callback = make()
    asyncio.run(callback.async_log_success_event(
        usage_kwargs({"status": "ok", "tokens_after": 1100, "model": "claude"},
                     {"status": "ok", "tokens_before": 500, "tokens_after": 400}), response, None, None))
    assert calibration.factor("claude") == pytest.approx(1300 / 1000)
    from context_engineering import metrics as m
    if hasattr(m.PROVIDER_CACHED_TOKENS, "labels") and hasattr(m.PROVIDER_CACHED_TOKENS.labels("anthropic"), "_value"):
        assert m.PROVIDER_CACHED_TOKENS.labels("anthropic")._value.get() >= 900


def test_usage_capture_never_raises():
    callback = make()
    asyncio.run(callback.async_log_success_event({}, None, None, None))
    asyncio.run(callback.async_log_success_event(usage_kwargs({"status": "ok"}), object(), None, None))


# ---- LiteLLM compatibility -----------------------------------------------------------------------------------------

def test_the_class_defines_its_own_pre_call_hook_as_litellm_requires():
    assert "async_pre_call_hook" in vars(cb.ContextEngineeringCallback)
    assert "async_log_success_event" in vars(cb.ContextEngineeringCallback)


def test_module_attribute_builds_one_instance_lazily():
    first = cb.context_engineering_instance
    assert first is cb.context_engineering_instance and isinstance(first, cb.ContextEngineeringCallback)
    with pytest.raises(AttributeError):
        cb.no_such_instance
