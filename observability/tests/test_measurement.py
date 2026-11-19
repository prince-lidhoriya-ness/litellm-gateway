"""Measurement before claims: the conversation-randomised holdout, billed cost per arm, the sampled quality check
(reports/production-readiness-audit/STRATEGY.md, Phase 2.1 and 2.2)."""

import asyncio
import dataclasses
from datetime import datetime, timedelta

import pytest
from prometheus_client import REGISTRY

from observability import measurement as ms
from prompt_compression import holdout

SYSTEM = {"role": "system", "content": "You are the payments assistant."}


def sample(name, **labels):
    return REGISTRY.get_sample_value(name, labels) or 0.0


def conversation(first="Why was invoice INV-17 charged twice?", turns=0):
    messages = [SYSTEM, {"role": "user", "content": first}]
    for i in range(turns):
        messages += [{"role": "assistant", "content": f"Answer {i}"}, {"role": "user", "content": f"Follow-up {i}"}]
    return messages


def callback(**overrides):
    return ms.MeasurementCallback(dataclasses.replace(ms.MeasurementSettings(salt="s"), **overrides))


def pre_call(cb, data):
    return asyncio.run(cb.async_pre_call_hook(None, None, data, "acompletion"))


# ---- the conversation key and the arm -----------------------------------------------------------------------------

def test_the_key_is_the_same_on_every_turn_and_differs_between_conversations():
    first = holdout.conversation_key({"messages": conversation()}, "s")
    later = holdout.conversation_key({"messages": conversation(turns=3)}, "s")
    other = holdout.conversation_key({"messages": conversation("A different question about INV-99?")}, "s")
    assert first == later and first != other and len(first) == 16
    assert holdout.conversation_key({"messages": conversation()}, "other-salt") != first   # salted


def test_a_client_session_id_wins_over_the_text():
    a = holdout.conversation_key({"messages": conversation(), "metadata": {"session_id": "sess-1"}}, "s")
    b = holdout.conversation_key({"messages": conversation("Something else"), "metadata": {"session_id": "sess-1"}}, "s")
    assert a == b


def test_the_holdout_share_is_respected_and_deterministic():
    keys = [holdout.conversation_key({"messages": conversation(f"question {i}")}, "s") for i in range(4000)]
    arms = [holdout.assign(key, 0.05) for key in keys]
    share = arms.count(holdout.HOLDOUT) / len(arms)
    assert 0.04 <= share <= 0.06
    assert arms == [holdout.assign(key, 0.05) for key in keys]
    assert all(holdout.assign(key, 0.0) == holdout.TREATMENT for key in keys[:100])


def test_pre_call_writes_the_arm_to_the_metadata_and_the_spend_logs_without_text():
    data = pre_call(callback(holdout_share=0.5), {"messages": conversation(), "metadata": {}})
    decision = data["metadata"][holdout.METADATA_KEY]
    assert decision["arm"] in (holdout.HOLDOUT, holdout.TREATMENT) and len(decision["key"]) == 16
    assert data["metadata"]["spend_logs_metadata"][holdout.METADATA_KEY] == decision
    assert "INV-17" not in str(decision)


def test_opted_out_and_internal_requests_are_kept_out_of_the_comparison():
    out = pre_call(callback(holdout_share=0.5), {"messages": conversation(), "metadata": {"prompt_compression": False}})
    internal = pre_call(callback(holdout_share=0.5), {"messages": conversation(), "metadata": {"gateway_internal": True}})
    assert holdout.decision(out)["arm"] == holdout.EXCLUDED
    assert holdout.decision(internal)["arm"] == holdout.INTERNAL


def test_an_existing_decision_is_never_overwritten():
    data = {"messages": conversation(), "metadata": {holdout.METADATA_KEY: {"arm": holdout.HOLDOUT, "key": "k"}}}
    assert holdout.decision(pre_call(callback(holdout_share=0.0), data)) == {"arm": holdout.HOLDOUT, "key": "k"}


