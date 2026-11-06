import pytest

from prompt_compression.sensitivity import ClassifierUnavailable, SensitivityDetector
from prompt_compression.settings import SensitivitySettings

from .fakes import FakeZeroShotPipeline

# candidate order: sensitive, critical, non_sensitive, less_important
CALM = [0.10, 0.20, 0.40, 0.30]
UNSURE = [0.30, 0.25, 0.25, 0.20]      # P(sensitive) 0.30
LIKELY = [0.45, 0.20, 0.20, 0.15]      # P(sensitive) 0.45


def detector(keyword_scores=None, default=CALM, raise_on=None, **overrides):
    values = dict(model="fake", backend="nli", threshold=0.35, cache_size=8, max_chunk_tokens=16)
    values.update(overrides)
    built = SensitivityDetector(SensitivitySettings(**values))
    built._pipeline = FakeZeroShotPipeline(keyword_scores or {}, default, raise_on=raise_on)
    return built


def test_rules_hit_is_sensitive_and_the_model_is_not_asked():
    d = detector()
    result = d.check("my email is jane.doe@example.com and I need help")
    assert result.sensitive and result.source == "rules" and "email" in result.rule_hits and result.score == 1.0
    assert d._pipeline.calls == []


def test_model_probability_at_or_above_the_threshold_is_sensitive():
    d = detector({"diagnosed": LIKELY, "maybe": UNSURE})
    assert d.check("I was diagnosed with something last year").sensitive
    unsure = d.check("maybe this is private")
    assert not unsure.sensitive and unsure.score == pytest.approx(0.30)
    assert not d.check("the weather is mild today").sensitive


def test_threshold_is_adjustable():
    strict = detector({"maybe": UNSURE}, threshold=0.25)
    lenient = detector({"maybe": UNSURE}, threshold=0.50)
    assert strict.check("maybe this is private").sensitive
    assert not lenient.check("maybe this is private").sensitive


def test_the_most_sensitive_chunk_decides():
    d = detector({"secretword": LIKELY})
    text = " ".join(["plain"] * 40) + " secretword " + " ".join(["plain"] * 40)
    result = d.check(text)
    assert result.sensitive and result.chunks > 1 and result.score == pytest.approx(0.45)


def test_an_inference_error_is_treated_as_sensitive_and_not_cached():
    d = detector(raise_on="explode")
    first = d.check("please explode now")
    assert first.sensitive and first.source == "error"
    d._pipeline.raise_on = None
    again = d.check("please explode now")
    assert not again.sensitive and again.source == "model"      # retried, not pinned by the error


def test_results_are_cached_and_flagged():
    d = detector()
    first = d.check("a perfectly ordinary sentence about parks")
    second = d.check("a perfectly ordinary sentence about parks")
    assert not first.cache_hit and second.cache_hit and len(d._pipeline.calls) == 1


def test_empty_text_is_not_sensitive_and_costs_nothing():
    d = detector()
    assert d.check("   ").source == "empty" and not d.check("").sensitive
    assert d._pipeline.calls == []


def test_rules_only_never_calls_the_model():
    d = detector({"anything": LIKELY})
    assert d.rules_only("write to ops@example.com").sensitive
    assert not d.rules_only("anything at all").sensitive
    assert d._pipeline.calls == []


def test_unavailable_model_raises_so_the_fail_mode_decides(monkeypatch):
    d = SensitivityDetector(SensitivitySettings(model="fake", backend="nli"))

    def boom(*args, **kwargs):
        raise OSError("no such model")

    monkeypatch.setattr("prompt_compression.sensitivity.load_zero_shot_pipeline", boom)
    with pytest.raises(ClassifierUnavailable):
        d.check("an ordinary sentence")
    with pytest.raises(ClassifierUnavailable):                      # the failure is remembered, not retried per request
        d.check("another ordinary sentence")


def test_unknown_label_format_is_rejected():
    with pytest.raises(ValueError):
        SensitivityDetector(SensitivitySettings(model="fake", label_format="nonsense"))


# ---- embedding backend (default) ------------------------------------------------------------------------------


class _FakeEncoder:
    _model = object()   # "loaded"


class FakeHead:
    """Stands in for EmbeddingSensitivityClassifier: score = 0.9 if a keyword is present, else 0.05."""

    def __init__(self, keywords=("secretword",), threshold=0.37):
        self.keywords = keywords
        self.threshold = threshold
        self.model_name = "fake-encoder+fake-head"
        self.encoder = _FakeEncoder()
        self.calls = []

    def load(self):
        pass

    def score(self, text, max_chunk_tokens=200):
        self.calls.append(text)
        return (0.9 if any(k in text for k in self.keywords) else 0.05), 1


def embedding_detector(threshold=None, **head_kwargs):
    d = SensitivityDetector(SensitivitySettings(backend="embedding", threshold=threshold, cache_size=8))
    d._classifier = FakeHead(**head_kwargs)
    if threshold is None:
        d.threshold = d._classifier.threshold
    return d


def test_embedding_backend_is_the_default_and_uses_the_trained_threshold():
    settings = SensitivitySettings()
    assert settings.backend == "embedding" and settings.threshold is None
    d = SensitivityDetector(settings)                  # reads models/sensitivity_head.json, loads no weights
    assert 0.0 < d.threshold < 1.0 and "all-MiniLM-L6-v2" in d.model_name


def test_embedding_backend_scores_with_the_head():
    d = embedding_detector()
    hit = d.check("a sentence with secretword inside")
    assert hit.sensitive and hit.source == "model" and hit.score == pytest.approx(0.9)
    calm = d.check("Customers value reliability and after-sales support when choosing suppliers.")
    assert not calm.sensitive and calm.score == pytest.approx(0.05)


def test_embedding_threshold_override():
    d = embedding_detector(threshold=0.95)
    assert not d.check("a sentence with secretword inside").sensitive


def test_topic_hit_is_sensitive_without_the_model():
    d = embedding_detector()
    result = d.check("My doctor changed my medication after the blood test.")
    assert result.sensitive and result.source == "rules" and "topic_health" in result.rule_hits
    assert d._classifier.calls == []
    assert d.rules_only("He is going through a divorce").rule_hits == ("topic_legal",)


def test_company_finance_is_not_a_topic_hit():
    from prompt_compression.topics import topic_hits

    assert topic_hits("For fiscal 2016 Dorvance reported revenue of $50.4 million against operating costs.") == []
    assert topic_hits("The paintings are on loan from European galleries.") == []
    assert topic_hits("Thanks for being so patient with me.") == []
