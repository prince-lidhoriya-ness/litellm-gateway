"""Regression tests for the defects in PROJECT_AUDIT_REPORT.md (each test names its finding)."""

import asyncio
import threading
import time

import pytest
from fastapi import HTTPException

from prompt_compression import deadline as deadlines
from prompt_compression import gate, intent, redaction, router
from prompt_compression.compressor_adapter import LLMLinguaCompressor
from prompt_compression.pipeline import PromptPipeline
from prompt_compression.prompt_compression_callback import PromptCompressionCallback
from prompt_compression.segmenter import split_segments
from prompt_compression.texts import count_tokens
from prompt_compression.units import Unit

from .fakes import StubCompressor, StubDetector
from .test_pipeline import settings

SECRET = "AKIAIOSFODNN7EXAMPLE"   # AWS's documented example key id
_WORDS = "the team reviewed how the service behaves when traffic grows and noted that careful planning keeps things calm"


def prose(topic: str, sentences: int = 5) -> str:
    """Plain prose (no digits or identifiers), so the segmenter calls it prose and the compressor may touch it."""
    words = _WORDS.split()
    return " ".join(f"This part about {topic} explains that " + " ".join(words[(i * 3) % 7:]) + "." for i in range(sentences))


def chat_history(topics):
    messages = []
    for topic in topics:
        messages.append({"role": "user", "content": f"Tell me about {topic}."})
        messages.append({"role": "assistant", "content": prose(topic)})
    return messages


SELECTION = frozenset({"narrative", "passages", "records"})


def pipeline(compressor=None, **overrides):
    values = dict(routes=SELECTION, min_passages=6, min_passage_tokens=50, protect_edges=True)
    values.update(overrides)
    return PromptPipeline(settings=settings(**values), detector=StubDetector(), compressor=compressor or StubCompressor())


def run(callback, data):
    return asyncio.run(callback.async_pre_call_hook(None, None, data, "acompletion"))


def hook(compressor=None, detector=None, **overrides):
    pipeline_settings = settings(**overrides)
    pipe = PromptPipeline(settings=pipeline_settings, detector=detector or StubDetector(),
                          compressor=compressor or StubCompressor())
    return PromptCompressionCallback(pipeline=pipe, settings=pipeline_settings)


# ---- F-06: selection scope --------------------------------------------------------------------------------------

TOPICS = ["database", "billing", "kubernetes", "invoices", "latency", "migration", "pricing", "backups"]


def test_f06_earlier_turns_are_not_selected_against_the_latest_question():
    messages = chat_history(TOPICS) + [{"role": "user", "content": "Regarding the database, what should we change?"}]
    _, report = pipeline().process(messages)
    actions = [e.get("action", "") for e in report.messages if e["role"] == "assistant"]
    assert not any("selected_passages" in a for a in actions)
    assert report.selection_scope == "latest_user"


def test_f06_scope_all_restores_the_old_behaviour():
    messages = chat_history(TOPICS) + [{"role": "user", "content": "Regarding the database, what should we change?"}]
    _, report = pipeline(selection_scope="all").process(messages)
    assert any("selected_passages" in e.get("action", "") for e in report.messages if e["role"] == "assistant")


def test_f06_a_document_in_the_latest_user_message_is_still_selected():
    document = "\n\n".join(prose(t) for t in TOPICS)
    messages = [{"role": "user", "content": f"Read this.\n\n{document}\n\nWhat does it say about backups?"}]
    new, report = pipeline().process(messages)
    assert report.messages[0]["segments"]["passages_dropped"] > 0 and "backups" in new[0]["content"]


# ---- F-07: task intent ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Summarize the whole report, focusing on risks.", "Give me a TL;DR", "Translate this into German.",
    "Review the document and list all issues.", "What are the key points?", "Rewrite every paragraph more formally.",
])
def test_f07_transform_requests_are_detected(text):
    assert intent.detect(text) == intent.TRANSFORM


@pytest.mark.parametrize("text", ["What was the status of request req-17?", "Which supplier is cheapest?", ""])
def test_f07_lookups_are_detected(text):
    assert intent.detect(text) == intent.LOOKUP


def test_f07_a_summary_request_keeps_every_section():
    sections = ["revenue", "hiring", "risks", "roadmap", "churn", "security", "outlook"]
    document = "\n\n".join(prose(s) for s in sections)
    messages = [{"role": "user", "content": f"Here is our report.\n\n{document}\n\nSummarize the whole report, focusing on risks."}]
    new, report = pipeline().process(messages)
    assert report.intent == intent.TRANSFORM
    assert report.messages[0]["segments"]["passages_dropped"] == 0
    assert all(s in new[0]["content"] for s in sections)


def test_f07_intent_gate_can_be_switched_off():
    sections = ["revenue", "hiring", "risks", "roadmap", "churn", "security", "outlook"]
    document = "\n\n".join(prose(s) for s in sections)
    messages = [{"role": "user", "content": f"Here is our report.\n\n{document}\n\nSummarize the risks."}]
    _, report = pipeline(intent_gate=False).process(messages)
    assert report.intent == intent.LOOKUP and report.messages[0]["segments"]["passages_dropped"] > 0


