"""Observation masking: duplicate folding, batched age masking, guards, stubs, recovery."""

import json

from context_engineering import masking
from context_engineering.analyzer import analyze
from context_engineering.store import MemoryStore, NullStore, RedisStore
from context_engineering.structures import DUPLICATE_MARKER, STUB_MARKER

from .builders import agent_conversation, error_output, json_output, log_output, settings, tool_round

ALL = frozenset({"dedupe", "mask"})


def varied(n):
    counter = iter(range(10**6))
    return lambda: log_output(n, tag=f"svc{next(counter)}")


def run(messages, store=None, techniques=ALL, **overrides):
    s = settings(**overrides)
    store = store if store is not None else MemoryStore()
    out, records, decisions = masking.mask(messages, analyze(messages), s, techniques, store)
    return out, records, decisions, store


def tool_indexes(messages):
    return [i for i, m in enumerate(messages) if m.get("role") == "tool"]


def test_old_large_outputs_are_masked_in_batches_and_recent_ones_kept():
    messages = agent_conversation(9, output=varied(120))
    out, records, _, _ = run(messages, observation_keep_recent=3, observation_batch=4)
    tools = tool_indexes(messages)
    # 9 candidates, 3 kept, surplus 6 -> one batch of 4
    assert [r.index for r in records] == tools[:4]
    for index in tools[4:]:
        assert out[index] == messages[index]
    assert all(r.reason == "age" and r.tokens_after < r.tokens_before for r in records)


def test_the_masked_set_only_changes_at_batch_boundaries():
    outputs = [log_output(120, tag=f"svc{i}") for i in range(20)]

    def conversation(rounds):
        it = iter(outputs)
        return agent_conversation(rounds, output=lambda: next(it))
    counts = [len(run(conversation(n), observation_keep_recent=3, observation_batch=4)[1]) for n in range(3, 13)]
    assert counts == [0, 0, 0, 0, 4, 4, 4, 4, 8, 8]
    # Two consecutive requests inside one batch step: the earlier request is a byte-identical prefix of the later one.
    a = run(conversation(8))[0]
    b = run(conversation(9))[0]
    assert json.dumps(a) == json.dumps(b[:len(a)])


def test_masking_is_deterministic_and_refs_are_content_hashes():
    messages = agent_conversation(9, output=varied(120))
    first = run(messages)[0]
    second = run(messages)[0]
    assert json.dumps(first) == json.dumps(second)
    record = run(messages)[1][0]
    assert record.ref == "obs_" + analyze(messages).items[record.index].content_sha[:12]


def test_tool_call_ids_names_and_roles_are_kept():
    messages = agent_conversation(9, output=varied(120))
    out, records, _, _ = run(messages)
    for record in records:
        before, after = messages[record.index], out[record.index]
        assert after["role"] == "tool" and after["tool_call_id"] == before["tool_call_id"]
        assert after["content"].startswith(STUB_MARKER)
    assert [m.get("role") for m in out] == [m.get("role") for m in messages]


def test_stub_keeps_error_lines_and_lines_the_next_answer_names_verbatim():
    messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "go"}]
    output = log_output(150)
    lines = output.splitlines()
    lines[70] = "2026-03-14T19:10:00Z ERROR svc=cart req=req-badbad status=500 latency_ms=9000 user=u-70"
    output = "\n".join(lines)
    messages += tool_round("c0", "read_logs", {}, output, "The failing request is req-000033, see above.")
    for i in range(1, 9):
        messages += tool_round(f"c{i}", "read_logs", {}, log_output(120, tag=f"x{i}"), "ok")
    out, records, _, _ = run(messages)
    stub = out[3]["content"]
    assert lines[70] in stub                                  # error line, verbatim
    assert next(line for line in lines if "req=req-000033" in line) in stub   # named by the follow-up answer
    assert lines[0] in stub and "obs_" in stub and "tool=read_logs" in stub
    for line in stub.splitlines()[2:-1]:
        assert line in output                                 # nothing invented


def test_json_outputs_get_a_structure_line_and_stay_verbatim_elsewhere():
    messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "go"}]
    for i in range(8):
        messages += tool_round(f"c{i}", "list_orders", {}, json_output(80 + i), "ok")
    out, records, _, _ = run(messages)
    assert records and "Structure: JSON array of 80 items; item keys: customer, order_id, total" in out[3]["content"]


def test_byte_identical_outputs_are_folded_into_a_pointer_to_the_first_copy():
    same = log_output(30)
    messages = agent_conversation(4, output=lambda: same)
    out, records, _, _ = run(messages, techniques=frozenset({"dedupe"}))
    tools = tool_indexes(messages)
    assert out[tools[0]] == messages[tools[0]]                 # the first copy stays: prefix unchanged
    assert [r.index for r in records] == tools[1:] and all(r.reason == "duplicate" for r in records)
    assert out[tools[1]]["content"].startswith(DUPLICATE_MARKER) and f"message #{tools[0]}" in out[tools[1]]["content"]


