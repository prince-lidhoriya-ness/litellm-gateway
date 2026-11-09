"""The pipeline end to end with a stub detector and a stub compressor: segment and classify, route, act, reassemble."""

import dataclasses
import json

from prompt_compression.pipeline import PromptPipeline
from prompt_compression.settings import PipelineSettings

from .fakes import RateStubCompressor, StubCompressor, StubDetector

LONG = " ".join(["word"] * 80)

PROSE_1 = (
    "Customers frequently cite reliability and after-sales support as the deciding factors when choosing between "
    "suppliers whose prices differ only by a few percentage points across the whole region."
)
PROSE_2 = (
    "Industry observers often note that mid-sized manufacturers adapt faster to new standards than their larger "
    "competitors, mainly because decisions pass through fewer layers of management and approval."
)
PROSE_3 = (
    "Recruitment has been a persistent challenge, with employers competing for engineers who combine mechanical "
    "training with experience in data analysis and automation tools used on modern production lines."
)
LOG_BLOCK = (
    "2026-03-14T19:06:42Z INFO  svc=report-builder req=req-a6a8e8 status=500 latency_ms=2742 user=u-66809 region=us-east-2\n"
    "2026-03-14T19:07:15Z INFO  svc=cart-service req=req-3e0206 status=409 latency_ms=1512 user=u-85079 region=ap-south-1"
)
JSON_BLOCK = '[\n  {"order_id": "ORD-8906", "items": 7, "total": 756.89},\n  {"order_id": "ORD-7255", "items": 3, "total": 902.45}\n]'
CODE_BLOCK = 'def check_records_so(data, retry_limit=109):\n    """Synchronise pending entries."""\n    return data[:retry_limit]'


def join(*blocks):
    return "\n\n".join(blocks)


def settings(**overrides):
    base = PipelineSettings.from_env()
    values = dict(
        enabled=True, fail_mode="open", timeout_s=5, redact_sensitive=False, preserve_last_user=False,
        min_chars=50, min_tokens=0, rate=0.4, eager_load=False,
        # Most tests use one-paragraph messages and ask for the plain behaviour (the latest user message is
        # compressible); the edge tests below turn this on.
        protect_edges=False, mode="enforce", routes=frozenset({"narrative"}),
    )
    values.update(overrides)
    return dataclasses.replace(base, **values)


def make_pipeline(sensitive_keywords=(), compressor=None, **overrides):
    compressor = compressor or StubCompressor()
    detector = StubDetector(sensitive_keywords)
    return PromptPipeline(settings=settings(**overrides), detector=detector, compressor=compressor), compressor, detector


# ---- keep verbatim: sensitive ---------------------------------------------------------------------------------

def test_sensitive_messages_are_sent_unchanged():
    pipeline, compressor, _ = make_pipeline(["SENS"])
    messages = [
        {"role": "user", "content": "SENS " + LONG},
        {"role": "assistant", "content": "SENS again " + LONG},
        {"role": "user", "content": "SENS once more " + LONG},
    ]
    new_messages, report = pipeline.process(messages)
    assert new_messages == messages and compressor.calls == []
    assert report.request_category == "sensitive" and report.ratio == 1.0
    assert [m["action"] for m in report.messages] == ["sensitive"] * 3


def test_a_rules_hit_is_sensitive_without_the_model():
    pipeline, compressor, detector = make_pipeline()
    text = "my email is jane.doe@example.com, " + LONG
    new_messages, report = pipeline.process([{"role": "user", "content": text}])
    assert new_messages[0]["content"] == text and compressor.calls == []
    entry = report.messages[0]
    assert entry["category"] == "sensitive" and entry["source"] == "rules" and entry["rule_hits"] == ["email"]


def test_only_the_block_with_the_rule_hit_is_protected():
    pipeline, compressor, _ = make_pipeline()
    private = "Contact me at jane.doe@example.com about the contract, thanks."
    text = join(PROSE_1, private, PROSE_2)
    new_messages, _ = pipeline.process([{"role": "user", "content": text}])
    out = new_messages[0]["content"]
    assert private in out and PROSE_1 not in out and PROSE_2 not in out
    assert sorted(c[0] for c in compressor.calls) == sorted([PROSE_1, PROSE_2])     # two runs, the protected block between


