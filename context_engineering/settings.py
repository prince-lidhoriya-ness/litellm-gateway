"""Environment-driven settings. Every variable is listed, with its default, in ../context_engineering.env.example.

The defaults follow docs/context-engineering-blueprint.md: the low-risk techniques (budget accounting, cache-aware
construction, duplicate folding and masking of large old tool outputs) are on; the lossy history techniques (JIT
retrieval, compaction) are off until they have been checked on your own traffic.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

MODES = ("enforce", "shadow")
FAIL_MODES = ("open", "closed")
STORE_BACKENDS = ("memory", "redis", "none")
CACHE_SUPPORT = ("auto", "on", "off")
FREEZE = ("auto", "always", "never")
MASK_TRIGGERS = ("always", "pressure")
COMPACTION_MODES = ("extractive", "llm")
RETRIEVAL_BACKENDS = ("bm25", "hybrid")

# Budget shares of the effective target per category (the reference repository's example split, tool outputs 35%,
# history 30%, retrieved 20%; system and tool definitions get a share too so an oversized system prompt is reported).
# A category over its share is "oversized"; that is a trigger, not a hard cut: system, tool definitions and the current
# query are never reduced.
DEFAULT_SHARES = "system=0.10,tool_definitions=0.10,history=0.30,tool_output=0.35,retrieved=0.15,current_query=0.30"


def _raw(*names: str) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip() != "":
            return value.strip()
    return None


def _bool(name: str, default: bool) -> bool:
    value = _raw(name)
    return default if value is None else value.lower() in ("1", "true", "yes", "on")


def _float(name: str, default: float) -> float:
    value = _raw(name)
    return float(value) if value is not None else default


def _int(name: str, default: int) -> int:
    value = _raw(name)
    return int(value) if value is not None else default


def _choice(name: str, default: str, choices: tuple) -> str:
    value = (_raw(name) or default).lower()
    if value not in choices:
        raise ValueError(f"{name} must be one of {', '.join(choices)}")
    return value


def _fraction(name: str, default: float, low: float = 0.0, high: float = 1.0) -> float:
    value = _float(name, default)
    if not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return value


def parse_shares(raw: str) -> dict:
    shares = {}
    for part in raw.replace(";", ",").split(","):
        if not part.strip():
            continue
        key, _, value = part.partition("=")
        shares[key.strip().lower()] = float(value)
    unknown = set(shares) - {"system", "tool_definitions", "history", "tool_output", "retrieved", "current_query"}
    if unknown:
        raise ValueError(f"CONTEXT_BUDGET_SHARES has unknown categories {sorted(unknown)}")
    return shares


@dataclass(frozen=True)
class ContextSettings:
    # --- the stage as a whole ---
    enabled: bool = True
    mode: str = "enforce"                      # shadow: run and report, but forward the original request
    fail_mode: str = "open"                    # open: forward the original request; closed: HTTP 503
    timeout_s: float = 2.0                     # the stage is pure Python; this only guards pathological inputs
    min_tokens: int = 1000                     # smaller requests skip the stage (nothing to gain)
    hash_salt: str = ""

    # --- A. budget manager ---
    budget_enabled: bool = True
    window_tokens: int = 0                     # 0: from LiteLLM's model map (max_input_tokens)
    default_window_tokens: int = 32768         # when the model is unknown (virtual names such as smart-*)
    max_utilization: float = 0.70              # effective target = this share of the window (repo heuristic)
    reserved_output_tokens: int = 4096         # reserve when the request has no max_tokens
    safety_buffer: float = 0.10                # share of the target kept free (tokenizer mismatch, provider overhead)
    shares: dict = field(default_factory=lambda: parse_shares(DEFAULT_SHARES))

    # --- B. JIT retrieval of older turns ---
    jit_enabled: bool = False
    recent_turns: int = 4                      # the newest user turns are never compacted or dropped
    jit_max_turns: int = 3                     # at most this many older turns are retrieved verbatim
    jit_min_score: float = 0.0                 # a turn must score above this (BM25; > 0 means a shared rare term)
    jit_backend: str = "bm25"                  # hybrid: BM25 + the MiniLM encoder the sensitivity check loads
    jit_on_caching_providers: bool = False     # query-dependent selection breaks the provider's prefix cache

    # --- C. observation masking ---
    masking_enabled: bool = True
    dedup_enabled: bool = True
    dedup_min_tokens: int = 50                 # byte-identical tool outputs at least this long are folded
    observation_max_tokens: int = 400          # larger tool outputs are eligible for masking
    observation_keep_recent: int = 3           # the newest eligible tool outputs stay in full
    observation_batch: int = 4                 # masks advance in batches so the prefix changes rarely
    observation_error_guard: int = 3           # error outputs among the newest N tool results are never masked
    observation_stub_max_tokens: int = 150
    observation_head_tail_lines: int = 3
    mask_trigger: str = "always"               # pressure: mask only when the budget says tool outputs are too big

    # --- store for masked / compacted originals ---
    store_backend: str = "memory"
    store_ttl_s: int = 3600
    store_max_items: int = 2048
    store_allow_sensitive: bool = False        # redis only: content with a rules hit is never written there
    redis_url: str = ""

    # --- D. compaction ---
    compaction_enabled: bool = False
    compaction_threshold: float = 0.80         # utilization (of the effective target) that triggers history work
    compaction_batch_turns: int = 4            # the compacted span grows in steps of this many turns
    compaction_mode: str = "extractive"        # llm: an asynchronous summary replaces the extractive one later
    compaction_model: str = ""                 # LiteLLM model name for llm mode (keep it local for privacy)
    compaction_max_summary_tokens: int = 800
    compaction_max_summary_ratio: float = 0.70  # a summary this big relative to its span is not worth it
    compaction_verbatim_block_tokens: int = 150  # code / data blocks up to this size are copied verbatim

    # --- E. cache-aware prompt construction ---
    prefix_cache_enabled: bool = True
    cache_support: str = "auto"                # auto: LiteLLM's supports_prompt_caching; on / off: override
    freeze_history: str = "auto"               # auto: freeze unless the provider is known not to cache
    inject_breakpoints: bool = True            # Anthropic-style providers: add cache_control_injection_points
    breakpoint_min_tokens: int = 1024          # below this the provider would not cache the prefix anyway
    relocate_volatile: bool = False            # move date/uuid lines out of the system prompt (changes the prompt)
    canonical_tools: bool = False              # sort tool definitions by name (changes the request)

    @classmethod
    def from_env(cls) -> "ContextSettings":
        recent_turns = _int("CONTEXT_RECENT_TURNS", 4)
        if recent_turns < 1:
            raise ValueError("CONTEXT_RECENT_TURNS must be at least 1")
        batch = _int("OBSERVATION_MASK_BATCH", 4)
        compaction_batch = _int("CONTEXT_COMPACTION_BATCH_TURNS", 4)
        if batch < 1 or compaction_batch < 1:
            raise ValueError("OBSERVATION_MASK_BATCH and CONTEXT_COMPACTION_BATCH_TURNS must be at least 1")
        return cls(
            enabled=_bool("CONTEXT_ENGINEERING_ENABLED", True),
            mode=_choice("CONTEXT_ENGINEERING_MODE", "enforce", MODES),
            fail_mode=_choice("CONTEXT_ENGINEERING_FAIL_MODE", "open", FAIL_MODES),
            timeout_s=_float("CONTEXT_ENGINEERING_TIMEOUT_S", 2.0),
            min_tokens=_int("CONTEXT_ENGINEERING_MIN_TOKENS", 1000),
            hash_salt=_raw("CONTEXT_HASH_SALT", "OBS_HASH_SALT") or "",
            budget_enabled=_bool("CONTEXT_BUDGET_ENABLED", True),
            window_tokens=_int("CONTEXT_WINDOW_TOKENS", 0),
            default_window_tokens=_int("CONTEXT_DEFAULT_WINDOW_TOKENS", 32768),
            max_utilization=_fraction("CONTEXT_MAX_UTILIZATION", 0.70, 0.05, 1.0),
            reserved_output_tokens=_int("CONTEXT_RESERVED_OUTPUT_TOKENS", 4096),
            safety_buffer=_fraction("CONTEXT_SAFETY_BUFFER", 0.10, 0.0, 0.9),
            shares=parse_shares(_raw("CONTEXT_BUDGET_SHARES") or DEFAULT_SHARES),
            jit_enabled=_bool("JIT_RETRIEVAL_ENABLED", False),
            recent_turns=recent_turns,
            jit_max_turns=_int("JIT_RETRIEVAL_MAX_TURNS", 3),
            jit_min_score=_float("JIT_RETRIEVAL_MIN_SCORE", 0.0),
            jit_backend=_choice("JIT_RETRIEVAL_BACKEND", "bm25", RETRIEVAL_BACKENDS),
            jit_on_caching_providers=_bool("JIT_RETRIEVAL_ON_CACHING_PROVIDERS", False),
            masking_enabled=_bool("OBSERVATION_MASKING_ENABLED", True),
            dedup_enabled=_bool("OBSERVATION_DEDUP_ENABLED", True),
            dedup_min_tokens=_int("OBSERVATION_DEDUP_MIN_TOKENS", 50),
            observation_max_tokens=_int("OBSERVATION_MAX_TOKENS", 400),
            observation_keep_recent=_int("OBSERVATION_KEEP_RECENT", 3),
            observation_batch=batch,
            observation_error_guard=_int("OBSERVATION_ERROR_GUARD", 3),
            observation_stub_max_tokens=_int("OBSERVATION_STUB_MAX_TOKENS", 150),
            observation_head_tail_lines=_int("OBSERVATION_HEAD_TAIL_LINES", 3),
            mask_trigger=_choice("OBSERVATION_MASK_TRIGGER", "always", MASK_TRIGGERS),
            store_backend=_choice("CONTEXT_STORE", "memory", STORE_BACKENDS),
            store_ttl_s=_int("CONTEXT_STORE_TTL_S", 3600),
            store_max_items=_int("CONTEXT_STORE_MAX_ITEMS", 2048),
            store_allow_sensitive=_bool("CONTEXT_STORE_ALLOW_SENSITIVE", False),
            redis_url=_raw("CONTEXT_STORE_REDIS_URL") or "",
            compaction_enabled=_bool("CONTEXT_COMPACTION_ENABLED", False),
            compaction_threshold=_fraction("CONTEXT_COMPACTION_THRESHOLD", 0.80, 0.05, 2.0),
            compaction_batch_turns=compaction_batch,
            compaction_mode=_choice("CONTEXT_COMPACTION_MODE", "extractive", COMPACTION_MODES),
            compaction_model=_raw("CONTEXT_COMPACTION_MODEL") or "",
            compaction_max_summary_tokens=_int("CONTEXT_COMPACTION_MAX_SUMMARY_TOKENS", 800),
            compaction_max_summary_ratio=_fraction("CONTEXT_COMPACTION_MAX_SUMMARY_RATIO", 0.70, 0.05, 1.0),
            compaction_verbatim_block_tokens=_int("CONTEXT_COMPACTION_VERBATIM_BLOCK_TOKENS", 150),
            prefix_cache_enabled=_bool("PREFIX_CACHE_OPTIMIZATION_ENABLED", True),
            cache_support=_choice("PREFIX_CACHE_PROVIDER_SUPPORT", "auto", CACHE_SUPPORT),
            freeze_history=_choice("PREFIX_CACHE_FREEZE_HISTORY", "auto", FREEZE),
            inject_breakpoints=_bool("PREFIX_CACHE_INJECT_BREAKPOINTS", True),
            breakpoint_min_tokens=_int("PREFIX_CACHE_BREAKPOINT_MIN_TOKENS", 1024),
            relocate_volatile=_bool("PREFIX_CACHE_RELOCATE_VOLATILE", False),
            canonical_tools=_bool("PREFIX_CACHE_CANONICAL_TOOLS", False),
        )
