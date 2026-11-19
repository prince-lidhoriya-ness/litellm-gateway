"""The production-readiness audit's failure cases as regression tests (STRATEGY.md, Phase 1.7).

    exp2   the root-cause line is kept at every distance from the matched line and for every wording of the question,
           with the default routes and with record selection switched on
    exp7   whole-document requests phrased without the old gate's keywords keep every date and owner
    exp8   ISO dates and hyphenated names survive compression byte for byte
    C1.3   every lossy removal leaves a marker: the number of omitted lines the markers announce equals the number of
           lines removed (invariant 17: a silent deletion is a bug)
    §3.1   selection runs only under context pressure when the context-engineering stage reports one

The models are test doubles (tests/fakes.py; the corrupting compressor of test_fidelity.py imitates the real model's
measured corruption). tests/test_model_regressions.py runs the same identifier checks on the real LLMLingua-2 model.
"""

import re

import pytest

from prompt_compression import intent
from prompt_compression.prompt_compression_callback import _pressure_hint

from .audit_cases import (
    CASE_C_NEEDLES, EXP2_DISTANCES, EXP2_QUESTIONS, EXP7_QUESTIONS, MEETING_DATES, MEETING_OWNERS, case_c, exp2_log,
    meeting_notes,
)
from .test_fidelity import CorruptingCompressor
from .test_pipeline import make_pipeline

DEFAULT = frozenset({"narrative", "logfold"})
EVERYTHING = frozenset({"narrative", "logfold", "passages", "records"})


def process(content, routes=DEFAULT, compressor=None, pressure=None, **overrides):
    pipeline, _, _ = make_pipeline(compressor=compressor, routes=routes, protect_edges=True, **overrides)
    new, report = pipeline.process([{"role": "user", "content": content}], pressure=pressure)
    return new[0]["content"], report


# ---- exp2 --------------------------------------------------------------------------------------------------------

def _exp2_prompt(distance, question="Why did order ord-7731 fail?"):
    # exp2: the matched line is line 80; a positive distance puts the root cause before it, a negative one after it
    return "Logs:\n\n" + exp2_log(80 - distance) + "\n\n" + question


@pytest.mark.parametrize("routes", [DEFAULT, EVERYTHING], ids=["default", "records_on"])
@pytest.mark.parametrize("distance", EXP2_DISTANCES)
def test_exp2_the_root_cause_is_kept_at_every_distance(distance, routes):
    content, _ = process(_exp2_prompt(distance), routes=routes)
    assert "ROOT-CAUSE-MARKER" in content                  # the audit lost it at every distance >= 2


@pytest.mark.parametrize("routes", [DEFAULT, EVERYTHING], ids=["default", "records_on"])
@pytest.mark.parametrize("question", EXP2_QUESTIONS)
def test_exp2_the_wording_of_the_question_does_not_decide_whether_the_root_cause_survives(question, routes):
    content, _ = process(_exp2_prompt(3, question), routes=routes)
    assert "ROOT-CAUSE-MARKER" in content


@pytest.mark.parametrize("distance", EXP2_DISTANCES)
def test_exp2_even_forced_record_selection_keeps_the_root_cause(distance):
    # Intent gate off: selection runs on "Why did ...?" as it did before the audit, and severity retention plus the
    # timestamp window still keep the error line.
    content, report = process(_exp2_prompt(distance), routes=frozenset({"records"}), intent_gate=False)
    assert "ROOT-CAUSE-MARKER" in content
    assert report.segments["record_lines_dropped"] > 100 and "[gateway: " in content


def test_exp2_a_root_cause_without_a_timestamp_match_is_still_kept_as_a_severity_line():
    lines = exp2_log(10).split("\n")
    lines[10] = "2026-11-17T09:00:00Z ERROR db-pool pool exhausted: max=20 active=20 (ROOT-CAUSE-MARKER)"   # far away
    content, _ = process("Logs:\n\n" + "\n".join(lines) + "\n\nWhy did order ord-7731 fail?",
                         routes=frozenset({"records"}), intent_gate=False)
    assert "ROOT-CAUSE-MARKER" in content