def test_a_prose_run_the_model_calls_sensitive_is_kept_whole():
    pipeline, compressor, detector = make_pipeline(["PRIVATE"])
    text = join(PROSE_1, "PRIVATE " + PROSE_2, PROSE_3)       # one prose run: the model judges it as a whole
    new_messages, report = pipeline.process([{"role": "user", "content": text}])
    assert new_messages[0]["content"] == text and compressor.calls == []
    assert report.messages[0]["category"] == "sensitive" and report.messages[0]["source"] == "model"


def test_redact_sensitive_replaces_pii_and_does_not_compress_the_block():
    pipeline, compressor, _ = make_pipeline(redact_sensitive=True)
    text = "my email is jane.doe@example.com, phone +1 555 013 2287. " + LONG
    new_messages, report = pipeline.process([{"role": "user", "content": text}])
    content = new_messages[0]["content"]
    assert "jane.doe@example.com" not in content and "[EMAIL]" in content and "[PHONE]" in content
    assert compressor.calls == [] and report.messages[0]["action"] == "redacted"
    assert report.messages[0]["redactions"] == 2


def test_redaction_is_off_by_default():
    pipeline, _, _ = make_pipeline()
    text = "my email is jane.doe@example.com " + LONG
    assert pipeline.process([{"role": "user", "content": text}])[0][0]["content"] == text


# ---- keep verbatim: roles and content types -----------------------------------------------------------------

def test_preserves_system_tool_messages_roles_and_order():
    pipeline, compressor, _ = make_pipeline()
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
    assert messages == original                                   # the input list is not mutated
    actions = {entry["index"]: entry["action"] for entry in report.messages}
    assert actions[0] == actions[1] == actions[3] == actions[4] == "preserved_role"


def test_protects_structure_inside_a_compressible_message():
    pipeline, compressor, _ = make_pipeline()
    text = join(PROSE_1, LOG_BLOCK, PROSE_2, CODE_BLOCK)
    new_messages, report = pipeline.process([{"role": "user", "content": text}, {"role": "assistant", "content": "ok"}])
    out = new_messages[0]["content"]
    assert LOG_BLOCK in out and CODE_BLOCK in out and PROSE_1 not in out
    entry = report.messages[0]
    assert entry["action"] == "compressed" and entry["segments"]["compressed_blocks"] == 2
    assert report.segments["structured"] == 1 and report.segments["code"] == 1
    assert report.kept == {"structured": 1, "code": 1}
    assert report.tokens_after < report.tokens_before


def test_a_message_of_only_exact_text_is_guarded():
    pipeline, compressor, detector = make_pipeline()
    text = join(LOG_BLOCK, JSON_BLOCK, CODE_BLOCK)
    new_messages, report = pipeline.process([{"role": "user", "content": text}, {"role": "assistant", "content": "ok"}])
    assert new_messages[0]["content"] == text and compressor.calls == []
    assert report.messages[0]["action"] == "guarded"
    assert detector.checked == []              # no prose, so the model was never asked


def test_the_model_is_only_asked_about_prose():
    pipeline, _, detector = make_pipeline()
    pipeline.process([{"role": "user", "content": join(PROSE_1, LOG_BLOCK, CODE_BLOCK, PROSE_2)},
                      {"role": "assistant", "content": "ok"}])
    assert detector.checked == [PROSE_1, PROSE_2]


def test_no_routes_means_nothing_to_do_and_no_model_calls():
    pipeline, compressor, detector = make_pipeline(routes=frozenset())
    messages = [{"role": "user", "content": join(PROSE_1, PROSE_2)}]
    new_messages, _ = pipeline.process(messages)
    assert new_messages == messages and detector.checked == [] and compressor.calls == []


def test_multimodal_parts_only_text_is_touched():
    pipeline, compressor, _ = make_pipeline()
    image = {"type": "image_url", "image_url": {"url": "https://example.com/cat.png"}}
    messages = [{"role": "user", "content": [{"type": "text", "text": "describe " + LONG}, image]}]
    new_messages, _ = pipeline.process(messages)
    assert new_messages[0]["content"][1] == image
    assert new_messages[0]["content"][0]["text"] != messages[0]["content"][0]["text"]


