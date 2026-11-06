import dataclasses

import pytest

from prompt_compression import gate
from prompt_compression.settings import PipelineSettings

LONG = " ".join(["word"] * 80)


def settings(**overrides):
    return dataclasses.replace(PipelineSettings.from_env(), **{"min_tokens": 50, **overrides})


def request(content=LONG, **extra):
    return {"model": "mock", "messages": [{"role": "user", "content": content}], **extra}


def test_a_normal_chat_request_passes():
    assert gate.check(request(), "acompletion", settings()).allow


@pytest.mark.parametrize("call_type", ["aembedding", "atext_completion", "arerank"])
def test_non_chat_calls_are_ignored_silently(call_type):
    decision = gate.check(request(), call_type, settings())
    assert not decision.allow and decision.silent and decision.reason == "not_chat"


def test_a_request_without_a_messages_list_is_ignored():
    assert not gate.check({"input": "x"}, "acompletion", settings()).allow


def test_disabled_is_silent():
    decision = gate.check(request(), "acompletion", settings(enabled=False))
    assert not decision.allow and decision.silent and decision.reason == "disabled"


@pytest.mark.parametrize("metadata", [{"prompt_compression": False}, {"prompt_compression": "false"},
                                      {"disable_prompt_compression": True}, {"disable_prompt_compression": "true"}])
def test_per_request_opt_out_in_either_metadata_key(metadata):
    for key in ("metadata", "litellm_metadata"):
        decision = gate.check(request(**{key: dict(metadata)}), "acompletion", settings())
        assert not decision.allow and not decision.silent and decision.reason == "request_opt_out"


def test_opt_in_values_do_not_opt_out():
    assert gate.check(request(metadata={"prompt_compression": True}), "acompletion", settings()).allow


def test_too_few_tokens_skips_the_pipeline():
    decision = gate.check(request("hi there"), "acompletion", settings())
    assert not decision.allow and not decision.silent and decision.reason == "below_min_size"
    assert gate.check(request("hi there"), "acompletion", settings(min_tokens=0)).allow


def test_tokens_are_counted_over_every_message_and_text_part():
    messages = [{"role": "system", "content": LONG}, {"role": "user", "content": [{"type": "text", "text": "short"}]}]
    assert gate.check({"messages": messages}, "acompletion", settings()).allow
