"""Fidelity guard and identifier-safe compression (reports/production-readiness-audit/STRATEGY.md, H3, H4).

The corrupting compressor below reproduces what the audit measured on the real LLMLingua-2 model (REPORT.md §3.1,
cases G and J; exp8): it puts spaces around "-", "_" and "." inside words and drops every third word. The real model is
exercised in tests/test_model_regressions.py.
"""

import re

import pytest

from prompt_compression import actions, fidelity, router
from prompt_compression.segmenter import split_segments
from prompt_compression.texts import count_tokens
from prompt_compression.units import Unit

from .fakes import StubCompressor
from .test_pipeline import settings

IDENTIFIER_PROSE = (
    "The quarterly incident review covered the customer escalations in some detail, and the team agreed that the "
    "tracking code for the incident is NIMBUS-5044 and it was opened against RFC-9110 section 5.2 on port 8443 "
    "running version 3.11.4 of the proxy, while the decisive configuration value IDLE_TIMEOUT_SECONDS=1800 must never "
    "be lowered below 900 and the owner team-mobile-app delivers the fix by 2026-12-10 according to the plan."
)


class CorruptingCompressor:
    """Behaves like the audit's LLMLingua-2 measurements: splits punctuation inside words and drops words."""

    model_name = "corrupting-compressor"

    def __init__(self):
        self.calls = []

    def load(self):
        pass

    def compress(self, text, rate):
        from prompt_compression.compressor_adapter import CompressionOutput

        self.calls.append((text, rate))
        words = [re.sub(r"(?<=\w)([-_.])(?=\w)", r" \1 ", w) for i, w in enumerate(text.split()) if i % 3 != 2]
        out = " ".join(words)
        return CompressionOutput(out, count_tokens(text), count_tokens(out))


class UnitDroppingCompressor:
    """Drops the word "seconds" (a unit) unless the rate keeps at least `keep_from` of the tokens."""

    model_name = "unit-dropping"

    def __init__(self, keep_from=1.1):
        self.calls = []
        self.keep_from = keep_from

    def load(self):
        pass

    def compress(self, text, rate):
        from prompt_compression.compressor_adapter import CompressionOutput

        self.calls.append((text, rate))
        words = text.split()
        if rate < self.keep_from:
            words = [w for w in words if not w.startswith("seconds")]
        # drop every fourth plain word; digits and the unit are only ever decided by the rate above
        words = [w for i, w in enumerate(words) if i % 4 != 3 or any(c.isdigit() for c in w) or w.startswith("seconds")]
        out = " ".join(words)
        return CompressionOutput(out, count_tokens(text), count_tokens(out))


def execute(text, compressor, reference="", **overrides):
    config = settings(**overrides)
    units = [Unit(0, None, s.kind, s.subtype, s.text, s.sep) for s in split_segments(text)]
    plan = router.route(units, config, None, None, count_tokens)
    plan.reference = reference
    outcome = actions.execute(plan, config, compressor, count_tokens)
    return "".join(u.full for u in units if not u.dropped), outcome


# ---- the patterns -------------------------------------------------------------------------------------------------

def test_the_audits_corrupted_strings_are_identifiers():
    found = fidelity.identifiers(IDENTIFIER_PROSE)
    for expected in ("NIMBUS-5044", "RFC-9110", "5.2", "3.11.4", "IDLE_TIMEOUT_SECONDS=1800", "team-mobile-app",
                     "2026-12-10"):
        assert expected in found


def test_split_protected_round_trips_and_cuts_at_every_identifier():
    pieces = fidelity.split_protected(IDENTIFIER_PROSE)
    assert "".join(piece for _, piece in pieces) == IDENTIFIER_PROSE
    protected = [piece for is_span, piece in pieces if is_span]
    assert "NIMBUS-5044" in protected and "3.11.4" in protected and "IDLE_TIMEOUT_SECONDS=1800" in protected
    assert all(not fidelity.identifiers(piece) for is_span, piece in pieces if not is_span)


def test_the_severity_pattern_is_the_one_context_engineering_uses():
    from context_engineering import extract

    assert fidelity.SEVERITY.pattern == extract._ERROR_LINE.pattern
    assert fidelity.SEVERITY.flags == extract._ERROR_LINE.flags


def test_referenced_strings_are_those_the_reference_mentions_case_insensitively():
    removed = "order ord-7731 timed out after 30000ms; pool db-main at 20 connections"
    assert fidelity.referenced(fidelity.must_survive(removed), "Why did ORD-7731 fail?") == ["ord-7731"]
    assert fidelity.missing_referenced(removed, "nothing kept", "Why did ORD-7731 fail?") == ["ord-7731"]
    assert fidelity.missing_referenced(removed, "kept: ord-7731", "Why did ORD-7731 fail?") == []
    assert fidelity.missing_referenced(removed, "", "") == []


# ---- identifier-safe compression (H3) -----------------------------------------------------------------------------