# ---- compress -------------------------------------------------------------------------------------------------

def test_compression_uses_the_configured_rate_and_reports_the_category():
    pipeline, compressor, _ = make_pipeline(rate=0.37)
    new_messages, report = pipeline.process([{"role": "user", "content": "plain " + LONG}])
    assert [rate for _, rate in compressor.calls] == [0.37]
    assert report.request_category == "general" and report.messages[0]["category"] == "general"
    assert report.tokens_after < report.tokens_before and report.ratio > 1


def test_short_messages_are_not_compressed():
    pipeline, compressor, _ = make_pipeline(min_chars=200)
    new_messages, report = pipeline.process([{"role": "user", "content": "hi there!"}])
    assert compressor.calls == [] and report.messages[0]["action"] == "below_min_chars"


def test_preserve_last_user_setting():
    pipeline, compressor, detector = make_pipeline(preserve_last_user=True)
    messages = [{"role": "user", "content": "older " + LONG}, {"role": "user", "content": "latest " + LONG}]
    new_messages, report = pipeline.process(messages)
    assert new_messages[1] == messages[1] and new_messages[0] != messages[0]
    assert report.messages[1]["action"] == "preserved_last_user"
    assert all("latest" not in text for text in detector.checked)        # not even asked about it


def test_the_instruction_and_question_of_the_latest_user_message_stay_verbatim():
    question = "Which factor do customers cite most often?"
    messages = [{"role": "user", "content": join("Read these notes.", PROSE_1, PROSE_2, PROSE_3, question)}]
    pipeline, compressor, _ = make_pipeline(protect_edges=True)
    new_messages, report = pipeline.process(messages)
    content = new_messages[0]["content"]
    assert content.startswith("Read these notes.") and content.endswith(question)
    assert compressor.calls[0][0] == join(PROSE_1, PROSE_2, PROSE_3)
    assert report.kept["edge"] == 2


def test_a_one_paragraph_latest_user_message_is_not_compressed_when_edges_are_protected():
    pipeline, compressor, _ = make_pipeline(protect_edges=True)
    new_messages, report = pipeline.process([{"role": "user", "content": PROSE_1 + " " + PROSE_2}])
    assert compressor.calls == [] and report.messages[0]["action"] == "guarded"


def test_the_model_does_not_judge_the_instruction_and_question_around_a_document():
    # They are kept verbatim anyway; a "sensitive" opinion on them (a lookup question) would only mislabel the request.
    question = "Question: SENS what was the user id of request req-1?"
    messages = [{"role": "user", "content": join("Read these notes.", PROSE_1, PROSE_2, PROSE_3, question)}]
    pipeline, compressor, detector = make_pipeline(["SENS"], protect_edges=True)
    new_messages, report = pipeline.process(messages)
    assert detector.checked == [join(PROSE_1, PROSE_2, PROSE_3)]
    assert report.request_category == "general" and compressor.calls
    assert new_messages[0]["content"].endswith(question)


def test_rules_still_protect_an_edge_the_model_skips():
    question = "Question: is jane.doe@example.com the account owner?"
    messages = [{"role": "user", "content": join("Read these notes.", PROSE_1, PROSE_2, PROSE_3, question)}]
    pipeline, _, detector = make_pipeline(protect_edges=True)
    new_messages, report = pipeline.process(messages)
    assert all("jane.doe" not in text for text in detector.checked)
    assert report.request_category == "sensitive" and report.messages[0]["rule_hits"] == ["email"]
    assert new_messages[0]["content"].endswith(question)


def test_a_short_prompt_is_still_judged_whole_by_the_model():
    # One or two paragraphs are all edges: the model stays the only judge of their label.
    pipeline, _, detector = make_pipeline(["SENS"], protect_edges=True)
    _, report = pipeline.process([{"role": "user", "content": join("SENS " + PROSE_1, PROSE_2)}])
    assert detector.checked and report.request_category == "sensitive"


