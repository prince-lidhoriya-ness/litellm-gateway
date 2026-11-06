"""Prometheus metrics for the prompt pipeline.

Registered on the default prometheus_client registry, which LiteLLM's built-in
`prometheus` callback serves at /metrics, so these appear next to litellm_*.
Labels are low-cardinality only; user, key, team and request ids are never labels.
"""

import threading

from prometheus_client import Counter, Gauge, Histogram

# Every label name used below. tests/test_metrics.py fails if a metric uses anything else.
ALLOWED_LABELS = frozenset({"model", "label", "route", "status", "source", "rule", "result", "mode", "reason", "component"})

_LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

REQUESTS = Counter(
    "prompt_pipeline_requests", "Chat requests seen by the pipeline, by request category and outcome.",
    ["model", "label", "status"],
)
MESSAGES = Counter(
    "prompt_pipeline_messages", "Classified messages by label, routing outcome and decision source.",
    ["label", "route", "source"],
)
CLASSIFIER_LATENCY = Histogram(
    "prompt_pipeline_classifier_latency_seconds", "Classifier time per message.", ["label"], buckets=_LATENCY_BUCKETS,
)
COMPRESS_LATENCY = Histogram(
    "prompt_pipeline_compress_latency_seconds", "LLMLingua-2 time per compressed message.", ["label"],
    buckets=_LATENCY_BUCKETS,
)
PIPELINE_DURATION = Histogram(
    "prompt_pipeline_duration_seconds", "Whole pre-call hook time (classify + route + compress).", ["status"],
    buckets=_LATENCY_BUCKETS,
)
TOP_SCORE = Histogram(
    "prompt_pipeline_classifier_top_score", "Classifier top score per model-classified message.", ["label"],
    buckets=(0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0),
)
TOKENS_BEFORE = Counter(
    "prompt_pipeline_tokens_before", "Prompt tokens before compression (cl100k_base).", ["model", "label"],
)
TOKENS_AFTER = Counter(
    "prompt_pipeline_tokens_after", "Prompt tokens after compression (cl100k_base).", ["model", "label"],
)
TOKENS_SAVED = Counter(
    "prompt_pipeline_tokens_saved", "Prompt tokens removed by compression.", ["model", "label"],
)
SHADOW_TOKENS_SAVED = Counter(
    "prompt_pipeline_shadow_tokens_saved",
    "Tokens compression would have removed in shadow mode (the original prompt was sent).", ["model", "label"],
)
COMPRESSION_RATIO = Histogram(
    "prompt_pipeline_compression_ratio", "tokens_before / tokens_after per request.", ["label"],
    buckets=(1.0, 1.1, 1.25, 1.5, 2.0, 3.0, 4.0, 6.0, 10.0),
)
RULE_HITS = Counter("prompt_pipeline_rule_hits", "Sensitive-data rule hits, by rule type.", ["rule"])
CLASSIFIER_CACHE = Counter("prompt_pipeline_classifier_cache", "Classifier LRU cache lookups.", ["result"])
REDACTIONS = Counter("prompt_pipeline_redactions", "PII spans replaced by placeholders.", ["label"])
FAILURES = Counter(
    "prompt_pipeline_failures", "Pipeline failures by fail mode (open/closed) and reason.", ["mode", "reason"],
)
MODEL_LOAD_SECONDS = Gauge("prompt_pipeline_model_load_seconds", "Model load time at startup.", ["component"])
MODEL_LOADED = Gauge("prompt_pipeline_model_loaded", "1 if the model loaded, 0 if loading failed.", ["component"])
COMPUTE_SECONDS = Counter(
    "prompt_pipeline_compute_seconds", "Local CPU/GPU time spent in classifier and compressor.", ["component"],
)
ESTIMATED_COMPUTE_COST = Counter(
    "prompt_pipeline_estimated_compute_cost_usd",
    "ESTIMATE: compute_seconds x OBS_*_HOURLY_RATE_USD / 3600 for the local models.", ["component"],
)

_model_values: set = set()
_model_lock = threading.Lock()


def bounded_model(model: object, limit: int) -> str:
    """Model label value; client-chosen names past `limit` distinct values collapse to "other"."""
    name = str(model or "unknown")[:80]
    with _model_lock:
        if name in _model_values:
            return name
        if len(_model_values) < limit:
            _model_values.add(name)
            return name
    return "other"