def test_case_c_with_every_route_on_keeps_all_key_facts():
    pipeline, _, _ = make_pipeline(routes=EVERYTHING, protect_edges=True)
    new, report = pipeline.process(case_c())
    assert all(needle in new[0]["content"] for needle in CASE_C_NEEDLES)      # the audit measured 1 of 5
    assert report.intent == intent.DIAGNOSE and report.tokens_after < report.tokens_before


# ---- C1.3: no silent deletion ------------------------------------------------------------------------------------

@pytest.mark.parametrize("distance", (2, 30, -5))
def test_every_removed_line_is_announced_by_a_marker(distance):
    content, report = process(_exp2_prompt(distance, "What is the status of order ord-7731?"),
                              routes=frozenset({"records"}))
    announced = 0
    for marker in re.findall(r"\[gateway: (?:line|lines) [^\]]*\]", content):
        match = re.search(r"\((\d+) lines?", marker)
        announced += int(match.group(1)) if match else 1
    assert report.segments["record_lines_dropped"] > 0
    assert announced == report.segments["record_lines_dropped"]
    assert report.segments["omission_markers"] == content.count("[gateway: ")


# ---- exp7: whole-document requests -------------------------------------------------------------------------------

@pytest.mark.parametrize("question", EXP7_QUESTIONS)
def test_exp7_document_requests_keep_every_date_and_owner(question):
    content, report = process("Meeting notes:\n\n" + meeting_notes() + "\n\n" + question, routes=EVERYTHING,
                              compressor=CorruptingCompressor())
    assert report.intent == intent.TRANSFORM and report.segments["passages_dropped"] == 0
    assert sum(date in content for date in MEETING_DATES) == 10
    assert sum(owner in content for owner in MEETING_OWNERS) == 10


# ---- exp8: identifiers survive compression -----------------------------------------------------------------------

def test_exp8_iso_dates_and_hyphenated_owners_survive_a_corrupting_compressor():
    content, report = process("Meeting notes:\n\n" + meeting_notes(repeat=1) + "\n\nWhat are the deadlines?",
                              compressor=CorruptingCompressor())
    assert report.tokens_after < report.tokens_before                  # something was compressed
    assert sum(date in content for date in MEETING_DATES) == 10        # audit: 5 of 10
    assert sum(owner in content for owner in MEETING_OWNERS) == 10     # audit: 5 of 10


# ---- §3.1: selection only under pressure -------------------------------------------------------------------------

def _lookup_prompt():
    return "Logs:\n\n" + exp2_log(77) + "\n\nWhat is the status of order ord-7731?"


@pytest.mark.parametrize("pressure, selects", [(None, True), ("low", False), ("moderate", False), ("high", True),
                                               ("over", True)])
def test_record_selection_needs_pressure_when_context_engineering_reports_one(pressure, selects):
    content, report = process(_lookup_prompt(), routes=frozenset({"records"}), pressure=pressure)
    assert report.intent == intent.LOOKUP and report.pressure == pressure
    assert report.selection_allowed is selects
    assert (report.segments["record_lines_dropped"] > 0) is selects


def test_the_minimum_pressure_is_configurable():
    _, report = process(_lookup_prompt(), routes=frozenset({"records"}), pressure="low", selection_min_pressure="low")
    assert report.segments["record_lines_dropped"] > 0


def test_the_hook_reads_the_pressure_hint_of_the_context_engineering_stage():
    assert _pressure_hint({"metadata": {"context_engineering": {"hints": {"pressure": "high"}}}}) == "high"
    assert _pressure_hint({"metadata": {"context_engineering": {"hints": {}}}}) is None          # shadow mode
    assert _pressure_hint({"metadata": {"context_engineering": {"hints": {"pressure": "bogus"}}}}) is None
    assert _pressure_hint({"metadata": {}}) is None
