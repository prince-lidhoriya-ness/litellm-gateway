"""Masking fidelity (reports/production-readiness-audit/STRATEGY.md, H1 and Phase 1.6/1.7).

  * masking runs only under budget pressure by default; the audit's case H (an old config dump asked about at 14%
    utilization) keeps the value instead of a stub the model then filled with an invented one
  * every stub says that values it does not show are unknown and must not be guessed
  * key lines include lines named by any user or assistant message after the output, up to the tool result that
    completed its mask batch, and the stub stays byte-identical when later messages arrive
  * an output that a later duplicate points to is never masked (the re-fetched content would be lost again)
  * a tool call repeating a masked observation's call is counted (the refetch loss signal)
"""

import copy
import json

from context_engineering import masking
from context_engineering.analyzer import analyze
from context_engineering.engine import ContextEngine
from context_engineering.store import MemoryStore
from context_engineering.structures import DUPLICATE_MARKER, STUB_MARKER

from .builders import agent_conversation, log_output, settings, tool_round

ALL = frozenset({"dedupe", "mask"})


def varied(n):
    counter = iter(range(10**6))
    return lambda: log_output(n, tag=f"svc{next(counter)}")


def mask(messages, **overrides):
    return masking.mask(messages, analyze(messages), settings(**overrides), ALL, MemoryStore())


def tool_index(round_number: int) -> int:
    return 3 + 3 * round_number          # [system, user] then (assistant call, tool, assistant reply) per round


def reply_index(round_number: int) -> int:
    return 4 + 3 * round_number


# ---- case H: the audit's agent loop -------------------------------------------------------------------------------

def config_dump() -> str:
    lines = [f"setting_{i:03d} = value_{i * 7 % 101}" for i in range(220)]
    lines[140] = "db.pool.max_size = 17   # raised from 10 after the March incident"
    return "\n".join(lines)


def grep_output(tag: int) -> str:
    return "\n".join(f"src/{tag}/mod_{i}.py:{10 + i}: logger.info('processed batch %s', batch_id)" for i in range(60))


def case_h() -> list:
    messages = [{"role": "system", "content": "You are a debugging agent. Never edit files under /etc."},
                {"role": "user", "content": "Find why the nightly import job hangs. Do not restart production services."}]
    messages += tool_round("call_0", "read_file", {"path": "config/app.conf"}, config_dump(),
                           "I read the config; nothing obviously wrong yet.")
    for i in range(1, 8):
        messages += tool_round(f"call_{i}", "grep", {"pattern": "batch", "dir": f"src/{i}"}, grep_output(i),
                               f"Searched src/{i}; the logging looks normal.")
    messages.append({"role": "user",
                     "content": "Earlier you read the config. What was db.pool.max_size set to, and was there a comment?"})
    return messages


def test_case_h_low_utilization_masks_nothing_and_the_value_survives():
    messages = case_h()
    result = ContextEngine(settings(), store=MemoryStore()).process(messages, model="gpt-4o-mini")
    text = json.dumps(result.messages)
    assert result.report.pressure in ("low", "moderate")
    assert not [r for r in result.report.masked if r.reason == "age"]
    assert "db.pool.max_size = 17   # raised from 10 after the March incident" in text


def test_case_h_with_the_old_always_trigger_the_stub_forbids_guessing():
    messages = case_h()
    result = ContextEngine(settings(mask_trigger="always"), store=MemoryStore()).process(messages, model="gpt-4o-mini")
    masked = [r for r in result.report.masked if r.reason == "age"]
    assert masked                                     # what the audit measured: masked at low utilization
    stub = result.messages[masked[0].index]["content"]
    assert stub.startswith(STUB_MARKER)
    assert "Values not shown above are unknown to you; do not guess them." in stub
    assert "Re-run the tool (same arguments) if you need them" in stub


# ---- richer, byte-stable key lines --------------------------------------------------------------------------------

def test_key_lines_include_records_a_later_turn_names_before_the_batch_was_cut():
    messages = agent_conversation(9, output=varied(120))
    for round_number in range(1, 9):             # the builder's replies name ids that every log shares; neutral here
        messages[reply_index(round_number)]["content"] = "Checking the next file."
    # Round 2's reply, after output 0 and before the tool result that completes output 0's batch, names req-00002a.
    messages[reply_index(2)]["content"] = "Also note req-00002a in the first log."
    out, records, _ = mask(messages)
    first = next(r for r in records if r.reason == "age" and r.index == tool_index(0))
    stub = out[first.index]["content"]
    assert any("req=req-00002a" in line for line in stub.splitlines())


def test_stubs_stay_byte_identical_when_later_messages_mention_other_records():
    messages = agent_conversation(9, output=varied(120))
    before, records, _ = mask(messages)
    later = copy.deepcopy(messages) + [{"role": "user", "content": "And what about req-000032 in the first log?"}]
    after, later_records, _ = mask(later)
    assert [r.index for r in records] == [r.index for r in later_records]
    for record in records:
        assert after[record.index]["content"] == before[record.index]["content"]
    first = next(r for r in records if r.index == tool_index(0))
    assert "req=req-000032" not in after[first.index]["content"]


# ---- a duplicate's target is never masked -------------------------------------------------------------------------

def test_an_output_a_later_duplicate_points_to_is_not_masked():
    outputs = iter([log_output(120, tag="first")] + [log_output(120, tag=f"svc{i}") for i in range(1, 8)]
                   + [log_output(120, tag="first")])
    messages = agent_conversation(9, output=lambda: next(outputs))
    out, records, decisions = mask(messages)
    duplicate = [r for r in records if r.reason == "duplicate"]
    assert duplicate and duplicate[0].index == tool_index(8)
    assert out[tool_index(8)]["content"].startswith(DUPLICATE_MARKER)
    # the pointer leads to message #3, which is still there in full
    assert out[tool_index(0)]["content"] == messages[tool_index(0)]["content"]
    assert not any(r.index == tool_index(0) for r in records)
    assert any("later duplicate points to them" in d for d in decisions)


# ---- refetch counter ----------------------------------------------------------------------------------------------

def test_a_repeated_call_of_a_masked_observation_is_counted_as_a_refetch():
    messages = agent_conversation(9, output=varied(120))
    _, records, _ = mask(messages)
    assert any(r.reason == "age" and r.index == tool_index(0) for r in records)
    messages += [{"role": "assistant", "content": None, "tool_calls": [
        {"id": "call_again", "type": "function",
         "function": {"name": "read_logs", "arguments": json.dumps({"file": "logs/cart-0.log"})}}]}]
    assert masking.refetch_count(messages, records, analyze(messages)) == 1
    other = messages[:-1] + [{"role": "assistant", "content": None, "tool_calls": [
        {"id": "call_new", "type": "function",
         "function": {"name": "read_logs", "arguments": json.dumps({"file": "logs/other.log"})}}]}]
    assert masking.refetch_count(other, records, analyze(other)) == 0


def test_the_engine_reports_refetches():
    messages = agent_conversation(9, output=varied(120))
    messages += [{"role": "assistant", "content": None, "tool_calls": [
        {"id": "call_again", "type": "function",
         "function": {"name": "read_logs", "arguments": json.dumps({"file": "logs/cart-0.log"})}}]},
        {"role": "tool", "tool_call_id": "call_again", "content": "short"}]
    result = ContextEngine(settings(mask_trigger="always"), store=MemoryStore()).process(messages, model="gpt-4o-mini")
    assert result.report.refetches == 1 and result.report.as_metadata()["refetches"] == 1