def test_edges_are_judged_by_the_model_when_edge_protection_is_off():
    question = "Question: SENS what was the user id of request req-1?"
    messages = [{"role": "user", "content": join("Read these notes.", PROSE_1, PROSE_2, PROSE_3, question)}]
    pipeline, _, detector = make_pipeline(["SENS"], protect_edges=False)
    _, report = pipeline.process(messages)
    assert any("SENS" in text for text in detector.checked) and report.request_category == "sensitive"


def test_ratio_cap_retries_lighter_then_accepts():
    words = ["market", "season", "supplier", "region", "delivery", "customer", "review"]
    text = " ".join(words[i % 7] for i in range(240))
    pipeline, compressor, _ = make_pipeline(compressor=RateStubCompressor(), rate=0.3, max_ratio=3.0)
    new_messages, report = pipeline.process([{"role": "user", "content": text}])
    assert len(compressor.calls) == 2 and compressor.calls[1][1] > compressor.calls[0][1]
    assert report.messages[0]["segments"]["compress_calls"] == 2 and report.messages[0]["action"] == "compressed"


# ---- select or drop -------------------------------------------------------------------------------------------

def log_block(n=40):
    return "\n".join(
        f"2026-03-14T19:{i % 60:02d}:00Z INFO svc=cart req=req-{i:06x} status=200 latency_ms={100 + i} user=u-{i}" for i in range(n)
    )


def test_records_are_selected_using_the_question_of_the_latest_message():
    question = "What was the status of request req-000010?"
    messages = [
        {"role": "user", "content": join("Here is the log.", log_block())},
        {"role": "assistant", "content": "Received."},
        {"role": "user", "content": question},
    ]
    pipeline, _, _ = make_pipeline(routes=frozenset({"records"}), protect_edges=True)
    new_messages, report = pipeline.process(messages)
    kept = [line for line in new_messages[0]["content"].splitlines() if line.startswith("2026-")]
    assert any("req-000010" in line for line in kept) and len(kept) < 10
    assert new_messages[2]["content"] == question and report.messages[0]["action"] == "selected_records"


def test_a_json_array_stays_valid_after_record_selection():
    records = ",\n".join(f'  {{"order_id": "ORD-{i:04d}", "customer": "c-{i}", "total": {i}.5}}' for i in range(40))
    question = "What is the total of order ORD-0039?"
    messages = [{"role": "user", "content": join("Use the data.", f"[\n{records}\n]", question)}]
    pipeline, _, _ = make_pipeline(routes=frozenset({"records"}), protect_edges=True)
    body = pipeline.process(messages)[0][0]["content"].split("\n\n")[1]
    parsed = json.loads(body)
    assert any(item["order_id"] == "ORD-0039" for item in parsed) and len(parsed) < 40


def test_passages_the_question_does_not_need_are_dropped_whole():
    fillers = [
        f"Filler paragraph number {i} about suppliers, delivery times, warehouse staffing plans and regional customer "
        f"feedback gathered during the quarterly review meetings held across several offices, where the teams compared "
        f"forecasts, discussed seasonal demand and agreed on the next steps for each product line." for i in range(9)
    ]
    relevant = ("The Zorvex programme delivers cold-chain loggers to regional clinics, and its coordinators report "
                "every month to the health ministry about stock levels, spoilage and transport delays in districts.")
    fillers[4] = relevant
    question = "What does the Zorvex programme deliver?"
    messages = [{"role": "user", "content": join("Use the passages below.", *fillers, question)}]
    pipeline, compressor, _ = make_pipeline(routes=frozenset({"passages"}), protect_edges=True)
    new_messages, report = pipeline.process(messages)
    content = new_messages[0]["content"]
    assert relevant in content and content.startswith("Use the passages") and content.endswith(question)
    assert 0 < report.segments["passages_dropped"] < 9 and compressor.calls == []
    assert report.messages[0]["action"] == "selected_passages" and report.tokens_after < report.tokens_before


