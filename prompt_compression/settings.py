"""Environment-driven settings. Every variable is listed in prompt_compression.env.example."""

import os
from dataclasses import dataclass

# Chosen by eval/benchmark.py on the held-out test set; see README.md "Model comparison".
DEFAULT_CLASSIFIER_MODEL = "typeform/distilbert-base-uncased-mnli"
DEFAULT_COMPRESSION_MODEL = "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value not in (None, "") else default


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value not in (None, "") else default


@dataclass(frozen=True)
class ClassifierSettings:
    model: str
    label_format: str
    min_confidence: float
    latency_budget_ms: float
    cache_size: int
    max_chunk_tokens: int
    # "none" or "int8" (torch dynamic quantization of Linear layers, CPU speed-up).
    quantize: str = "none"

    @classmethod
    def from_env(cls) -> "ClassifierSettings":
        return cls(
            quantize=(os.getenv("CLASSIFIER_QUANTIZE") or "none").strip().lower(),
            model=os.getenv("CLASSIFIER_MODEL") or DEFAULT_CLASSIFIER_MODEL,
            label_format=os.getenv("CLASSIFIER_LABEL_FORMAT") or "descriptive",
            min_confidence=_float("CLASSIFIER_MIN_CONFIDENCE", 0.6),
            latency_budget_ms=_float("CLASSIFIER_LATENCY_BUDGET_MS", 300.0),
            cache_size=_int("CLASSIFIER_CACHE_SIZE", 2048),
            # Premise budget per chunk; the hypothesis and special tokens need the rest of the window.
            max_chunk_tokens=_int("CLASSIFIER_MAX_CHUNK_TOKENS", 400),
        )


@dataclass(frozen=True)
class PipelineSettings:
    enabled: bool
    fail_mode: str
    timeout_s: float
    redact_sensitive: bool
    preserve_last_user: bool
    min_chars: int
    compression_model: str
    rate_non_sensitive: float
    rate_less_important: float
    eager_load: bool

    @classmethod
    def from_env(cls) -> "PipelineSettings":
        fail_mode = (os.getenv("PROMPT_COMPRESSION_FAIL_MODE") or "open").strip().lower()
        if fail_mode not in ("open", "closed"):
            raise ValueError("PROMPT_COMPRESSION_FAIL_MODE must be 'open' or 'closed'")
        return cls(
            enabled=_bool("PROMPT_COMPRESSION_ENABLED", True),
            fail_mode=fail_mode,
            timeout_s=_float("PROMPT_COMPRESSION_TIMEOUT_S", 10.0),
            redact_sensitive=_bool("REDACT_SENSITIVE", False),
            preserve_last_user=_bool("PROMPT_COMPRESSION_PRESERVE_LAST_USER", False),
            min_chars=_int("PROMPT_COMPRESSION_MIN_CHARS", 200),
            compression_model=os.getenv("PROMPT_COMPRESSION_MODEL") or DEFAULT_COMPRESSION_MODEL,
            # rate = fraction of tokens LLMLingua-2 keeps (higher => lighter compression).
            rate_non_sensitive=_float("PROMPT_COMPRESSION_RATE_NON_SENSITIVE", 0.6),
            rate_less_important=_float("PROMPT_COMPRESSION_RATE_LESS_IMPORTANT", 0.3),
            eager_load=_bool("PROMPT_COMPRESSION_EAGER_LOAD", True),
        )
