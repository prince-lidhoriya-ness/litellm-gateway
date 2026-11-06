import json

import pytest

from prompt_compression.segmenter import (
    CODE, EXACT, PROSE, STRUCTURED, classify_block, exact_share, join_segments, label_split, split_segments,
)

PROSE_1 = (
    "Customers frequently cite reliability and after-sales support as the deciding factors when choosing between "
    "suppliers whose prices differ only by a few percentage points."
)
PROSE_2 = (
    "Industry observers often note that mid-sized manufacturers adapt faster to new standards than their larger "
    "competitors, mainly because decisions pass through fewer layers of management."
)
LOG_BLOCK = (
    "2026-03-14T19:06:42Z INFO  svc=report-builder req=req-a6a8e8 status=500 latency_ms=2742 user=u-66809 region=us-east-2\n"
    "2026-03-14T19:07:15Z INFO  svc=cart-service req=req-3e0206 status=409 latency_ms=1512 user=u-85079 region=ap-south-1"
)
JSON_ARRAY = '[\n  {"order_id": "ORD-8906", "items": 7, "total": 756.89},\n  {"order_id": "ORD-7255", "items": 3, "total": 902.45}\n]'
PYTHON = 'def check_records_so(data, retry_limit=109):\n    """Synchronise pending entries."""\n    limit = min(retry_limit, MAX_WINDOW_DO)\n    return data[:limit]'


def kinds(text, **kwargs):
    return [(s.kind, s.subtype) for s in split_segments(text, **kwargs) if s.text.strip()]


# ---- the segmenter never changes a character -----------------------------------------------------------------

ROUND_TRIPS = [
    "",
    "   \n\n  ",
    "\n\n" + PROSE_1,
    PROSE_1 + "\n\n\n\n" + PROSE_2 + "\n",
    "line one\r\n\r\nline two\r\n",
    PROSE_1 + "\n\n```python\nprint('x')\n```\n\n" + PROSE_2,
    "```\nunterminated fence\nstill code",
    "~~~sh\nls -la\n~~~",
    "intro\n\n" + LOG_BLOCK + "\n\n" + JSON_ARRAY + "\n\n" + PYTHON,
    "\t indented start\n\n\t\tmore",
    "tabs\tand\tcolumns\n1\t2\t3\n4\t5\t6",
]


@pytest.mark.parametrize("text", ROUND_TRIPS)
def test_segments_reassemble_to_the_original(text):
    assert join_segments(split_segments(text)) == text


# ---- structure ------------------------------------------------------------------------------------------------

def test_fenced_block_is_code_and_surroundings_are_separate():
    text = PROSE_1 + "\n\n```python\nx = 1\n```\n\n" + PROSE_2
    assert kinds(text) == [(PROSE, "prose"), (CODE, "fence"), (PROSE, "prose")]


def test_unterminated_fence_runs_to_the_end():
    assert kinds("intro text here\n\n```\nnever closed\nmore code") == [(PROSE, "prose"), (CODE, "fence")]


def test_json_array_object_lines_and_truncated_json():
    assert classify_block(JSON_ARRAY) == (STRUCTURED, "json")
    assert classify_block('{"a": 1, "b": {"c": [1, 2, 3]}}') == (STRUCTURED, "json")
    assert classify_block('{"a": 1}\n{"a": 2}\n{"a": 3}') == (STRUCTURED, "jsonl")
    assert classify_block('{"id": "x", "name": "y", "tags": ["a", "b"') == (STRUCTURED, "json")


def test_log_lines():
    assert classify_block(LOG_BLOCK) == (STRUCTURED, "log")
    assert classify_block("2026-03-14 19:06:42,123 ERROR Failed to connect to database") == (STRUCTURED, "log")
    assert classify_block("ERROR code=500 path=/api/cart") == (STRUCTURED, "log")


def test_timestamped_meeting_transcript_is_still_prose():
    transcript = "[00:12:03] Alice: I think we should move the launch to next quarter.\n[00:12:11] Bob: That works for me."
    assert classify_block(transcript) == (PROSE, "prose")


def test_stack_trace():
    trace = 'Traceback (most recent call last):\n  File "app.py", line 12, in main\n    run()\nValueError: bad input'
    assert classify_block(trace) == (STRUCTURED, "stack")


def test_tables_and_csv():
    assert classify_block("| id | name |\n|---|---|\n| 1 | Ana |\n| 2 | Bo |") == (STRUCTURED, "table")
    assert classify_block("id,name,city\n1,Ana,Oslo\n2,Bo,Rome\n3,Cy,Lyon") == (STRUCTURED, "csv")
    assert classify_block("id\tname\n1\tAna\n2\tBo\n3\tCy") == (STRUCTURED, "tsv")