def test_with_passage_selection_each_passage_is_judged_alone():
    # A sensitive opinion on one passage protects that passage, not the whole document.
    fillers = [
        f"Filler paragraph number {i} about suppliers, delivery times, warehouse staffing plans and regional customer "
        f"feedback gathered during the quarterly review meetings held across several offices, where the teams compared "
        f"forecasts, discussed seasonal demand and agreed on the next steps for each product line." for i in range(9)
    ]
    flagged = fillers[2] = "SENS " + fillers[2]
    relevant = ("The Zorvex programme delivers cold-chain loggers to regional clinics, and its coordinators report "
                "every month to the ministry about stock levels, spoilage and transport delays in districts.")
    fillers[6] = relevant
    question = "What does the Zorvex programme deliver?"
    messages = [{"role": "user", "content": join("Use the passages below.", *fillers, question)}]
    pipeline, _, detector = make_pipeline(["SENS"], routes=frozenset({"passages"}), protect_edges=True)
    new_messages, report = pipeline.process(messages)
    content = new_messages[0]["content"]
    assert len(detector.checked) == 9 and all("\n\n" not in text for text in detector.checked)
    assert flagged in content and relevant in content and report.segments["passages_dropped"] > 0
    assert report.segments["sensitive"] == 1 and report.request_category == "sensitive"


def test_a_short_passage_is_judged_with_its_neighbour():
    short = "Ok, noted."
    paragraphs = [PROSE_1, short, PROSE_2, PROSE_3]
    messages = [{"role": "user", "content": join("Read these notes.", *paragraphs, "Question: what is noted?")}]
    pipeline, _, detector = make_pipeline(routes=frozenset({"passages"}), protect_edges=True)
    pipeline.process(messages)
    assert detector.checked == [PROSE_1, join(short, PROSE_2), PROSE_3]


def long_turn(role, n=120):
    return {"role": role, "content": " ".join(f"{role}{i}" for i in range(n))}


def history(turns=4):
    messages = [{"role": "system", "content": "Be brief."}]
    for _ in range(turns):
        messages += [long_turn("user"), long_turn("assistant")]
    messages.append({"role": "user", "content": "And now the last question?"})
    return messages


def test_history_drops_oldest_whole_turns_and_reports_original_indexes():
    messages = history()
    pipeline, _, _ = make_pipeline(routes=frozenset({"history"}), history_max_tokens=600, history_keep_messages=3)
    new_messages, report = pipeline.process(messages)
    assert report.history_dropped >= 2 and len(new_messages) == len(messages) - report.history_dropped
    assert new_messages[0]["role"] == "system" and new_messages[-1]["content"] == "And now the last question?"
    roles = [m["role"] for m in new_messages[1:]]
    assert roles[0] == "user" and all(a != b for a, b in zip(roles, roles[1:]))
    dropped = [e for e in report.messages if e["action"] == "dropped_history"]
    assert [e["index"] for e in dropped] == list(range(1, 1 + report.history_dropped))
    kept = [e for e in report.messages if e["action"] != "dropped_history"]
    assert [e["new_index"] for e in kept] == list(range(len(new_messages)))
    assert report.tokens_after < report.tokens_before


def test_history_is_off_without_a_budget_even_if_listed():
    pipeline, _, _ = make_pipeline(routes=frozenset({"history"}), history_max_tokens=0)
    new_messages, report = pipeline.process(history(2))
    assert len(new_messages) == len(history(2)) and report.history_dropped == 0


def test_a_turn_with_sensitive_text_is_never_dropped_from_the_history():
    messages = history()
    messages[1] = {"role": "user", "content": "I am allergic to penicillin. " + messages[1]["content"]}
    pipeline, _, _ = make_pipeline(["allergic"], routes=frozenset({"history"}), history_max_tokens=600, history_keep_messages=3)
    new_messages, report = pipeline.process(messages)
    assert report.history_dropped == 0 and any("allergic to penicillin" in m["content"] for m in new_messages)


# ---- the report -----------------------------------------------------------------------------------------------

def test_report_metadata_describes_the_stages():
    pipeline, _, _ = make_pipeline(["SENS"])
    messages = [{"role": "user", "content": "SENS " + LONG}, {"role": "assistant", "content": LONG}]
    _, report = pipeline.process(messages)
    meta = report.as_metadata()
    assert meta["category"] == "sensitive" and meta["mode"] == "enforce" and meta["routes"] == ["narrative"]
    first, second = meta["messages"]
    assert first["category"] == "sensitive" and second["category"] == "general"
    assert {"score", "source", "classify_ms", "tokens_before", "tokens_after", "segments", "new_index"} <= set(second)