def test_outputs_after_the_last_assistant_message_are_never_touched():
    messages = agent_conversation(9, output=varied(120), pending_last=True)
    out, records, _, _ = run(messages)
    assert out[-1] == messages[-1] and out[-2] == messages[-2]
    assert len(messages) - 1 not in {r.index for r in records}


def test_recent_error_outputs_are_kept_for_active_debugging():
    messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "fix the tests"}]
    for i in range(8):
        messages += tool_round(f"c{i}", "run_tests", {}, log_output(120, tag=f"t{i}"), "next")
    messages += tool_round("err", "run_tests", {}, error_output(400), "One failure in test_login, investigating.")
    messages += tool_round("c9", "read_file", {}, log_output(120, tag="t9"), "reading")
    out, records, decisions, _ = run(messages, observation_keep_recent=0, observation_batch=1)
    error_index = next(i for i, m in enumerate(messages) if m.get("tool_call_id") == "err")
    assert error_index not in {r.index for r in records} and out[error_index] == messages[error_index]
    assert any("active debugging" in d for d in decisions)


def test_mentioning_a_ref_restores_that_observation():
    messages = agent_conversation(9, output=varied(120))
    _, records, _, _ = run(messages)
    ref = records[0].ref
    follow = messages + [{"role": "user", "content": f"Show me {ref} in full please."}]
    out, again, decisions, _ = run(follow)
    assert records[0].index not in {r.index for r in again}
    assert out[records[0].index] == follow[records[0].index]
    assert any("ref was mentioned" in d for d in decisions)


def test_originals_are_stored_and_recoverable():
    messages = agent_conversation(9, output=varied(120))
    out, records, _, store = run(messages)
    entry = masking.recover_observation(store, records[0].ref)
    assert entry["content"] == messages[records[0].index]["content"]
    assert entry["tool_call_id"] == messages[records[0].index]["tool_call_id"]
    assert records[0].stored and "original stored" in out[records[0].index]["content"]


def test_with_no_store_the_stub_says_so():
    messages = agent_conversation(9, output=varied(120))
    out, records, _, _ = run(messages, store=NullStore())
    assert not records[0].stored and "original not stored" in out[records[0].index]["content"]


def test_small_outputs_and_gateway_stubs_are_left_alone():
    messages = agent_conversation(9, output=varied(5))
    assert run(messages)[1] == []
    masked = run(agent_conversation(9, output=varied(120)))[0]
    assert [r for r in run(masked)[1] if r.reason == "age"] == []       # idempotent


def test_multipart_text_content_is_masked_and_non_text_parts_are_not():
    messages = agent_conversation(9, output=varied(120))
    tools = tool_indexes(messages)
    messages[tools[0]] = {**messages[tools[0]], "content": [{"type": "text", "text": log_output(120, tag="mp")}]}
    messages[tools[1]] = {**messages[tools[1]], "content": [{"type": "image_url", "image_url": {"url": "x"}}]}
    out, records, _, _ = run(messages)
    masked = {r.index for r in records}
    assert tools[0] in masked and isinstance(out[tools[0]]["content"], list)
    assert tools[1] not in masked


class FakeRedis:
    def __init__(self):
        self.data = {}

    def set(self, key, value, ex=None):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key)


def test_redis_store_never_receives_sensitive_content_by_default():
    secret = "AKIA" + "IOSFODNN7EXAMPLE"
    messages = agent_conversation(9, output=varied(120))
    tools = tool_indexes(messages)
    messages[tools[0]] = {**messages[tools[0]], "content": log_output(120, tag="s") + f"\naws_key={secret}"}
    store = RedisStore(FakeRedis(), ttl_s=60)
    _, records, _, _ = run(messages, store=store)
    by_index = {r.index: r for r in records}
    assert not by_index[tools[0]].stored and by_index[tools[1]].stored
    assert all(secret not in value for value in store.client.data.values())
    assert store.get(by_index[tools[1]].ref)["content"] == messages[tools[1]]["content"]


def test_redis_errors_never_raise():
    class Broken:
        def set(self, *a, **k):
            raise ConnectionError("down")

        def get(self, *a, **k):
            raise ConnectionError("down")
    store = RedisStore(Broken())
    assert store.put("obs_x", {"a": 1}) is False and store.get("obs_x") is None and store.errors == 2


def test_memory_store_evicts_and_expires():
    store = MemoryStore(max_items=2, ttl_s=3600)
    for ref in ("a", "b", "c"):
        store.put(ref, {"ref": ref})
    assert store.get("a") is None and store.get("c") == {"ref": "c"}
    expired = MemoryStore(ttl_s=-1)
    expired.ttl_s = 1e-9
    expired.put("x", {})
    import time
    time.sleep(0.05)
    assert expired.get("x") is None