def test_settings_refuse_a_free_judge_and_bad_shares(monkeypatch):
    monkeypatch.setenv("GATEWAY_QUALITY_SAMPLE_RATE", "0.01")
    monkeypatch.setenv("GATEWAY_QUALITY_MODE", "judge")
    monkeypatch.setenv("GATEWAY_QUALITY_JUDGE_MODEL", "judge-nemotron:free")
    with pytest.raises(ValueError, match="free-tier"):
        ms.MeasurementSettings.from_env()
    monkeypatch.setenv("GATEWAY_QUALITY_ALLOW_FREE_JUDGE", "true")
    assert ms.MeasurementSettings.from_env().judge_model == "judge-nemotron:free"
    monkeypatch.setenv("GATEWAY_HOLDOUT_SHARE", "0.9")
    with pytest.raises(ValueError):
        ms.MeasurementSettings.from_env()


# ---- both stages treat a holdout conversation as shadow mode ------------------------------------------------------

def _stages():
    from context_engineering.callback import ContextEngineeringCallback
    from context_engineering.settings import ContextSettings
    from prompt_compression.pipeline import PromptPipeline
    from prompt_compression.prompt_compression_callback import PromptCompressionCallback
    from prompt_compression.tests.fakes import StubCompressor, StubDetector
    from prompt_compression.tests.test_pipeline import LONG, settings as pipeline_settings

    pc_settings = pipeline_settings(mode="enforce")
    pc = PromptCompressionCallback(PromptPipeline(pc_settings, StubDetector(), StubCompressor()), pc_settings)
    ce = ContextEngineeringCallback(settings=dataclasses.replace(ContextSettings(), mode="enforce", min_tokens=0,
                                                                 mask_trigger="always"))
    return ce, pc, LONG


@pytest.mark.parametrize("arm, sent_original", [(holdout.HOLDOUT, True), (holdout.TREATMENT, False)])
def test_a_holdout_conversation_reaches_the_provider_unoptimised(arm, sent_original):
    ce, pc, long_text = _stages()
    messages = [SYSTEM, {"role": "user", "content": "CHAT " + long_text}]
    data = {"model": "gpt-4o-mini", "messages": [dict(m) for m in messages], "litellm_call_id": "c1",
            "metadata": {holdout.METADATA_KEY: {"arm": arm, "key": "k"}}}

    async def chain():
        out = await ce.async_pre_call_hook(None, None, data, "acompletion")
        return await pc.async_pre_call_hook(None, None, out, "acompletion")

    out = asyncio.run(chain())
    summary = out["metadata"]["prompt_compression"]
    assert (out["messages"] == messages) is sent_original
    assert summary["holdout"] is sent_original
    assert summary["status"] == ("shadow" if sent_original else "ok")
    assert summary["tokens_after"] < summary["tokens_before"]          # the holdout still reports what it would save


# ---- billed cost per arm ------------------------------------------------------------------------------------------

def success_kwargs(arm, cost=0.002, prompt_tokens=1200, status="ok", call_id="c1", messages=None, before=900, after=500,
                   turn=1, internal=False):
    return {
        "litellm_call_id": call_id,
        "model": "gpt-4o-mini",
        "messages": messages or conversation(),
        "optional_params": {"temperature": 0, "max_tokens": 200},
        "litellm_params": {"metadata": {"gateway_internal": True} if internal else {}},
        "standard_logging_object": {
            "model_group": "tier-standard", "response_cost": cost, "prompt_tokens": prompt_tokens,
            "metadata": {"spend_logs_metadata": {
                holdout.METADATA_KEY: {"arm": arm, "key": "k", "turn": turn},
                "prompt_compression": {"status": status, "tokens_before": before, "tokens_after": after},
            }},
        },
    }


def response(text, cached=0):
    return {"choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": 1200, "prompt_tokens_details": {"cached_tokens": cached}}}


