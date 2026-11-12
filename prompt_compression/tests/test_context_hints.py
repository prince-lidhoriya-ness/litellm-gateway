"""The pipeline honours the context-engineering stage's hints (context_engineering/, which runs before this hook)."""

import asyncio

from prompt_compression.pipeline import PromptPipeline
from prompt_compression.prompt_compression_callback import PromptCompressionCallback, _protected_indexes

from .fakes import StubCompressor, StubDetector
from .test_pipeline import LONG, settings

SUMMARY = "[gateway: earlier conversation compacted by gateway: 2 turn(s)]\n- " + LONG


def conversation():
    return [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "first " + LONG},
        {"role": "user", "content": SUMMARY},
        {"role": "assistant", "content": "answer " + LONG},
        {"role": "user", "content": "latest " + LONG},
    ]


def test_protected_messages_are_left_verbatim_and_reported():
    pipeline = PromptPipeline(settings=settings(), detector=StubDetector(), compressor=StubCompressor())
    out, report = pipeline.process(conversation(), protected=frozenset({2}))
    assert out[2]["content"] == SUMMARY
    assert next(e for e in report.messages if e["index"] == 2)["action"] == "preserved_context_engineering"
    assert out[3]["content"] != conversation()[3]["content"]        # everything else is still compressed


def test_without_protection_the_same_message_is_compressed():
    pipeline = PromptPipeline(settings=settings(), detector=StubDetector(), compressor=StubCompressor())
    out, _ = pipeline.process(conversation())
    assert out[2]["content"] != SUMMARY


def test_the_history_route_never_drops_a_protected_message():
    s = settings(routes=frozenset({"narrative", "history"}), history_max_tokens=50, history_keep_messages=1)
    pipeline = PromptPipeline(settings=s, detector=StubDetector(), compressor=StubCompressor())
    out, report = pipeline.process(conversation(), protected=frozenset({2}))
    assert SUMMARY in [m["content"] for m in out]


def test_hints_are_read_from_metadata_and_malformed_hints_ignored():
    assert _protected_indexes({"metadata": {"context_engineering": {"hints": {"protected_indexes": [2, 5]}}}}) == {2, 5}
    assert _protected_indexes({"metadata": {"context_engineering": {"hints": {"protected_indexes": "2"}}}}) == set()
    assert _protected_indexes({"metadata": {"context_engineering": {"hints": {"protected_indexes": [True, "x"]}}}}) \
        == set()
    assert _protected_indexes({"metadata": {"context_engineering": "oops"}}) == set()
    assert _protected_indexes({}) == set()


def test_the_hook_passes_the_hint_to_the_pipeline():
    s = settings()
    pipeline = PromptPipeline(settings=s, detector=StubDetector(), compressor=StubCompressor())
    callback = PromptCompressionCallback(pipeline=pipeline, settings=s)
    data = {"model": "m", "messages": conversation(),
            "metadata": {"context_engineering": {"hints": {"protected_indexes": [2]}}}}
    out = asyncio.run(callback.async_pre_call_hook(user_api_key_dict=None, cache=None, data=data,
                                                   call_type="acompletion"))
    assert out["messages"][2]["content"] == SUMMARY