def test_f07_transform_also_keeps_every_log_line():
    log = "\n".join(f"2026-03-14T19:06:{i:02d}Z INFO svc=api req=req-{i:04d} status=200" for i in range(30))
    messages = [{"role": "user", "content": f"Here is the log.\n\n{log}\n\nSummarize this log, mention req-0007."}]
    new, report = pipeline().process(messages)
    assert new[0]["content"].count("\n2026-") == 30 and report.messages[0]["segments"]["record_lines_dropped"] == 0


# ---- F-14: kept-reason counters ---------------------------------------------------------------------------------

def test_f14_exact_units_that_become_passages_are_not_counted_as_kept():
    texts = [f"Passage about suppliers and delivery plans number {i} with order ORD-{i:04d} and code X_{i}." for i in range(8)]
    units = [Unit(0, None, s.kind, s.subtype, s.text, s.sep) for s in split_segments("\n\n".join(texts))]
    assert any(u.kind == "exact" for u in units)
    plan = router.route(units, settings(routes=frozenset({"passages"}), min_passages=6, min_passage_tokens=10,
                                        selection_scope="all"), "suppliers", None, count_tokens)
    assert plan.passages and "exact" not in plan.reasons


# ---- F-15S: redaction guardrail ---------------------------------------------------------------------------------

def test_f15s_redact_messages_never_changes_its_input():
    messages = [{"role": "system", "content": f"key {SECRET}"},
                {"role": "user", "content": [{"type": "text", "text": f"also {SECRET}"}, {"type": "image_url"}]}]
    new, count, names = redaction.redact_messages(messages)
    assert count == 2 and names == ["aws_access_key"]
    assert SECRET in messages[0]["content"] and SECRET not in new[0]["content"]
    assert SECRET not in new[1]["content"][0]["text"] and new[1]["content"][1] == {"type": "image_url"}
    untouched = [{"role": "user", "content": "nothing here"}]
    assert redaction.redact_messages(untouched)[0] is untouched


@pytest.mark.parametrize("case", ["below_min_size", "opt_out", "system_role", "shadow", "compression_disabled"])
def test_f15s_redaction_has_no_bypass(case):
    overrides = {"redact_sensitive": True, "min_tokens": 50}
    messages = [{"role": "user", "content": prose("filler", 12) + f"\n\nmy key is {SECRET}\n\nwhat now?"}]
    metadata = {}
    if case == "below_min_size":
        messages = [{"role": "user", "content": f"my key is {SECRET}"}]
    elif case == "opt_out":
        metadata = {"prompt_compression": False}
    elif case == "system_role":
        messages = [{"role": "system", "content": f"deploy key {SECRET}"}] + [{"role": "user", "content": prose("x", 12)}]
    elif case == "shadow":
        overrides["mode"] = "shadow"
    elif case == "compression_disabled":
        overrides["enabled"] = False
    data = run(hook(**overrides), {"model": "m", "messages": messages, "metadata": metadata})
    assert all(SECRET not in str(m.get("content")) for m in data["messages"])
    assert data["metadata"]["prompt_redaction"]["redactions"] >= 1


def test_f15s_redaction_failure_rejects_the_request_even_when_failing_open(monkeypatch):
    import prompt_compression.prompt_compression_callback as module

    def broken(messages):
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "redact_messages", broken)
    with pytest.raises(HTTPException) as excinfo:
        run(hook(redact_sensitive=True, fail_mode="open"), {"model": "m", "messages": [{"role": "user", "content": SECRET}]})
    assert excinfo.value.status_code == 503


def test_f15s_redaction_is_off_by_default():
    data = run(hook(), {"model": "m", "messages": [{"role": "user", "content": f"my key is {SECRET}"}]})
    assert SECRET in data["messages"][0]["content"] and "prompt_redaction" not in data.get("metadata", {})


# ---- F-03 / F-04: request-level limits and the size gate --------------------------------------------------------

def test_f03_compressor_calls_are_capped_per_request():
    compressor = StubCompressor()
    messages = [{"role": "user" if i % 2 == 0 else "assistant", "content": prose(f"topic{'abcdefghijklmnopqrstuvwxyzabcdefghijklmn'[i]}", 6)}
                for i in range(40)] + [{"role": "user", "content": "continue"}]
    _, report = pipeline(compressor, routes=frozenset({"narrative"}), max_compress_calls_per_request=12).process(messages)
    assert len(compressor.calls) == 12 and report.compress_calls == 12
    assert report.compress_stopped == "request_budget"


def test_f03_too_large_requests_skip_the_pipeline():
    detector = StubDetector()
    data = run(hook(detector=detector, max_input_tokens=100), {"model": "m", "messages": [{"role": "user", "content": prose("x", 40)}]})
    summary = data["metadata"]["prompt_compression"]
    assert (summary["status"], summary["reason"]) == ("skipped", "too_large") and detector.checked == []


