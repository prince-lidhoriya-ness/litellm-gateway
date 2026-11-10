"""The engine end to end: stage order, feature flags, per-stage fallback, determinism, cache stability."""

import json

import pytest

from context_engineering import engine as engine_module
from context_engineering import history, masking
from context_engineering.engine import ContextEngine
from context_engineering.store import MemoryStore
from context_engineering.structures import SUMMARY_MARKER

from .builders import agent_conversation, log_output, long_chat, settings


def varied(n=120):
    counter = iter(range(10**6))
    return lambda: log_output(n, tag=f"svc{next(counter)}")


def make(**overrides):
    return ContextEngine(settings(**overrides), store=MemoryStore())


def test_agent_traffic_is_masked_and_reported():
    messages = agent_conversation(10, output=varied())
    result = make().process(messages, model="gpt-4o-mini")
    report = result.report
    assert report.tokens_after < report.tokens_before and report.masked
    assert report.by_category_after["tool_output"] < report.by_category_before["tool_output"]
    assert report.caching == "supported" and report.window_source == "model_map"
    assert report.stages_failed == [] and report.invariant_violations == []
    assert set(report.stage_ms) == {"analyze", "cache", "mask", "history"}
    json.dumps(report.as_metadata())                 # serialisable for metadata and spend logs


def test_input_messages_are_never_mutated():
    messages = agent_conversation(10, output=varied())
    snapshot = json.dumps(messages)
    make().process(messages, model="gpt-4o-mini")
    assert json.dumps(messages) == snapshot


def test_masking_comes_first_and_history_runs_only_if_still_needed():
    messages = agent_conversation(10, output=varied())
    result = make(compaction_enabled=True, window_tokens=100000).process(messages, model="m")
    assert result.report.masked and result.report.summary_index is None
    assert any("not needed after masking" in d for d in result.report.decisions) or "history" not in \
        result.report.techniques


def test_long_chat_on_a_small_window_is_compacted_and_the_summary_is_protected():
    chat = long_chat(14)
    result = make(compaction_enabled=True, window_tokens=8000).process(chat, model="ollama_chat/llama3.2:3b")
    report = result.report
    assert report.summary_index is not None and report.hints == {"protected_indexes": [report.summary_index]}
    assert result.messages[report.summary_index]["content"].startswith(SUMMARY_MARKER)
    assert report.utilization_after < report.utilization_before
    assert result.messages[-1] == chat[-1]


@pytest.mark.parametrize("flag", ["masking_enabled", "prefix_cache_enabled", "budget_enabled"])
def test_each_feature_flag_switches_its_technique_off(flag):
    messages = agent_conversation(10, output=varied())
    result = make(**{flag: False}).process(messages, model="anthropic/claude-sonnet-4-5")
    if flag == "masking_enabled":
        assert not result.report.masked and result.messages == messages
    if flag == "prefix_cache_enabled":
        assert result.breakpoints is None and result.report.caching == "unknown"
    if flag == "budget_enabled":
        assert result.report.masked                  # masking needs no budget


def test_everything_off_returns_the_same_messages():
    messages = agent_conversation(10, output=varied())
    result = make(masking_enabled=False, prefix_cache_enabled=False).process(messages, model="m")
    assert result.messages is messages and result.report.tokens_after == result.report.tokens_before


def test_a_failing_stage_is_skipped_and_the_last_valid_messages_are_used(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("bug")
    monkeypatch.setattr(masking, "mask", boom)
    chat = long_chat(14)
    result = make(compaction_enabled=True, window_tokens=8000).process(chat, model="m")
    assert "mask:RuntimeError" in result.report.stages_failed
    assert result.report.summary_index is not None              # the next stage still ran


def test_a_stage_that_breaks_an_invariant_is_undone(monkeypatch):
    original_apply = history.apply

    def corrupting(messages, *args, **kwargs):
        outcome = original_apply(messages, *args, **kwargs)
        outcome.messages = outcome.messages[:-1]                # drops the current question
        return outcome
    monkeypatch.setattr(history, "apply", corrupting)
    chat = long_chat(14)
    result = make(compaction_enabled=True, window_tokens=8000).process(chat, model="m")
    assert "history:invariant" in result.report.stages_failed
    assert any(v.startswith("history:") for v in result.report.invariant_violations)
    assert result.messages == chat and result.report.summary_index is None and result.report.hints == {}


def test_output_is_deterministic():
    chat = long_chat(14)
    a = make(compaction_enabled=True, window_tokens=8000).process(chat, model="m").messages
    b = make(compaction_enabled=True, window_tokens=8000).process(chat, model="m").messages
    assert json.dumps(a) == json.dumps(b)


def test_already_optimised_context_is_not_processed_again():
    messages = agent_conversation(10, output=varied())
    eng = make()
    once = eng.process(messages, model="gpt-4o-mini").messages
    twice = eng.process(once, model="gpt-4o-mini")
    assert twice.messages == once and not [r for r in twice.report.masked if r.reason == "age"]


def test_consecutive_requests_share_a_byte_identical_prefix():
    outputs = [log_output(120, tag=f"svc{i}") for i in range(20)]

    def conversation(rounds):
        it = iter(outputs)
        return agent_conversation(rounds, output=lambda: next(it))
    eng = make()
    a = eng.process(conversation(8), model="gpt-4o-mini").messages
    b = eng.process(conversation(9), model="gpt-4o-mini").messages
    assert json.dumps(a) == json.dumps(b[:len(a)])


def test_breakpoints_are_returned_for_anthropic_models_with_a_long_system_prompt():
    messages = agent_conversation(3)
    messages[0] = {"role": "system", "content": " ".join(f"Rule {i}: be careful with step {i}." for i in range(400))}
    result = make().process(messages, model="anthropic/claude-sonnet-4-5")
    assert result.breakpoints == [{"location": "message", "role": "system"}] and result.report.breakpoints_added


def test_llm_mode_returns_pending_summaries_for_the_callback_to_schedule():
    chat = long_chat(14)
    eng = ContextEngine(settings(compaction_enabled=True, compaction_mode="llm", compaction_model="local",
                                 window_tokens=8000), store=MemoryStore())
    result = eng.process(chat, model="m")
    assert eng.summarizer is not None and len(result.pending_summaries) == 1
    assert result.report.summary_source == "extractive"


def test_engine_module_exposes_the_result_type():
    assert engine_module.EngineResult