def test_the_billed_cost_tokens_and_conversations_are_counted_per_arm():
    cb = callback()
    labels = dict(arm="holdout", mode="shadow")
    before = {name: sample(name, **labels) for name in (
        "gateway_holdout_billed_usd_total", "gateway_holdout_prompt_tokens_total", "gateway_holdout_cached_tokens_total",
        "gateway_holdout_conversations_total", "gateway_holdout_requests_total", "gateway_holdout_latency_seconds_count")}
    start = datetime(2026, 11, 19, 10, 0, 0)
    asyncio.run(cb.async_log_success_event(success_kwargs("holdout", status="shadow"), response("ok", cached=300),
                                           start, start + timedelta(seconds=2)))
    assert sample("gateway_holdout_billed_usd_total", **labels) - before["gateway_holdout_billed_usd_total"] == \
        pytest.approx(0.002)
    assert sample("gateway_holdout_prompt_tokens_total", **labels) - before["gateway_holdout_prompt_tokens_total"] == 1200
    assert sample("gateway_holdout_cached_tokens_total", **labels) - before["gateway_holdout_cached_tokens_total"] == 300
    assert sample("gateway_holdout_conversations_total", **labels) - before["gateway_holdout_conversations_total"] == 1
    assert sample("gateway_holdout_requests_total", **labels) - before["gateway_holdout_requests_total"] == 1
    assert sample("gateway_holdout_latency_seconds_count", **labels) - before["gateway_holdout_latency_seconds_count"] == 1


def test_a_later_turn_is_not_a_new_conversation():
    cb = callback()
    labels = dict(arm="treatment", mode="enforce")
    before = sample("gateway_holdout_conversations_total", **labels)
    start = datetime(2026, 11, 19, 10, 0, 0)
    # with turn_off_message_logging the callback sees scrubbed messages: the turn comes from the pre-call decision
    asyncio.run(cb.async_log_success_event(success_kwargs("treatment", turn=3, messages=[{"role": "user", "content": "x"}]),
                                           response("ok"), start, start))
    assert sample("gateway_holdout_conversations_total", **labels) == before


def test_the_gateways_own_calls_are_counted_as_internal():
    # Quality re-runs go to the router directly: no pre-call hook gives them an arm, the metadata marks them.
    cb = callback()
    before = sample("gateway_holdout_billed_usd_total", arm="internal", mode="none")
    kwargs = success_kwargs("treatment", internal=True)
    kwargs["standard_logging_object"]["metadata"]["spend_logs_metadata"] = {}
    asyncio.run(cb.async_log_success_event(kwargs, response("ok"), datetime.now(), datetime.now()))
    assert sample("gateway_holdout_billed_usd_total", arm="internal", mode="none") - before == pytest.approx(0.002)


def test_pre_call_records_the_turn_number():
    data = pre_call(callback(), {"messages": conversation(turns=2), "metadata": {}})
    assert holdout.decision(data)["turn"] == 3


# ---- the quality check --------------------------------------------------------------------------------------------

class FakeModels:
    """Stands in for the proxy router: the re-run of the original prompt answers `baseline`, the judge `verdict`."""

    def __init__(self, baseline, verdict="EQUIVALENT"):
        self.baseline, self.verdict, self.calls = baseline, verdict, []

    async def __call__(self, model, messages, metadata, **params):
        self.calls.append({"model": model, "messages": messages, "metadata": metadata, "params": params})
        return response(self.verdict if model == "paid-judge" else self.baseline)


def run_check(cb, final_answer, status="ok", before=900, after=500):
    data = pre_call(cb, {"messages": conversation(), "metadata": {}, "litellm_call_id": "call-q"})
    assert holdout.decision(data)["arm"] == holdout.TREATMENT

    async def go():
        await cb.async_log_success_event(success_kwargs("treatment", status=status, call_id="call-q", before=before,
                                                        after=after),
                                         response(final_answer), datetime.now(), datetime.now())
        await asyncio.gather(*list(cb._tasks))
    asyncio.run(go())


def test_facts_mode_reruns_the_original_prompt_opted_out_and_finds_a_lost_value():
    models = FakeModels("INV-17 was charged twice: the retry of payment pay-118 for 129.90 USD ran after a timeout.")
    cb = ms.MeasurementCallback(dataclasses.replace(ms.MeasurementSettings(salt="s"), quality_sample_rate=1.0),
                                completion=models)
    before = sample("gateway_quality_samples_total", mode="facts", verdict="facts_missing")
    run_check(cb, "INV-17 was charged twice because a retry ran after a timeout.")
    assert sample("gateway_quality_samples_total", mode="facts", verdict="facts_missing") - before == 1
    rerun = models.calls[0]
    assert rerun["model"] == "tier-standard" and rerun["messages"] == conversation()     # the original messages
    assert rerun["metadata"]["prompt_compression"] is False and rerun["metadata"]["context_engineering"] is False
    assert rerun["metadata"]["gateway_internal"] is True and rerun["params"] == {"temperature": 0, "max_tokens": 200}


