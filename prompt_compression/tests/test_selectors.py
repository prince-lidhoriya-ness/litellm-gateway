import json

from prompt_compression.selectors import (
    drop_trailing_comma, rank_units, select_passages, select_records, tokenize, trim_history,
)


def count(text):
    return len(text.split())


def words(n, role="user", **extra):
    return {"role": role, "content": " ".join(["w"] * n), **extra}


def message_tokens(message):
    return len(str(message.get("content") or "").split())


# ---- ranking ------------------------------------------------------------------------------------------------

def test_tokenize_keeps_compound_identifiers():
    tokens = tokenize("The Pryworks-804 line, request req_ab12 and v1.2.3!")
    assert {"pryworks-804", "req_ab12", "v1.2.3"} <= set(tokens)


def test_rank_units_puts_the_matching_unit_first():
    units = ["Weather was mild all week.", "The Pryworks-804 line sold 7867 units.", "Staff were hired in March."]
    scores = rank_units("How many units of Pryworks-804 were sold?", units)
    assert scores.index(max(scores)) == 1


def test_rank_units_without_overlap_is_all_zero():
    assert rank_units("zorvex", ["alpha beta", "gamma delta"]) == [0.0, 0.0]
    assert rank_units("", ["alpha"]) == [0.0]


# ---- passages -----------------------------------------------------------------------------------------------

def passages_with_one_relevant(n=9, relevant=4):
    items = [f"Filler paragraph number {i} about suppliers, delivery times and regional staffing plans." for i in range(n)]
    items[relevant] = "The Zorvex programme delivers cold-chain loggers to regional clinics."
    return items


def test_select_passages_keeps_the_relevant_one_and_its_neighbours():
    items = passages_with_one_relevant()
    flags = select_passages(items, "What does the Zorvex programme deliver?", 0.5, count)
    assert flags[4] is True
    assert flags[3] and flags[5]            # neighbours fill the shortfall
    assert 3 <= sum(flags) <= 6 and not all(flags)


def test_select_passages_without_lexical_signal_drops_nothing():
    items = passages_with_one_relevant()
    assert select_passages(items, "Tell me more about it", 0.5, count) is None
    assert select_passages([], "anything", 0.5, count) is None


def test_select_passages_stops_at_the_keep_ratio():
    items = ["alpha beta gamma delta epsilon zeta"] * 10
    items[2] = "alpha target zeta"
    items[7] = "alpha target eta"
    flags = select_passages(items, "target", 0.2, count)
    assert flags[2] and flags[7] and sum(flags) <= 4


# ---- records ------------------------------------------------------------------------------------------------

def log_lines(n=30):
    return [f"2026-03-14T19:{i:02d}:00Z INFO svc=cart req=req-{i:06x} status=200 latency_ms={100 + i}" for i in range(n)]


def test_records_named_by_the_question_are_kept_with_neighbours():
    lines = log_lines()
    flags = select_records(lines, "What was the latency_ms value of request req-00001a?", "log", context_lines=1)
    assert [i for i, keep in enumerate(flags) if keep] == [25, 26, 27]


def test_a_field_name_alone_does_not_trigger_selection():
    # latency_ms is on every line, so it identifies nothing
    assert select_records(log_lines(), "What is the latency_ms of the slowest request?", "log") is None


def test_no_identifier_in_the_question_keeps_everything():
    assert select_records(log_lines(), "What went wrong overall?", "log") is None


def test_identifier_on_most_lines_keeps_everything():
    lines = [f"svc-a request {i}" for i in range(20)]
    assert select_records(lines, "Which request of svc-a failed?", "log") is None


def test_table_header_and_json_brackets_survive():
    csv = ["id,name,city"] + [f"{i},user{i},Oslo" for i in range(1, 30)]
    flags = select_records(csv, "Which city is user17 in?", "csv", context_lines=0)
    assert flags[0] and flags[17] and sum(flags) == 2
    json_lines = ["["] + [f'  {{"order_id": "ORD-{i:04d}", "total": {i}}},' for i in range(30)] + ["]"]
    flags = select_records(json_lines, "What is the total of ORD-0007?", "json", context_lines=0)
    assert flags[0] and flags[-1] and flags[8]


def test_drop_trailing_comma_keeps_json_valid():
    lines = ["[", '  {"a": 1},', '  {"a": 2},', "]"]
    assert json.loads("\n".join(drop_trailing_comma(lines[:2] + ["]"])))     # last kept record loses its comma
    assert drop_trailing_comma(['  {"a": 1}', "]"]) == ['  {"a": 1}', "]"]


# ---- chat history -------------------------------------------------------------------------------------------

def conversation(turns=4, size=100):
    messages = [words(10, "system")]
    for _ in range(turns):
        messages += [words(size, "user"), words(size, "assistant")]
    messages.append(words(20, "user"))
    return messages


def test_history_under_budget_is_untouched():
    assert trim_history(conversation(), 10_000, 4, message_tokens) == ([], 0)


def test_budget_of_zero_disables_trimming():
    assert trim_history(conversation(), 0, 4, message_tokens) == ([], 0)


def test_oldest_whole_turns_go_first_and_system_stays():
    messages = conversation(turns=4)            # 10 + 8*100 + 20 = 830 tokens
    dropped, removed = trim_history(messages, 500, 2, message_tokens)
    assert dropped == [1, 2, 3, 4]                # two oldest user+assistant pairs
    assert removed == 400
    assert 0 not in dropped and len(messages) - 1 not in dropped


def test_the_last_messages_are_always_kept():
    messages = conversation(turns=4)
    dropped, _ = trim_history(messages, 50, 4, message_tokens)
    assert set(dropped).isdisjoint(range(len(messages) - 4, len(messages)))
    assert all(index > 0 for index in dropped)


def test_a_turn_is_never_cut_in_half():
    messages = conversation(turns=2)            # indexes: 0 system, 1 u, 2 a, 3 u, 4 a, 5 u (latest)
    # only the latest message is protected: the turn before it ends exactly at the boundary and is complete
    assert trim_history(messages, 100, 1, message_tokens)[0] == [1, 2, 3, 4]
    # the last two messages are protected: turn [3, 4] would lose its reply to the protected tail, so it stays
    assert trim_history(messages, 100, 2, message_tokens)[0] == [1, 2]


def test_tool_calls_and_results_stop_the_trimming():
    messages = [
        words(10, "system"),
        words(100, "user"),
        {"role": "assistant", "content": None, "tool_calls": [{"id": "c1"}]},
        {"role": "tool", "tool_call_id": "c1", "content": " ".join(["w"] * 100)},
        words(100, "assistant"),
        words(100, "user"), words(100, "assistant"), words(20, "user"),
    ]
    assert trim_history(messages, 100, 2, message_tokens) == ([], 0)