def test_f04_the_hook_gate_does_not_count_tokens():
    decision = gate.check({"messages": [{"role": "user", "content": "hi"}]}, "acompletion", settings(min_tokens=50),
                          count_tokens=False)
    assert decision.allow
    assert gate.size_check([{"role": "user", "content": "hi"}], settings(min_tokens=50)).reason == "below_min_size"


# ---- F-02: deadlines, lock waits and admission ------------------------------------------------------------------

class LockedSlowCompressor(StubCompressor):
    """Holds one lock per call, like LLMLinguaCompressor, and takes `seconds` per call."""

    def __init__(self, seconds):
        super().__init__()
        self.seconds = seconds
        self.lock = threading.Lock()
        self.finished = 0

    def compress(self, text, rate):
        with deadlines.acquire(self.lock, "compressor"):
            time.sleep(self.seconds)
            self.finished += 1
            return super().compress(text, rate)


def four_prose_messages():
    return [{"role": "user", "content": prose(f"topic{c}", 6)} for c in "abcd"] + [{"role": "user", "content": "ok, and?"}]


def test_f02_a_timed_out_request_stops_its_background_work():
    compressor = LockedSlowCompressor(0.5)
    callback = hook(compressor=compressor, timeout_s=0.8, routes=frozenset({"narrative"}))
    run(callback, {"model": "m", "messages": four_prose_messages()})
    time.sleep(1.0)
    assert compressor.finished <= 2          # it used to run all 4 calls after the request had given up
    assert callback.in_flight == 0


def test_f02_deadline_stops_compression_early_and_sends_a_valid_partial_result():
    compressor = LockedSlowCompressor(0.3)
    callback = hook(compressor=compressor, timeout_s=1.0, routes=frozenset({"narrative"}))
    data = run(callback, {"model": "m", "messages": four_prose_messages()})
    summary = data["metadata"]["prompt_compression"]
    assert summary["status"] == "ok" and summary["compress_stopped"] == "deadline"
    assert 1 <= summary["compress_calls"] < 4


def test_f02_busy_workers_skip_instead_of_queueing():
    compressor = LockedSlowCompressor(0.4)
    callback = hook(compressor=compressor, timeout_s=5, routes=frozenset({"narrative"}), max_concurrency=1)

    async def both():
        first = asyncio.create_task(callback.async_pre_call_hook(None, None, {"model": "m", "messages": four_prose_messages()}, "acompletion"))
        await asyncio.sleep(0.1)
        second = await callback.async_pre_call_hook(None, None, {"model": "m", "messages": four_prose_messages()}, "acompletion")
        return await first, second

    first, second = asyncio.run(both())
    assert first["metadata"]["prompt_compression"]["status"] == "ok"
    assert second["metadata"]["prompt_compression"] == {"status": "skipped", "reason": "busy"}
    assert callback.in_flight == 0


def test_f02_lock_wait_is_bounded_by_the_deadline():
    lock = threading.Lock()
    lock.acquire()
    try:
        with deadlines.use(deadlines.Deadline(0.05)):
            started = time.monotonic()
            with pytest.raises(deadlines.DeadlineExceeded):
                with deadlines.acquire(lock, "compressor"):
                    pass
            assert time.monotonic() - started < 0.5
    finally:
        lock.release()
    assert not deadlines.NO_DEADLINE.expired() and deadlines.NO_DEADLINE.remaining() is None


# ---- F-15 / F-19S: compressor adapter cache and pinning ---------------------------------------------------------

class FakeLingua:
    def __init__(self):
        self.calls = 0

    def compress_prompt(self, texts, rate, force_reserve_digit):
        self.calls += 1
        words = texts[0].split()
        return {"compressed_prompt": " ".join(words[::2]), "origin_tokens": len(words), "compressed_tokens": len(words) // 2}


def test_f15_compressed_outputs_are_replayed_from_the_cache():
    adapter = LLMLinguaCompressor("some/model", cache_size=2)
    adapter._compressor = fake = FakeLingua()
    first = adapter.compress("one two three four", 0.4)
    second = adapter.compress("one two three four", 0.4)
    assert fake.calls == 1 and not first.cached and second.cached and second.text == first.text
    adapter.compress("one two three four", 0.6)            # another rate is another entry
    assert fake.calls == 2


def test_f19s_default_models_are_pinned_and_others_use_main():
    from prompt_compression.settings import DEFAULT_COMPRESSION_MODEL, DEFAULT_COMPRESSION_REVISION

    assert LLMLinguaCompressor(DEFAULT_COMPRESSION_MODEL).revision == DEFAULT_COMPRESSION_REVISION
    assert LLMLinguaCompressor("other/model").revision == "main"
    assert LLMLinguaCompressor("other/model", revision="abc123").revision == "abc123"
