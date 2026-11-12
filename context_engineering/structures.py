"""Data passed between the context-engineering stages. Nothing here carries message text except where named."""

from dataclasses import asdict, dataclass, field
from typing import Optional

# Context categories (budget accounting). "retrieved" holds older turns that JIT retrieval kept verbatim and the
# compaction summary; "current_query" is the latest user message.
SYSTEM = "system"
TOOL_DEFINITIONS = "tool_definitions"
HISTORY = "history"
TOOL_OUTPUT = "tool_output"
RETRIEVED = "retrieved"
CURRENT_QUERY = "current_query"
CATEGORIES = (SYSTEM, TOOL_DEFINITIONS, HISTORY, TOOL_OUTPUT, RETRIEVED, CURRENT_QUERY)

# Markers that make the gateway's own insertions recognisable (idempotence, and so the compression stage skips them).
STUB_MARKER = "[gateway: observation "
DUPLICATE_MARKER = "[gateway: duplicate of observation "
SUMMARY_MARKER = "[gateway: earlier conversation compacted"


@dataclass(frozen=True)
class ModelInfo:
    name: str                      # the name the client sent (a LiteLLM model group, or a provider/model string)
    resolved: str                  # the provider model behind it, when the proxy router knows it
    provider: Optional[str]
    window: int                    # max input tokens used for budgeting
    window_source: str             # "override" | "model_map" | "default"
    supports_caching: Optional[bool]   # None = unknown


@dataclass(frozen=True)
class ContextItem:
    index: int                     # position in the messages list
    role: str
    category: str
    tokens: int
    turn: int                      # number of user messages up to and including this one (0 = before the first)
    content_sha: str               # sha256 of the message's text content
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_rank: Optional[int] = None    # tool results counted from the newest (0 = newest)
    is_error: bool = False
    pinned: bool = False           # never edited by any stage
    gateway_made: bool = False     # a stub or summary the gateway inserted earlier


@dataclass(frozen=True)
class ContextProfile:
    items: tuple
    totals: dict                   # category -> tokens
    total_tokens: int
    tools_tokens: int
    last_user_index: Optional[int]
    last_assistant_index: Optional[int]
    prefix_sha: str                # system/developer messages + tool definitions
    conversation_key: str          # salted hash: identity for metrics and logs, never the text
    volatile: tuple                # volatile pattern names found in system messages
    system_tokens: int


@dataclass(frozen=True)
class BudgetPlan:
    enabled: bool
    window: int
    target_tokens: int
    output_reserve: int
    utilization: float
    pressure: str                  # low | moderate | high | over
    limits: dict
    oversized: tuple               # categories over their share
    techniques: frozenset          # what this request may use: dedupe, mask, history
    decisions: tuple               # human-readable reasons (no text from the prompt)


@dataclass(frozen=True)
class CachePlan:
    enabled: bool
    caching: str                   # supported | unsupported | unknown
    freeze_history: bool           # earlier messages must not be rewritten per question
    jit_allowed: bool
    breakpoints: Optional[list]    # cache_control_injection_points to add, or None
    decisions: tuple


@dataclass(frozen=True)
class MaskRecord:
    index: int
    ref: str
    reason: str                    # duplicate | age
    tool_name: str
    tool_call_id: str
    tokens_before: int
    tokens_after: int
    stored: bool


@dataclass(frozen=True)
class HistoryRecord:
    action: str                    # compacted | retrieved | protected | restored (its ref was mentioned)
    ref: str
    original_indexes: tuple
    tokens: int
    score: Optional[float] = None


@dataclass
class ContextReport:
    status: str = "ok"
    mode: str = "enforce"
    model: str = ""
    window: int = 0
    window_source: str = ""
    caching: str = "unknown"
    tokens_before: int = 0
    tokens_after: int = 0
    by_category_before: dict = field(default_factory=dict)
    by_category_after: dict = field(default_factory=dict)
    utilization_before: float = 0.0
    utilization_after: float = 0.0
    pressure: str = "low"
    oversized: list = field(default_factory=list)
    techniques: list = field(default_factory=list)
    decisions: list = field(default_factory=list)
    masked: list = field(default_factory=list)
    history: list = field(default_factory=list)
    saved_by_technique: dict = field(default_factory=dict)   # deduplication / masking / compaction / jit_retrieval
    restored: dict = field(default_factory=dict)             # originals kept because their ref was mentioned
    retrieved_turns: int = 0
    summary_index: Optional[int] = None
    summary_source: str = ""
    volatile_prefix: list = field(default_factory=list)
    breakpoints_added: bool = False
    stages_failed: list = field(default_factory=list)
    invariant_violations: list = field(default_factory=list)
    stage_ms: dict = field(default_factory=dict)
    elapsed_ms: float = 0.0
    conversation_key: str = ""
    prefix_sha: str = ""
    hints: dict = field(default_factory=dict)

    @property
    def tokens_saved(self) -> int:
        return max(0, self.tokens_before - self.tokens_after)

    def as_metadata(self) -> dict:
        data = asdict(self)
        data["masked"] = [asdict(r) if not isinstance(r, dict) else r for r in self.masked]
        data["history"] = [asdict(r) if not isinstance(r, dict) else r for r in self.history]
        data["tokens_saved"] = self.tokens_saved
        return data