def test_identifiers_never_reach_the_compressor_and_survive_byte_for_byte():
    compressor = CorruptingCompressor()
    out, outcome = execute(IDENTIFIER_PROSE, compressor)
    assert outcome.acted[0] == ["compressed"] and count_tokens(out) < count_tokens(IDENTIFIER_PROSE)
    for identifier in fidelity.identifiers(IDENTIFIER_PROSE):
        assert identifier in out
        assert all(identifier not in text for text, _ in compressor.calls)
    assert "NIMBUS - 5044" not in out and "3. 11. 4" not in out
    assert outcome.fidelity.as_dict()["compress"]["checked"] == 1


def test_without_span_protection_the_byte_exact_check_reverts_the_run(monkeypatch):
    # The post-check is a guard of its own: should a pattern ever miss a span, a corrupted run is still not sent.
    monkeypatch.setattr(fidelity, "split_protected", lambda text: [(False, text)])
    out, outcome = execute(IDENTIFIER_PROSE, CorruptingCompressor())
    assert out == IDENTIFIER_PROSE and 0 not in outcome.acted
    tally = outcome.fidelity.as_dict()["compress"]
    assert tally["reverted"] == 1 and tally["reasons"] == {"identifier": 1}
    assert outcome.stats[0]["fidelity_reverts"] == 1


def test_a_run_of_only_identifiers_and_short_gaps_is_not_compressed():
    text = "NIMBUS-5044 and RFC-9110 and 3.11.4 and team-mobile-app and 2026-12-10 and IDLE_TIMEOUT_SECONDS=1800 ok."
    compressor = StubCompressor()
    out, _ = execute(text, compressor, min_chars=20)
    assert out == text and compressor.calls == []


# ---- referenced strings: retry lighter, then revert (H4) ----------------------------------------------------------

UNIT_PROSE = (
    "During the review the operators explained that the nightly export job usually finishes quickly, but when the "
    "upstream queue is congested the worker waits and the job times out after 45 seconds, which then triggers the "
    "retry policy and a second attempt that normally completes without any further manual intervention by the team."
)


def test_a_referenced_unit_that_compression_dropped_is_retried_lighter_and_kept():
    compressor = UnitDroppingCompressor(keep_from=0.6)
    out, outcome = execute(UNIT_PROSE, compressor, reference="The SLO says jobs must finish within 45 seconds.")
    assert "45 seconds" in out and outcome.acted[0] == ["compressed"]
    rates = [rate for _, rate in compressor.calls]
    assert min(rates) == pytest.approx(0.4) and max(rates) == pytest.approx(0.65)
    tally = outcome.fidelity.as_dict()["compress"]
    assert tally["retried"] == 1 and tally["reverted"] == 0


def test_when_the_lighter_retry_still_loses_it_the_run_is_reverted():
    out, outcome = execute(UNIT_PROSE, UnitDroppingCompressor(), reference="jobs must finish within 45 seconds")
    assert out == UNIT_PROSE and 0 not in outcome.acted
    tally = outcome.fidelity.as_dict()["compress"]
    assert tally["retried"] == 1 and tally["reverted"] == 1 and tally["reasons"] == {"referenced": 1}


def test_an_unreferenced_unit_may_be_compressed_away():
    out, outcome = execute(UNIT_PROSE, UnitDroppingCompressor(), reference="Unrelated question about billing.")
    assert "45 seconds" not in out and outcome.acted[0] == ["compressed"]
    assert outcome.fidelity.as_dict()["compress"]["retried"] == 0


# ---- the adapter batches the pieces of a run into one model call --------------------------------------------------

def test_the_adapter_compresses_many_texts_in_one_call_and_caches_each(monkeypatch):
    from prompt_compression.compressor_adapter import LLMLinguaCompressor

    class Model:
        def __init__(self):
            self.calls = []

        def compress_prompt(self, context, rate, force_reserve_digit, use_context_level_filter=True):
            # the real compress_prompt drops whole contexts unless this is off (compressor_adapter.compress_many)
            assert use_context_level_filter is False
            self.calls.append(list(context))
            return {"compressed_prompt": "\n\n".join(c[:5] for c in context),
                    "compressed_prompt_list": [c[:5] for c in context], "origin_tokens": 1, "compressed_tokens": 1}

    adapter = LLMLinguaCompressor("m", "r", cache_size=8)
    adapter._compressor = Model()
    outputs, calls = adapter.compress_many(["alpha beta gamma", "delta epsilon"], 0.4)
    assert calls == 1 and [o.text for o in outputs] == ["alpha", "delta"]
    again, calls = adapter.compress_many(["alpha beta gamma", "zeta eta theta"], 0.4)
    assert calls == 1 and again[0].cached and not again[1].cached
    assert adapter._compressor.calls == [["alpha beta gamma", "delta epsilon"], ["zeta eta theta"]]


def test_the_adapter_refuses_a_batch_result_without_one_text_per_context():
    from prompt_compression.compressor_adapter import LLMLinguaCompressor

    class Model:
        def compress_prompt(self, context, rate, force_reserve_digit, use_context_level_filter=True):
            return {"compressed_prompt": "x", "origin_tokens": 1, "compressed_tokens": 1}

    adapter = LLMLinguaCompressor("m", "r", cache_size=0)
    adapter._compressor = Model()
    with pytest.raises(ValueError):
        adapter.compress_many(["a b c", "d e f"], 0.4)
