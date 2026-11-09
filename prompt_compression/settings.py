"""Environment-driven settings. Every variable is listed in prompt_compression.env.example."""

import os
from dataclasses import dataclass
from typing import Optional

# The zero-shot NLI model that scores "sensitive". Chosen by eval/benchmark.py; see eval/results/SELECTION.md.
DEFAULT_CLASSIFIER_MODEL = "typeform/distilbert-base-uncased-mnli"
DEFAULT_COMPRESSION_MODEL = "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"
# Hugging Face commits the defaults are pinned to, so a changed upstream model can never change behaviour silently
# (PROJECT_AUDIT_REPORT.md, F-19S). A model other than the default runs at the revision given in its *_REVISION
# variable, or at "main" when that is empty.
DEFAULT_COMPRESSION_REVISION = "5f0c82792b7ea14c6484e015b6a072009496b7f2"
DEFAULT_ENCODER = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_ENCODER_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"

# Router actions that can be switched on or off (PROMPT_COMPRESSION_ROUTES). On by default: "narrative" (compress prose),
# "passages" and "records" (drop whole passages / log lines the question does not need). The two selection routes kept
# accuracy at 1.000 on the research benchmark (eval/results/guard_eval_real.md) and are where nearly all the savings come
# from: with only "narrative" the benchmark prompts saved 11% (QA) and 0% (logs); with all three 39% and 66%
# (reports/playground-ab/REPORT.md). "history" needs a token budget and stays off.
ROUTE_NAMES = ("narrative", "passages", "records", "history")
DEFAULT_ROUTES = "narrative,passages,records"
MODES = ("enforce", "shadow")
# Which messages passage and record selection may thin out. "latest_user" (default): only the latest user message, so
# earlier turns are never re-selected against a new question (that silently lost context in multi-turn chats and changed
# the conversation prefix on every request, PROJECT_AUDIT_REPORT.md F-06/F-15). "all": every eligible message (the
# behaviour before the audit).
SELECTION_SCOPES = ("latest_user", "all")


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


def _routes(name: str, default: str) -> frozenset:
    raw = os.getenv(name)
    value = default if raw is None or raw.strip() == "" else raw
    names = {part.strip().lower() for part in value.replace(";", ",").split(",") if part.strip()}
    unknown = names.difference(ROUTE_NAMES)
    if unknown:
        raise ValueError(f"{name} has unknown route(s) {sorted(unknown)}; valid: {', '.join(ROUTE_NAMES)}")
    return frozenset(names)


SENSITIVITY_BACKENDS = ("embedding", "nli")
# Threshold of the legacy zero-shot backend (smallest value with dev recall 1.0; flags about two thirds of ordinary
# prompts, which is why it is no longer the default).
NLI_DEFAULT_THRESHOLD = 0.35


@dataclass(frozen=True)
class SensitivitySettings:
    """The model half of the sensitivity check (the deterministic half is rules.py and topics.py).

    backend "embedding" (default): sentence embedding + trained logistic-regression head (embedding_classifier.py);
            its threshold comes from models/sensitivity_head.json unless SENSITIVITY_THRESHOLD is set.
    backend "nli": the earlier zero-shot NLI model (CLASSIFIER_MODEL), kept for comparison and rollback.
    """

    model: str = DEFAULT_CLASSIFIER_MODEL
    label_format: str = "descriptive"
    backend: str = "embedding"
    # A text counts as sensitive when the model's probability reaches this value. None: the backend's own default
    # (the head's cross-validated threshold, or NLI_DEFAULT_THRESHOLD for "nli").
    threshold: Optional[float] = None
    latency_budget_ms: float = 300.0
    cache_size: int = 2048
    max_chunk_tokens: int = 400
    # "none" or "int8" (torch dynamic quantization of Linear layers, CPU speed-up).
    quantize: str = "none"
    # Hugging Face revision of the embedding encoder; None = DEFAULT_ENCODER_REVISION for the default encoder.
    encoder_revision: Optional[str] = None
    # Encoder windows per forward pass (bounds memory on very long prompts).
    batch_size: int = 32

    @classmethod
    def from_env(cls) -> "SensitivitySettings":
        backend = (os.getenv("SENSITIVITY_BACKEND") or "embedding").strip().lower()
        if backend not in SENSITIVITY_BACKENDS:
            raise ValueError(f"SENSITIVITY_BACKEND must be one of {', '.join(SENSITIVITY_BACKENDS)}")
        raw_threshold = os.getenv("SENSITIVITY_THRESHOLD")
        return cls(
            quantize=(os.getenv("CLASSIFIER_QUANTIZE") or "none").strip().lower(),
            model=os.getenv("CLASSIFIER_MODEL") or DEFAULT_CLASSIFIER_MODEL,
            label_format=os.getenv("CLASSIFIER_LABEL_FORMAT") or "descriptive",
            backend=backend,
            threshold=float(raw_threshold) if raw_threshold not in (None, "") else None,
            latency_budget_ms=_float("CLASSIFIER_LATENCY_BUDGET_MS", 300.0),
            cache_size=_int("CLASSIFIER_CACHE_SIZE", 2048),
            # Premise budget per chunk; the hypothesis and special tokens need the rest of the window.
            max_chunk_tokens=_int("CLASSIFIER_MAX_CHUNK_TOKENS", 400),
            encoder_revision=os.getenv("SENSITIVITY_ENCODER_REVISION") or None,
            batch_size=max(1, _int("CLASSIFIER_BATCH_SIZE", 32)),
        )


