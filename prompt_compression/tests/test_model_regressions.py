"""The audit's identifier cases on the real LLMLingua-2 model (STRATEGY.md, H3 and Phase 1.7).

These need the pinned model weights. They run offline (HF_HUB_OFFLINE=1) and are skipped when the weights are not on
this machine, so the plain unit-test job stays fast. CI runs them inside the built image, where the weights are baked
in (.github/workflows/ci.yml, job "image"). Sensitivity uses the rule-based test double: what is under test here is
compression.
"""

import os

import pytest

from prompt_compression.compressor_adapter import LLMLinguaCompressor
from prompt_compression.settings import DEFAULT_COMPRESSION_MODEL

from .audit_cases import MEETING_DATES, MEETING_OWNERS, case_g, case_j, meeting_notes
from .test_pipeline import make_pipeline


@pytest.fixture(scope="module")
def compressor():
    previous = {name: os.environ.get(name) for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")}
    os.environ["HF_HUB_OFFLINE"] = os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        model = LLMLinguaCompressor(DEFAULT_COMPRESSION_MODEL, None, cache_size=0)
        try:
            model.load()
        except Exception as exc:          # weights not on this machine: nothing to test against
            if os.environ.get("GATEWAY_REQUIRE_MODEL_TESTS") == "1":
                raise                     # CI's image job: the weights are baked in, a skip would be a false pass
            pytest.skip(f"LLMLingua-2 weights unavailable offline ({type(exc).__name__})")
        yield model
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def run(messages, compressor):
    pipeline, _, _ = make_pipeline(compressor=compressor, routes=frozenset({"narrative", "logfold"}), protect_edges=True,
                                   min_chars=200)
    new, report = pipeline.process(messages)
    return "\n".join(m["content"] for m in new if isinstance(m.get("content"), str)), report


def test_exp8_real_model_keeps_iso_dates_and_hyphenated_owners(compressor):
    text, report = run([{"role": "user", "content": "Meeting notes:\n\n" + meeting_notes(repeat=1)
                         + "\n\nWhat are the deadlines?"}], compressor)
    assert report.tokens_after < report.tokens_before
    assert [d for d in MEETING_DATES if d not in text] == []          # audit: 5 of 10 survived
    assert [o for o in MEETING_OWNERS if o not in text] == []         # audit: 5 of 10 survived


def test_case_j_real_model_keeps_every_identifier_byte_for_byte(compressor):
    messages, needles = case_j()
    text, report = run(messages, compressor)
    assert report.tokens_after < report.tokens_before
    assert [n for n in needles if n not in text] == []                # audit: 1 of 5 exact
    assert "NIMBUS - 5044" not in text and "3. 11. 4" not in text


def test_case_g_real_model_keeps_the_configuration_key_intact(compressor):
    messages, needles = case_g()
    text, report = run(messages, compressor)
    assert report.tokens_after < report.tokens_before
    assert [n for n in needles if n not in text] == []                # audit: IDLE _ TIMEOUT _ SECONDS
    assert "IDLE _ TIMEOUT" not in text