def test_prose_with_commas_is_not_csv():
    text = "First, we reviewed the plan.\nSecond, we agreed on a budget.\nThird, we set a date."
    assert classify_block(text)[0] == PROSE


def test_key_value_config_but_not_speaker_lines():
    assert classify_block("max_connections = 20\ntimeout_s: 30\nLOG_LEVEL=debug") == (STRUCTURED, "kv")
    assert classify_block("Alice: I will send the notes today.\nBob: Thanks, that helps a lot.")[0] == PROSE


# ---- code -----------------------------------------------------------------------------------------------------

def test_unfenced_code_shell_and_sql():
    assert classify_block(PYTHON)[0] == CODE
    assert classify_block("$ git status\n$ npm install")[0] == CODE
    assert classify_block("SELECT id, name FROM users WHERE id = 7;")[0] == CODE
    assert classify_block("log = logging.getLogger(__name__)")[0] == CODE


def test_indented_block_is_code():
    # whether it is called code or key=value, the block must be protected
    assert classify_block("    first = 1\n    second = 2\n    third = first + second")[0] in (CODE, STRUCTURED)


# ---- identifier-dense text ------------------------------------------------------------------------------------

def test_constants_and_ids_are_exact_text():
    assert classify_block("MAX_WINDOW_PB = 259")[0] == EXACT
    fact = "The Pryworks-804 line launched in September 1990 at a price of $805, and the first batch sold 7867 units in 17 days."
    assert classify_block(fact) == (EXACT, "ids")


def test_ordinary_prose_stays_prose_even_with_a_year():
    text = "The company was founded in 1995 by two engineers who wanted to build a small workshop for cold-chain loggers."
    assert classify_block(text) == (PROSE, "prose")
    assert classify_block(PROSE_1) == (PROSE, "prose")


def test_paragraphs_full_of_names_are_exact_text():
    # the benchmark's answer paragraph for "who was chief executive before Sana Grimaldi": two digit-words only, but
    # the names are what the question asks for, and token pruning dropped "Tanaka" from it
    text = "After 6 years under Nadia Tanaka, leadership passed to Sana Grimaldi in 2009, who remains chief executive."
    assert classify_block(text) == (EXACT, "ids")
    assert classify_block("The story of Dorvance began in Utrecht in 1995, when Yara Nakamura set up a workshop.")[0] == EXACT


def test_sentence_starts_and_speaker_labels_are_not_names():
    assert exact_share("Customers frequently cite reliability. Industry observers note it. Recruitment is hard.") == (0, 11)
    assert exact_share("Alice: I think we should wait. Bob: That works for me.") == (0, 11)
    assert exact_share("We asked Nadia about it.") == (1, 5)


def test_a_label_line_above_data_does_not_hide_the_data():
    assert classify_block("Document:\n" + JSON_ARRAY) == (STRUCTURED, "json")
    assert classify_block("Here is the log:\n" + LOG_BLOCK) == (STRUCTURED, "log")
    assert classify_block("Note:\n" + PROSE_1) == (PROSE, "prose")
    assert label_split("Document:\n[1, 2]") == ("Document:\n", "[1, 2]")
    assert label_split("Not a label\nsecond line") == ("", "Not a label\nsecond line")


def test_exact_density_threshold_is_adjustable():
    text = "Revenue reached 48 million in 2021 and costs fell over the same period according to the audit committee last year."
    assert classify_block(text, exact_density=0.15)[0] == PROSE
    assert classify_block(text, exact_density=0.05)[0] == EXACT


def test_paths_emails_and_camel_case_count_as_exact():
    exact, words = exact_share("see /var/log/app.log or mail ops@example.com about getUserName")
    assert (exact, words) == (3, 7)


# ---- messages mixing kinds -----------------------------------------------------------------------------------

def test_mixed_message_keeps_each_block_with_its_own_kind():
    text = "\n\n".join([PROSE_1, LOG_BLOCK, PROSE_2, JSON_ARRAY, "MAX_WINDOW_PB = 259", PYTHON])
    assert [k for k, _ in kinds(text)] == [PROSE, STRUCTURED, PROSE, STRUCTURED, EXACT, CODE]


def test_protected_flag():
    segments = split_segments(PROSE_1 + "\n\n" + LOG_BLOCK)
    assert [s.protected for s in segments] == [False, True]


def test_research_datasets_are_protected_when_present():
    """The benchmark items behind reports/compression-fit: every log, JSON and code context must be fully protected."""
    from pathlib import Path

    data = Path(__file__).resolve().parents[2] / "reports" / "compression-fit" / "data"
    if not (data / "logs.jsonl").exists():
        pytest.skip("research datasets not present")
    for name in ("logs", "code"):
        for line in (data / f"{name}.jsonl").read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            segments = split_segments(item["context"])
            assert join_segments(segments) == item["context"]
            assert all(s.protected for s in segments if s.text.strip()), item["id"]