def test_facts_mode_matches_when_the_optimised_answer_keeps_every_value():
    answer = "INV-17 was charged twice: the retry of payment pay-118 for 129.90 USD ran after a timeout."
    cb = ms.MeasurementCallback(dataclasses.replace(ms.MeasurementSettings(salt="s"), quality_sample_rate=1.0),
                                completion=FakeModels(answer))
    before = sample("gateway_quality_samples_total", mode="facts", verdict="facts_match")
    run_check(cb, answer)
    assert sample("gateway_quality_samples_total", mode="facts", verdict="facts_match") - before == 1


@pytest.mark.parametrize("judge_says, verdict", [("EQUIVALENT", "equivalent"), ("DIFFERENT.", "different"),
                                                 ("I cannot tell", "unparsed")])
def test_judge_mode_records_the_judges_verdict(judge_says, verdict):
    models = FakeModels("INV-17 was charged twice.", verdict=judge_says)
    cb = ms.MeasurementCallback(dataclasses.replace(ms.MeasurementSettings(salt="s"), quality_sample_rate=1.0,
                                                    quality_mode="judge", judge_model="paid-judge"), completion=models)
    before = sample("gateway_quality_samples_total", mode="judge", verdict=verdict)
    run_check(cb, "INV-17 was charged twice.")
    assert sample("gateway_quality_samples_total", mode="judge", verdict=verdict) - before == 1
    judge = models.calls[1]
    assert judge["model"] == "paid-judge" and judge["metadata"]["gateway_internal"] is True
    assert "Answer 1:" in judge["messages"][1]["content"] and "Answer 2:" in judge["messages"][1]["content"]


def test_a_sample_whose_prompt_was_not_changed_is_not_checked():
    models = FakeModels("x")
    cb = ms.MeasurementCallback(dataclasses.replace(ms.MeasurementSettings(salt="s"), quality_sample_rate=1.0),
                                completion=models)
    before = sample("gateway_quality_dropped_total", reason="not_optimised")
    run_check(cb, "x", status="shadow")
    assert models.calls == [] and sample("gateway_quality_dropped_total", reason="not_optimised") - before == 1


def test_a_busy_checker_drops_the_sample_instead_of_queueing():
    models = FakeModels("x")
    cb = ms.MeasurementCallback(dataclasses.replace(ms.MeasurementSettings(salt="s"), quality_sample_rate=1.0,
                                                    max_inflight=1), completion=models)
    cb._inflight = 1
    before = sample("gateway_quality_dropped_total", reason="busy")
    run_check(cb, "x")
    assert models.calls == [] and sample("gateway_quality_dropped_total", reason="busy") - before == 1


def test_a_failing_check_is_counted_and_never_raises():
    async def broken(**kwargs):
        raise RuntimeError("provider down")

    cb = ms.MeasurementCallback(dataclasses.replace(ms.MeasurementSettings(salt="s"), quality_sample_rate=1.0),
                                completion=broken)
    before = sample("gateway_quality_samples_total", mode="facts", verdict="error")
    run_check(cb, "x")
    assert sample("gateway_quality_samples_total", mode="facts", verdict="error") - before == 1


def test_originals_kept_for_sampling_are_bounded():
    cb = ms.MeasurementCallback(dataclasses.replace(ms.MeasurementSettings(salt="s"), quality_sample_rate=1.0,
                                                    max_pending=3))
    for i in range(10):
        pre_call(cb, {"messages": conversation(f"q {i}"), "metadata": {}, "litellm_call_id": f"c{i}"})
    assert len(cb._pending) == 3 and list(cb._pending) == ["c7", "c8", "c9"]


def test_no_original_is_kept_when_sampling_is_off():
    cb = callback()
    pre_call(cb, {"messages": conversation(), "metadata": {}, "litellm_call_id": "c1"})
    assert not cb._pending
