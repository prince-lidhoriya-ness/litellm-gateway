import dataclasses

from prompt_compression.labels import CRITICAL, LESS_IMPORTANT, NON_SENSITIVE, SENSITIVE
from prompt_compression.pipeline import PromptPipeline
from prompt_compression.router import build_routes
from prompt_compression.settings import PipelineSettings

from .fakes import StubClassifier, StubCompressor

LONG = " ".join(["word"] * 80)


def settings(**overrides):
    base = PipelineSettings.from_env()
    values = dict(
        enabled=True, fail_mode="open", timeout_s=5, redact_sensitive=False, preserve_last_user=False,
        min_chars=50, rate_non_sensitive=0.6, rate_less_important=0.3, eager_load=False,
    )
    values.update(overrides)
    return dataclasses.replace(base, **values)


def make_pipeline(keyword_labels, **overrides):
    compressor = StubCompressor()
    pipeline = PromptPipeline(
        settings=settings(**overrides), classifier=StubClassifier(keyword_labels), compressor=compressor
    )
    return pipeline, compressor


def test_routing_table():
    routes = build_routes(settings())
    assert not routes[SENSITIVE].compress
    assert not routes[CRITICAL].compress
    assert routes[NON_SENSITIVE].compress and routes[NON_SENSITIVE].rate == 0.6
    assert routes[NON_SENSITIVE].force_reserve_digit
    assert routes[LESS_IMPORTANT].compress and routes[LESS_IMPORTANT].rate == 0.3


def test_sensitive_and_critical_are_sent_unchanged():
    pipeline, compressor = make_pipeline({"SENS": SENSITIVE, "CRIT": CRITICAL})
    messages = [
        {"role": "user", "content": "SENS " + LONG},
        {"role": "assistant", "content": "CRIT " + LONG},
        {"role": "user", "content": "CRIT again " + LONG},
    ]
    new_messages, report = pipeline.process(messages)
    assert new_messages == messages
    assert compressor.calls == []
    assert report.request_category == SENSITIVE
    assert report.tokens_before == report.tokens_after
    assert report.ratio == 1.0


def test_less_important_and_non_sensitive_use_their_rates():
    pipeline, compressor = make_pipeline({"CHAT": LESS_IMPORTANT, "PLAIN": NON_SENSITIVE})
    messages = [{"role": "user", "content": "CHAT " + LONG}, {"role": "user", "content": "PLAIN " + LONG}]
    new_messages, report = pipeline.process(messages)
    assert [(label, rate) for _, label, rate in compressor.calls] == [(LESS_IMPORTANT, 0.3), (NON_SENSITIVE, 0.6)]
    assert all(len(m["content"]) < len(o["content"]) for m, o in zip(new_messages, messages))
    assert report.tokens_after < report.tokens_before
    assert report.ratio > 1
    assert report.request_category == NON_SENSITIVE


def test_preserves_system_tool_messages_roles_and_order():
    pipeline, compressor = make_pipeline({}, )  # everything non_sensitive -> compressible
    messages = [
        {"role": "system", "content": "SYSTEM " + LONG},
        {"role": "developer", "content": "DEV " + LONG},
        {"role": "user", "content": "question " + LONG},
        {"role": "assistant", "content": None,
         "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "f", "arguments": "{\"a\": 1}"}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "TOOL RESULT " + LONG},
        {"role": "user", "content": "latest " + LONG},
    ]
    original = [dict(m) for m in messages]
    new_messages, report = pipeline.process(messages)
    assert [m["role"] for m in new_messages] == [m["role"] for m in messages]
    for index in (0, 1, 3, 4):
        assert new_messages[index] == original[index]
    assert new_messages[2]["content"] != original[2]["content"]
    assert messages == original  # input list is not mutated
    actions = {entry["index"]: entry["action"] for entry in report.messages}
    assert actions[0] == actions[1] == actions[3] == actions[4] == "preserved_role"


def test_preserve_last_user_setting():
    pipeline, compressor = make_pipeline({}, preserve_last_user=True)
    messages = [{"role": "user", "content": "older " + LONG}, {"role": "user", "content": "latest " + LONG}]
    new_messages, report = pipeline.process(messages)
    assert new_messages[1] == messages[1]
    assert new_messages[0] != messages[0]
    assert report.messages[1]["action"] == "preserved_last_user"


def test_short_messages_are_not_compressed():
    pipeline, compressor = make_pipeline({"CHAT": LESS_IMPORTANT}, min_chars=200)
    new_messages, report = pipeline.process([{"role": "user", "content": "CHAT hi there!"}])
    assert compressor.calls == []
    assert report.messages[0]["action"] == "below_min_chars"


def test_multimodal_parts_only_text_is_touched():
    pipeline, compressor = make_pipeline({})
    image = {"type": "image_url", "image_url": {"url": "https://example.com/cat.png"}}
    messages = [{"role": "user", "content": [{"type": "text", "text": "describe " + LONG}, image]}]
    new_messages, _ = pipeline.process(messages)
    assert new_messages[0]["content"][1] == image
    assert new_messages[0]["content"][0]["text"] != messages[0]["content"][0]["text"]


def test_redact_sensitive_replaces_pii_and_skips_compression():
    pipeline, compressor = make_pipeline({"SENS": SENSITIVE}, redact_sensitive=True)
    text = "SENS my email is jane.doe@example.com, phone +1 555 013 2287. " + LONG
    new_messages, report = pipeline.process([{"role": "user", "content": text}])
    content = new_messages[0]["content"]
    assert "jane.doe@example.com" not in content and "[EMAIL]" in content and "[PHONE]" in content
    assert compressor.calls == []
    assert report.messages[0]["action"] == "redacted"


def test_redaction_off_by_default_leaves_sensitive_text_verbatim():
    pipeline, _ = make_pipeline({"SENS": SENSITIVE})
    text = "SENS my email is jane.doe@example.com " + LONG
    new_messages, _ = pipeline.process([{"role": "user", "content": text}])
    assert new_messages[0]["content"] == text
