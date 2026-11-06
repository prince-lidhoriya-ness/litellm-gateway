"""Actions carry out the plan: keep does nothing, select drops whole units, compress calls LLMLingua-2 under a cap."""

import json

from prompt_compression import actions, router
from prompt_compression.texts import count_tokens
from prompt_compression.units import Unit
from prompt_compression.segmenter import split_segments

from .fakes import RateStubCompressor, StubCompressor
from .test_pipeline import (
    CODE_BLOCK, JSON_BLOCK, LOG_BLOCK, PROSE_1, PROSE_2, PROSE_3, join, log_block, settings,
)


def run(text, compressor=None, last_user=None, query=None, **overrides):
    """Route and execute one message; returns (text after the actions, outcome, plan, compressor)."""
    compressor = compressor or StubCompressor()
    config = settings(**overrides)
    units = [Unit(0, None, s.kind, s.subtype, s.text, s.sep) for s in split_segments(text)]
    plan = router.route(units, config, query, last_user, count_tokens)
    outcome = actions.execute(plan, config, compressor, count_tokens)
    return "".join(u.full for u in units if not u.dropped), outcome, plan, compressor


# ---- compress ---------------------------------------------------------------------------------------------------

def test_only_prose_reaches_the_compressor_and_everything_else_is_byte_for_byte():
    text = join(PROSE_1, LOG_BLOCK, PROSE_2, JSON_BLOCK, "MAX_WINDOW_PB = 259", CODE_BLOCK, "```python\nx = 1\n```")
    out, outcome, _, compressor = run(text)
    for protected in (LOG_BLOCK, JSON_BLOCK, "MAX_WINDOW_PB = 259", CODE_BLOCK, "```python\nx = 1\n```"):
        assert protected in out
    assert sorted(c[0] for c in compressor.calls) == sorted([PROSE_1, PROSE_2])
    assert PROSE_1 not in out and PROSE_2 not in out
    assert outcome.acted[0] == ["compressed"] and outcome.stats[0]["compressed_blocks"] == 2


def test_consecutive_prose_blocks_go_in_one_call_and_the_separator_before_a_protected_block_survives():
    out, _, _, compressor = run(join(PROSE_1, PROSE_2, PROSE_3, LOG_BLOCK))
    assert len(compressor.calls) == 1 and compressor.calls[0][0] == join(PROSE_1, PROSE_2, PROSE_3)
    assert out.endswith("\n\n" + LOG_BLOCK)


def test_nothing_to_compress_means_no_call():
    text = join(LOG_BLOCK, CODE_BLOCK, JSON_BLOCK)
    out, outcome, _, compressor = run(text)
    assert out == text and compressor.calls == [] and outcome.acted == {}


def test_short_prose_is_left_alone():
    text = join("Thanks, that is all.", LOG_BLOCK)
    out, _, _, compressor = run(text, min_chars=100)
    assert out == text and compressor.calls == []


def test_the_configured_rate_is_what_the_compressor_gets():
    _, _, _, compressor = run(join(PROSE_1, LOG_BLOCK), rate=0.31)
    assert [rate for _, rate in compressor.calls] == [0.31]


# ---- ratio cap --------------------------------------------------------------------------------------------------

_CYCLE = ["market", "season", "supplier", "region", "delivery", "customer", "review"]
LONG_PROSE = " ".join(_CYCLE[i % 7] for i in range(240))


def test_ratio_above_the_cap_is_retried_lighter_and_then_accepted():
    out, outcome, _, compressor = run(LONG_PROSE, RateStubCompressor(), rate=0.3, max_ratio=3.0, min_chars=50)
    assert len(compressor.calls) == 2 and compressor.calls[1][1] > compressor.calls[0][1]
    assert outcome.acted[0] == ["compressed"]
    assert count_tokens(LONG_PROSE) / count_tokens(out) <= 3.0 * 1.05


def test_a_compressor_that_cannot_be_kept_under_the_cap_is_ignored():
    out, outcome, _, _ = run(LONG_PROSE, RateStubCompressor(floor=0.1), rate=0.3, max_ratio=3.0)
    assert out == LONG_PROSE and outcome.stats[0]["ratio_cap_hits"] == 1 and 0 not in outcome.acted


def test_a_result_that_is_not_shorter_is_ignored():
    class NoGain(StubCompressor):
        def compress(self, text, rate):
            output = super().compress(text, rate)
            return type(output)(text, output.origin_tokens, output.origin_tokens)

    text = join(PROSE_1, LOG_BLOCK)
    assert run(text, NoGain())[0] == text


def test_compress_calls_are_capped_per_message_and_the_longest_runs_go_first():
    blocks = [PROSE_1, LOG_BLOCK, PROSE_2 + " " + PROSE_3, JSON_BLOCK, PROSE_1 + " " + PROSE_2 + " " + PROSE_3, CODE_BLOCK, PROSE_2]
    _, outcome, _, compressor = run(join(*blocks), max_compress_calls=2)
    assert len(compressor.calls) == 2 and {c[0] for c in compressor.calls} == {blocks[4], blocks[2]}
    assert outcome.stats[0]["compressed_blocks"] == 2