@dataclass(frozen=True)
class PipelineSettings:
    # --- gate ---
    enabled: bool = True
    fail_mode: str = "open"
    timeout_s: float = 10.0
    # Requests with fewer text tokens than this are not processed at all (the classifier alone would cost more
    # than the compression can save; the earlier local pipeline run put the useful window at about 50 tokens and up).
    min_tokens: int = 50
    # Requests with more text tokens than this skip the pipeline ("too_large"): the work would not finish inside the
    # timeout anyway. 0 = no limit.
    max_input_tokens: int = 32000
    # Pipelines running at the same time in one worker process. A request that finds them all busy is sent unchanged
    # ("busy") instead of queueing behind them into a timeout.
    max_concurrency: int = 4
    # "enforce": send the compressed prompt. "shadow": compute and report, but send the original.
    mode: str = "enforce"
    # --- keep verbatim ---
    redact_sensitive: bool = False
    preserve_last_user: bool = False
    # In the latest user message the first and the last paragraph (instruction and question) are never compressed.
    protect_edges: bool = True
    # A paragraph in which this share of the words carries digits, underscores, paths, camelCase or names is exact text.
    exact_density: float = 0.15
    # --- compress text ---
    compression_model: str = DEFAULT_COMPRESSION_MODEL
    # None = DEFAULT_COMPRESSION_REVISION for the default model, "main" otherwise.
    compression_model_revision: Optional[str] = None
    # LLMLingua-2 rate = fraction of tokens kept (0.4 gives about 2x on prose in the local calibration).
    rate: float = 0.4
    # Largest ratio (tokens before / after) accepted for one compressed block; above it the block is retried lighter
    # once and then left as it was. The report supports 3x for prose (summarization) and no more.
    max_ratio: float = 3.0
    # Prose blocks shorter than this many characters are never compressed.
    min_chars: int = 200
    # At most this many LLMLingua-2 calls per message (each costs about a second of CPU).
    max_compress_calls: int = 6
    # ... and at most this many per request, over all messages (the longest runs first). Calls answered from the
    # compression cache do not count.
    max_compress_calls_per_request: int = 12
    # Compressed outputs remembered per worker, keyed by text and rate: a conversation's earlier turns are compressed
    # once and then replayed byte for byte, which also keeps the prompt prefix stable for provider prompt caching.
    compress_cache_size: int = 512
    eager_load: bool = True
    # Per-message report entries copied into spend_logs_metadata (the latest ones). The full list stays in the request
    # metadata; spend-log rows stay bounded however long the conversation is. evals/ read message [0] of 1-message runs.
    spend_log_messages: int = 8
    # --- select or drop ---
    # Which router actions are active; see ROUTE_NAMES.
    routes: frozenset = frozenset({"narrative", "passages", "records"})
    selection_scope: str = "latest_user"
    # Turn passage and record selection off for requests that need the whole text (summarise, translate, review ...).
    intent_gate: bool = True
    # "passages" route: needs at least this many passage blocks holding at least this many tokens, and keeps this
    # share of their tokens. Short material is left alone: selection is not worth its risk there. 100 tokens / 10 lines
    # are the guards the quality evaluation ran with (eval/guard_eval.py); the earlier 300 / 20 stopped both routes on
    # typical prompts (a 9-paragraph document, an 11-line log), so they never fired.
    min_passages: int = 6
    min_passage_tokens: int = 100
    passage_keep_ratio: float = 0.5
    # "records" route: blocks with at least this many lines are candidates; neighbours kept around each match.
    record_min_lines: int = 10
    record_context_lines: int = 1
    # "history" route: 0 = off even if the route is listed; otherwise trim oldest whole turns above this many tokens.
    history_max_tokens: int = 0
    history_keep_messages: int = 6

    @classmethod
    def from_env(cls) -> "PipelineSettings":
        fail_mode = (os.getenv("PROMPT_COMPRESSION_FAIL_MODE") or "open").strip().lower()
        if fail_mode not in ("open", "closed"):
            raise ValueError("PROMPT_COMPRESSION_FAIL_MODE must be 'open' or 'closed'")
        mode = (os.getenv("PROMPT_COMPRESSION_MODE") or "enforce").strip().lower()
        if mode not in MODES:
            raise ValueError("PROMPT_COMPRESSION_MODE must be 'enforce' or 'shadow'")
        scope = (os.getenv("PROMPT_COMPRESSION_SELECTION_SCOPE") or "latest_user").strip().lower()
        if scope not in SELECTION_SCOPES:
            raise ValueError(f"PROMPT_COMPRESSION_SELECTION_SCOPE must be one of {', '.join(SELECTION_SCOPES)}")
        max_ratio = _float("PROMPT_COMPRESSION_MAX_RATIO", 3.0)
        if max_ratio < 1.0:
            raise ValueError("PROMPT_COMPRESSION_MAX_RATIO must be at least 1.0")
        return cls(
            enabled=_bool("PROMPT_COMPRESSION_ENABLED", True),
            fail_mode=fail_mode,
            timeout_s=_float("PROMPT_COMPRESSION_TIMEOUT_S", 10.0),
            min_tokens=_int("PROMPT_COMPRESSION_MIN_TOKENS", 50),
            max_input_tokens=_int("PROMPT_COMPRESSION_MAX_INPUT_TOKENS", 32000),
            max_concurrency=max(1, _int("PROMPT_COMPRESSION_MAX_CONCURRENCY", 4)),
            mode=mode,
            redact_sensitive=_bool("REDACT_SENSITIVE", False),
            preserve_last_user=_bool("PROMPT_COMPRESSION_PRESERVE_LAST_USER", False),
            protect_edges=_bool("PROMPT_COMPRESSION_PROTECT_EDGES", True),
            exact_density=_float("PROMPT_COMPRESSION_EXACT_DENSITY", 0.15),
            compression_model=os.getenv("PROMPT_COMPRESSION_MODEL") or DEFAULT_COMPRESSION_MODEL,
            compression_model_revision=os.getenv("PROMPT_COMPRESSION_MODEL_REVISION") or None,
            rate=_float("PROMPT_COMPRESSION_RATE", 0.4),
            max_ratio=max_ratio,
            min_chars=_int("PROMPT_COMPRESSION_MIN_CHARS", 200),
            max_compress_calls=_int("PROMPT_COMPRESSION_MAX_CALLS", 6),
            max_compress_calls_per_request=_int("PROMPT_COMPRESSION_MAX_CALLS_PER_REQUEST", 12),
            compress_cache_size=_int("PROMPT_COMPRESSION_CACHE_SIZE", 512),
            eager_load=_bool("PROMPT_COMPRESSION_EAGER_LOAD", True),
            spend_log_messages=max(0, _int("PROMPT_COMPRESSION_SPEND_LOG_MESSAGES", 8)),
            routes=_routes("PROMPT_COMPRESSION_ROUTES", DEFAULT_ROUTES),
            selection_scope=scope,
            intent_gate=_bool("PROMPT_COMPRESSION_INTENT_GATE", True),
            min_passages=_int("PROMPT_COMPRESSION_MIN_PASSAGES", 6),
            min_passage_tokens=_int("PROMPT_COMPRESSION_MIN_PASSAGE_TOKENS", 100),
            passage_keep_ratio=_float("PROMPT_COMPRESSION_PASSAGE_KEEP_RATIO", 0.5),
            record_min_lines=_int("PROMPT_COMPRESSION_RECORD_MIN_LINES", 10),
            record_context_lines=_int("PROMPT_COMPRESSION_RECORD_CONTEXT_LINES", 1),
            history_max_tokens=_int("PROMPT_COMPRESSION_HISTORY_MAX_TOKENS", 0),
            history_keep_messages=_int("PROMPT_COMPRESSION_HISTORY_KEEP_MESSAGES", 6),
        )


def resolve_revision(model: str, revision: Optional[str], default_model: str, default_revision: str) -> str:
    """The Hugging Face revision to load: the explicit one, the pinned default for the default model, else "main"."""
    if revision:
        return revision
    return default_revision if model == default_model else "main"
