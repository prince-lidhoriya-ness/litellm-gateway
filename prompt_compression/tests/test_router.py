"""The router only decides: which action each unit gets and why."""

from prompt_compression import router
from prompt_compression.segmenter import split_segments
from prompt_compression.texts import count_tokens, message_tokens
from prompt_compression.units import COMPRESS, KEEP, SELECT, Unit

from .test_pipeline import CODE_BLOCK, JSON_BLOCK, LOG_BLOCK, PROSE_1, PROSE_2, PROSE_3, join, settings


def units_of(text, message=0):
    return [Unit(message, None, s.kind, s.subtype, s.text, s.sep) for s in split_segments(text)]


def route(text, query=None, last_user=None, **overrides):
    # These tests exercise the routing rules themselves, on units with no latest user message, so selection is allowed
    # on every message; the default scope ("latest_user") has its own tests below.
    overrides.setdefault("selection_scope", "all")
    units = units_of(text)
    plan = router.route(units, settings(**overrides), query, last_user, count_tokens)
    return units, plan


def test_prose_is_compressed_and_exact_kinds_are_kept_with_a_reason():
    units, plan = route(join(PROSE_1, LOG_BLOCK, CODE_BLOCK, "MAX_WINDOW_PB = 259", PROSE_2))
    assert [(u.action, u.reason) for u in units] == [
        (COMPRESS, "prose"), (KEEP, "structured"), (KEEP, "code"), (KEEP, "exact"), (COMPRESS, "prose")]
    assert [u.compressible for u in units] == [True, False, False, False, True]
    assert plan.reasons == {"structured": 1, "code": 1, "exact": 1}


def test_sensitive_wins_over_everything():
    units = units_of(join(PROSE_1, PROSE_2))
    units[0].sensitive = True
    router.route(units, settings(), None, None, count_tokens)
    assert (units[0].action, units[0].reason, units[0].compressible) == (KEEP, "sensitive", False)
    assert units[1].action == COMPRESS


def test_the_first_and_last_paragraph_of_the_latest_user_message_are_edges():
    units, plan = route(join("Read the notes.", PROSE_1, PROSE_2, "Which factor matters most?"), last_user=0, protect_edges=True)
    assert [u.reason for u in units] == ["edge", "prose", "prose", "edge"] and units[0].edge and units[-1].edge


def test_a_one_paragraph_latest_message_is_a_single_edge():
    units, _ = route(PROSE_1, last_user=0, protect_edges=True)
    assert units[0].reason == "edge" and units[0].action == KEEP


def test_earlier_messages_have_no_edges_and_edges_can_be_switched_off():
    assert all(u.reason == "prose" for u in route(join(PROSE_1, PROSE_2), last_user=5, protect_edges=True)[0])
    assert all(u.reason == "prose" for u in route(join(PROSE_1, PROSE_2), last_user=0, protect_edges=False)[0])


def test_preserve_last_user_keeps_the_whole_message():
    units, _ = route(join(PROSE_1, PROSE_2), last_user=0, preserve_last_user=True, protect_edges=False)
    assert all((u.action, u.reason) == (KEEP, "last_user") for u in units)


def test_narrative_route_off_keeps_prose_with_a_reason():
    units, _ = route(join(PROSE_1, PROSE_2), routes=frozenset())
    assert all((u.action, u.reason, u.compressible) == (KEEP, "route_off", False) for u in units)


# ---- select: records and passages ---------------------------------------------------------------------------

def test_records_route_selects_structured_blocks_only_when_there_is_a_question():
    text = join(LOG_BLOCK, JSON_BLOCK, CODE_BLOCK)
    units, plan = route(text, query="What was the latency of req-3e0206?", routes=frozenset({"records"}))
    assert [(u.action, u.reason) for u in units] == [(SELECT, "records"), (SELECT, "records"), (KEEP, "code")]
    assert plan.records == units[:2]
    units, plan = route(text, query=None, routes=frozenset({"records"}))
    assert [u.reason for u in units] == ["structured", "structured", "code"] and plan.records == []


def passages(n=8):
    return [f"Passage number {i} describes suppliers, delivery times and regional staffing plans in some detail." for i in range(n)]


def test_passages_route_marks_candidates_when_there_is_a_question_and_enough_text():
    text = join(*passages(), "MAX_WINDOW_PB = 259")
    units, plan = route(text, query="What about suppliers?", routes=frozenset({"passages"}), min_passages=6, min_passage_tokens=50)
    assert len(plan.passages) == 9                      # eight prose passages and the exact block, which is droppable but never compressed
    assert all(u.selectable and u.action == SELECT for u in plan.passages)
    assert not units[-1].compressible


def test_passages_route_needs_enough_passages_and_enough_tokens_and_a_question():
    text = join(*passages(8))
    base = dict(routes=frozenset({"passages"}), min_passages=6, min_passage_tokens=50)
    assert route(text, query="suppliers", **{**base, "min_passages": 9})[1].passages == []
    assert route(text, query="suppliers", **{**base, "min_passage_tokens": 5000})[1].passages == []
    assert route(text, query=None, **base)[1].passages == []
    assert len(route(text, query="suppliers", **base)[1].passages) == 8


def test_sensitive_passages_are_never_candidates():
    units = units_of(join(*passages(8)))
    units[3].sensitive = True
    plan = router.route(units, settings(routes=frozenset({"passages"}), min_passages=6, min_passage_tokens=50,
                                        selection_scope="all"),
                        "suppliers", None, count_tokens)
    assert units[3] not in plan.passages and len(plan.passages) == 7


# ---- select: history -----------------------------------------------------------------------------------------

def conversation(turns=4, size=100):
    messages = [{"role": "system", "content": "Be brief."}]
    for _ in range(turns):
        messages += [{"role": "user", "content": " ".join(["w"] * size)}, {"role": "assistant", "content": " ".join(["w"] * size)}]
    messages.append({"role": "user", "content": "last question"})
    return messages


def test_history_route_off_or_under_budget_drops_nothing():
    messages = conversation()
    assert router.plan_history(messages, {}, settings(routes=frozenset({"narrative"}), history_max_tokens=100), message_tokens) == []
    assert router.plan_history(messages, {}, settings(routes=frozenset({"history"}), history_max_tokens=0), message_tokens) == []
    assert router.plan_history(messages, {}, settings(routes=frozenset({"history"}), history_max_tokens=10_000), message_tokens) == []


def test_history_route_drops_the_oldest_whole_turns_and_spares_sensitive_ones():
    messages = conversation()
    config = settings(routes=frozenset({"history"}), history_max_tokens=500, history_keep_messages=3)
    assert router.plan_history(messages, {}, config, message_tokens) == [1, 2, 3, 4]
    sensitive = Unit(1, None, "prose", "prose", "private", sensitive=True)
    assert router.plan_history(messages, {1: [sensitive]}, config, message_tokens) == []
