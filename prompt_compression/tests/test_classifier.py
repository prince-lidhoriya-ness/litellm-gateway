import os

import pytest

from prompt_compression.classifier import ClassifierUnavailable, PromptClassifier
from prompt_compression.labels import CRITICAL, LABELS, LESS_IMPORTANT, NON_SENSITIVE, SENSITIVE, most_restrictive
from prompt_compression.settings import DEFAULT_CLASSIFIER_MODEL, ClassifierSettings

from .fakes import FakeZeroShotPipeline

# Score vectors are in candidate-label order: sensitive, critical, non_sensitive, less_important.
CONFIDENT_LESS = [0.02, 0.03, 0.05, 0.90]
CONFIDENT_NON = [0.05, 0.05, 0.85, 0.05]
CONFIDENT_CRITICAL = [0.05, 0.85, 0.05, 0.05]
FLAT = [0.30, 0.25, 0.25, 0.20]


def make_classifier(pipeline, **overrides):
    values = dict(
        model="fake/model", label_format="descriptive", min_confidence=0.6,
        latency_budget_ms=300, cache_size=8, max_chunk_tokens=400,
    )
    values.update(overrides)
    classifier = PromptClassifier(ClassifierSettings(**values))
    classifier._pipeline = pipeline
    return classifier


def test_rule_hit_forces_sensitive_without_calling_model():
    pipeline = FakeZeroShotPipeline({}, CONFIDENT_LESS)
    result = make_classifier(pipeline).classify("thanks!! btw my email is jane.doe@example.com")
    assert result.label == SENSITIVE
    assert result.source == "rules"
    assert "email" in result.rule_hits
    assert pipeline.calls == []


def test_confident_model_label_is_used():
    result = make_classifier(FakeZeroShotPipeline({}, CONFIDENT_LESS)).classify("hello there, nice day")
    assert result.label == LESS_IMPORTANT
    assert result.source == "model"
    assert set(result.scores) == set(LABELS)


def test_low_confidence_falls_back_to_critical():
    result = make_classifier(FakeZeroShotPipeline({}, FLAT)).classify("something ambiguous")
    assert result.label == CRITICAL
    assert result.source == "fallback_low_confidence"


def test_threshold_is_configurable():
    result = make_classifier(FakeZeroShotPipeline({}, FLAT), min_confidence=0.2).classify("something ambiguous")
    assert result.label == SENSITIVE  # FLAT's top label, now above the threshold
    assert result.source == "model"


def test_inference_error_falls_back_to_critical_and_is_not_cached():
    pipeline = FakeZeroShotPipeline({}, CONFIDENT_LESS, raise_on="explode")
    classifier = make_classifier(pipeline)
    result = classifier.classify("please explode")
    assert (result.label, result.source) == (CRITICAL, "fallback_error")
    assert classifier._cache_get(classifier._cache_key("please explode")) is None


def test_load_failure_raises_classifier_unavailable_once_and_remembers_it():
    classifier = PromptClassifier(ClassifierSettings(
        model="this-org/does-not-exist-zz", label_format="descriptive", min_confidence=0.6,
        latency_budget_ms=300, cache_size=8, max_chunk_tokens=400,
    ))
    with pytest.raises(ClassifierUnavailable):
        classifier.classify("plain text with no secrets")
    with pytest.raises(ClassifierUnavailable):
        classifier.load()


def test_rules_still_work_when_model_is_unavailable():
    classifier = PromptClassifier(ClassifierSettings(
        model="this-org/does-not-exist-zz", label_format="descriptive", min_confidence=0.6,
        latency_budget_ms=300, cache_size=8, max_chunk_tokens=400,
    ))
    assert classifier.classify("key AKIAIOSFODNN7EXAMPLE").label == SENSITIVE


def test_long_text_is_chunked_and_most_restrictive_label_wins():
    pipeline = FakeZeroShotPipeline({"SECRET-ISH": CONFIDENT_CRITICAL}, CONFIDENT_LESS)
    classifier = make_classifier(pipeline, max_chunk_tokens=20)
    text = " ".join(["filler"] * 50) + " SECRET-ISH " + " ".join(["filler"] * 50)
    result = classifier.classify(text)
    assert result.chunks == 6  # 101 whitespace tokens / 20 per chunk
    assert len(pipeline.calls[0]) == 6
    assert all(len(piece.split()) <= 20 for piece in pipeline.calls[0])
    assert result.label == CRITICAL


def test_short_text_is_one_chunk():
    pipeline = FakeZeroShotPipeline({}, CONFIDENT_NON)
    result = make_classifier(pipeline).classify("a short paragraph about parks")
    assert result.chunks == 1
    assert result.label == NON_SENSITIVE


def test_label_priority_order():
    assert most_restrictive([LESS_IMPORTANT, NON_SENSITIVE]) == NON_SENSITIVE
    assert most_restrictive([LESS_IMPORTANT, CRITICAL, NON_SENSITIVE]) == CRITICAL
    assert most_restrictive([CRITICAL, SENSITIVE, LESS_IMPORTANT]) == SENSITIVE
    assert most_restrictive([LESS_IMPORTANT]) == LESS_IMPORTANT


def test_cache_is_bounded_lru_and_skips_inference():
    pipeline = FakeZeroShotPipeline({}, CONFIDENT_NON)
    classifier = make_classifier(pipeline, cache_size=2)
    classifier.classify("one")
    classifier.classify("two")
    classifier.classify("one")  # hit, refreshes "one"
    classifier.classify("three")  # evicts "two"
    assert len(pipeline.calls) == 3
    assert len(classifier._cache) == 2
    assert classifier._cache_get(classifier._cache_key("two")) is None


def test_empty_text():
    result = make_classifier(FakeZeroShotPipeline({}, CONFIDENT_NON)).classify("   ")
    assert result.source == "empty"


def test_model_name_comes_from_env(monkeypatch):
    monkeypatch.setenv("CLASSIFIER_MODEL", "some-org/some-model")
    assert ClassifierSettings.from_env().model == "some-org/some-model"
    monkeypatch.delenv("CLASSIFIER_MODEL")
    assert ClassifierSettings.from_env().model == DEFAULT_CLASSIFIER_MODEL


@pytest.mark.skipif(os.getenv("SKIP_MODEL_TESTS") == "1", reason="SKIP_MODEL_TESTS=1")
def test_selected_model_loads_and_classifies():
    classifier = PromptClassifier(ClassifierSettings.from_env())
    classifier.load()
    assert classifier.loaded
    result = classifier.classify("Hi there! Hope you're having a great day.")
    assert result.label in LABELS
    assert result.source in ("model", "fallback_low_confidence")
    assert result.chunks == 1
