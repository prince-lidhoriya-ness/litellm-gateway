"""Attribution: per-technique savings add up, are never double-counted, and the success hook records them once."""

import itertools

from context_engineering import callback as cb
from context_engineering import tokens as tk
from context_engineering.engine import ContextEngine
from context_engineering.store import MemoryStore

from .builders import agent_conversation, log_output, long_chat, settings


def test_masking_and_dedup_savings_are_reported_separately_and_sum_to_the_stage_total():
    counter = itertools.count()
    messages = agent_conversation(10, output=lambda: log_output(120, tag=f"s{next(counter)}"))
    same = log_output(80, tag="dup")
    messages[6]["content"] = same
    messages[9]["content"] = same
    report = ContextEngine(settings(), store=MemoryStore()).process(messages, model="gpt-4o-mini").report
    saved = report.saved_by_technique
    assert saved["deduplication"] > 0 and saved["masking"] > 0
    assert sum(saved.values()) == report.tokens_before - report.tokens_after


def test_history_savings_are_credited_to_compaction_or_to_jit():
    chat = long_chat(14)
    compaction = ContextEngine(settings(compaction_enabled=True, window_tokens=8000), store=MemoryStore())
    report = compaction.process(chat, model="m").report
    assert set(report.saved_by_technique) == {"compaction"}
    assert report.saved_by_technique["compaction"] == report.tokens_before - report.tokens_after
    jit = ContextEngine(settings(jit_enabled=True, window_tokens=8000, cache_support="off"), store=MemoryStore())
    assert set(jit.process(chat, model="m").report.saved_by_technique) == {"jit_retrieval"}


def test_retrieved_and_restored_counts_are_reported():
    chat = long_chat(14, last_question="How does the onboarding batch job read from the marketing queue?")
    eng = ContextEngine(settings(compaction_enabled=True, jit_enabled=True, window_tokens=8000, cache_support="off"),
                        store=MemoryStore())
    first = eng.process(chat, model="m").report
    assert first.retrieved_turns >= 1
    ref = next(r.ref for r in first.history if r.action == "compacted")
    chat[-1]["content"] += f" Also restore {ref}."
    assert eng.process(chat, model="m").report.restored["turns"] == 1


def test_success_hook_attributes_each_technique_once():
    summary = {"status": "ok", "saved_by_technique": {"masking": 900, "compaction": 400}}
    compression = {"status": "ok", "tokens_before": 2000, "tokens_after": 1500}
    contributions = cb.ContextEngineeringCallback._attribute(summary, compression, 300, {"model": "gpt-4o-mini"})
    assert contributions == {"masking": 900, "compaction": 400, "prompt_compression": 500, "provider_cache": 300}


def test_shadow_and_skipped_stages_attribute_nothing_of_their_own():
    shadow = cb.ContextEngineeringCallback._attribute({"status": "shadow", "saved_by_technique": {"masking": 9}},
                                                      {"status": "shadow", "tokens_before": 9, "tokens_after": 1}, 0, {})
    assert shadow == {}
    compression_only = cb.ContextEngineeringCallback._attribute(
        {"status": "skipped"}, {"status": "ok", "tokens_before": 100, "tokens_after": 60}, 0, {})
    assert compression_only == {"prompt_compression": 40}


def test_prices_come_from_the_model_map():
    price, cache_price = cb._prices({"model": "gpt-4o-mini", "custom_llm_provider": "openai"})
    assert price > 0 and 0 < cache_price < price
    assert cb._prices({"model": "no-such-model"}) == (0.0, 0.0)


def test_attribution_runs_from_the_success_event_without_a_context_summary(monkeypatch):
    seen = {}
    monkeypatch.setattr(cb.ContextEngineeringCallback, "_attribute",
                        staticmethod(lambda s, c, cached, p: seen.update(c=c, cached=cached) or {}))
    kwargs = {"standard_logging_object": {"model": "m", "metadata": {"spend_logs_metadata": {
        "prompt_compression": {"status": "ok", "tokens_before": 10, "tokens_after": 5}}}}}
    import asyncio
    from types import SimpleNamespace
    asyncio.run(cb.ContextEngineeringCallback(settings=settings()).async_log_success_event(
        kwargs, SimpleNamespace(usage=SimpleNamespace(prompt_tokens=5, prompt_tokens_details=None)), None, None))
    assert seen["c"]["tokens_after"] == 5 and seen["cached"] == 0
    assert tk.CALIBRATION is not None