# ---- select: passages -------------------------------------------------------------------------------------------

def passage_text():
    fillers = [
        f"Filler paragraph number {i} about suppliers, delivery times, warehouse staffing plans and regional customer "
        f"feedback gathered during the quarterly review meetings held across several offices, where the teams compared "
        f"forecasts, discussed seasonal demand and agreed on the next steps for each product line." for i in range(9)
    ]
    relevant = ("The Zorvex programme delivers cold-chain loggers to regional clinics, and its coordinators report "
                "every month to the health ministry about stock levels, spoilage and transport delays in remote districts.")
    fillers[4] = relevant
    return join("Use the passages below to answer.", *fillers, "What does the Zorvex programme deliver?"), relevant


def test_passages_the_question_does_not_need_are_dropped_and_never_reach_the_compressor():
    text, relevant = passage_text()
    out, outcome, _, compressor = run(text, last_user=0, query="What does the Zorvex programme deliver?",
                                      routes=frozenset({"passages"}), protect_edges=True)
    assert relevant in out and out.startswith("Use the passages") and out.endswith("What does the Zorvex programme deliver?")
    assert 0 < outcome.stats[0]["passages_dropped"] < 9 and compressor.calls == []
    assert outcome.acted[0] == ["selected_passages"] and count_tokens(out) < count_tokens(text)


def test_passages_without_a_lexical_signal_drop_nothing():
    text, _ = passage_text()
    out, outcome, _, _ = run(text, last_user=0, query="Tell me more about it", routes=frozenset({"passages"}), protect_edges=True)
    assert out == text and outcome.stats.get(0, {}).get("passages_dropped", 0) == 0


def test_dropped_passages_do_not_block_compression_of_the_ones_that_stay():
    text, relevant = passage_text()
    out, outcome, _, compressor = run(text, last_user=0, query="What does the Zorvex programme deliver?",
                                      routes=frozenset({"passages", "narrative"}), protect_edges=True)
    assert outcome.acted[0] == ["selected_passages", "compressed"]
    assert all("Filler paragraph number 0 " not in call[0] for call in compressor.calls)


# ---- select: records ---------------------------------------------------------------------------------------------

def test_records_keep_the_named_record_and_its_neighbours():
    question = "What was the latency_ms value of request req-00001a?"
    out, outcome, _, compressor = run(join("Answer from the log.", log_block(), question), last_user=0, query=question,
                                      routes=frozenset({"records"}), protect_edges=True)
    kept = [line for line in out.splitlines() if line.startswith("2026-")]
    assert any("req-00001a" in line for line in kept) and 1 <= len(kept) <= 3
    assert outcome.stats[0]["record_lines_dropped"] == 40 - len(kept) and compressor.calls == []


def test_a_label_line_above_the_data_stays():
    question = "What was the latency_ms value of request req-00001a?"
    out, outcome, _, _ = run(join("Answer from the log.", "Here is the log:\n" + log_block(), question), last_user=0,
                             query=question, routes=frozenset({"records"}), protect_edges=True)
    assert "Here is the log:\n2026-" in out and outcome.stats[0]["record_lines_dropped"] > 30


def test_short_blocks_and_unnamed_questions_are_left_alone():
    question = "What was the latency of request req-000002?"
    ctx = dict(last_user=0, query=question, routes=frozenset({"records"}), protect_edges=True)
    assert run(join("Read.", log_block(5), question), **ctx)[0].count("2026-") == 5
    ctx["query"] = "Summarise the log."
    assert run(join("Read.", log_block(), "Summarise the log."), **ctx)[0].count("2026-") == 40


def test_a_json_array_stays_valid_when_the_last_record_is_the_match():
    records = ",\n".join(f'  {{"order_id": "ORD-{i:04d}", "customer": "c-{i}", "total": {i}.5}}' for i in range(40))
    question = "What is the total of order ORD-0039?"
    out, _, _, _ = run(join("Use the data.", f"[\n{records}\n]", question), last_user=0, query=question,
                       routes=frozenset({"records"}), protect_edges=True)
    parsed = json.loads(out.split("\n\n")[1])
    assert any(item["order_id"] == "ORD-0039" for item in parsed) and len(parsed) < 40


# ---- keep with redaction -----------------------------------------------------------------------------------------

def test_sensitive_spans_are_redacted_only_when_asked():
    text = "Write to jane.doe@example.com about the plan."
    plan_units = [Unit(0, None, "prose", "prose", text, sensitive=True, rule_hits=("email",))]
    config = settings(redact_sensitive=True)
    plan = router.route(plan_units, config, None, None, count_tokens)
    outcome = actions.execute(plan, config, StubCompressor(), count_tokens)
    assert plan_units[0].text == "Write to [EMAIL] about the plan." and outcome.acted[0] == ["redacted"]
    plain_units = [Unit(0, None, "prose", "prose", text, sensitive=True, rule_hits=("email",))]
    plain = router.route(plain_units, settings(), None, None, count_tokens)
    actions.execute(plain, settings(), StubCompressor(), count_tokens)
    assert plain_units[0].text == text
