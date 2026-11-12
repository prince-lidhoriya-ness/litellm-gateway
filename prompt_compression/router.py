"""Router: the task type picks the action for every unit. It only decides; actions.py does the work.

Inputs are the units that "Segment and classify" produced (what kind of text, sensitive or not) and the request
context (the question, which message is the latest user message). Output is a Plan:

    keep      code, structured data, identifier-dense text, sensitive text, the instruction and the question
    select    whole units that the task does not need can be dropped: old chat turns, passages, log lines
    compress  running prose goes to LLMLingua-2

Evidence for each rule is in reports/compression-fit/REPORT.md, sections 4 and 7.

Two limits on "select" (PROJECT_AUDIT_REPORT.md, F-06 and F-07):
  scope   with selection_scope "latest_user" (default) only units of the latest user message may be selected; earlier
          turns are history and are never re-selected against a new question
  intent  a request that needs the whole text (summarise, translate, review ..., intent.py) selects nothing
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

from prompt_compression.intent import LOOKUP, TRANSFORM
from prompt_compression.segmenter import CODE, EXACT, PROSE, STRUCTURED
from prompt_compression.selectors import trim_history
from prompt_compression.settings import PipelineSettings
from prompt_compression.units import COMPRESS, KEEP, SELECT, Unit

RECORD_SUBTYPES = ("log", "jsonl", "csv", "tsv", "table", "json")


@dataclass
class Plan:
    units: list
    query: Optional[str] = None
    passages: list = field(default_factory=list)    # units a passage selection may drop
    records: list = field(default_factory=list)     # structured blocks a record selection may thin out
    reasons: dict = field(default_factory=dict)     # reason -> number of units kept verbatim for it
    intent: str = LOOKUP


def route(units: list, settings: PipelineSettings, query: Optional[str], last_user_index: Optional[int],
          count_tokens: Callable[[str], int], intent: str = LOOKUP) -> Plan:
    plan = Plan(units=units, query=(query or "").strip() or None, intent=intent)
    routes = settings.routes
    selection_allowed = not (settings.intent_gate and intent == TRANSFORM)

    def selectable(unit: Unit) -> bool:
        return selection_allowed and (settings.selection_scope == "all" or unit.message == last_user_index)

    # the instruction and the question of the latest user message
    if settings.protect_edges and last_user_index is not None:
        filled = [u for u in units if u.message == last_user_index and u.filled]
        for unit in filled[:1] + filled[-1:]:
            unit.edge = True

    candidates = []
    for unit in units:
        if not unit.filled:
            continue
        if unit.sensitive:
            _keep(plan, unit, "sensitive")
        elif settings.preserve_last_user and unit.message == last_user_index:
            _keep(plan, unit, "last_user")
        elif unit.edge:
            _keep(plan, unit, "edge")
        elif unit.kind == CODE:
            _keep(plan, unit, "code")
        elif unit.kind == STRUCTURED:
            if plan.query and "records" in routes and unit.subtype in RECORD_SUBTYPES and selectable(unit):
                unit.action, unit.reason = SELECT, "records"
                plan.records.append(unit)
            else:
                _keep(plan, unit, "structured")
        elif unit.kind == EXACT:
            _keep(plan, unit, "exact")
            if selectable(unit):
                candidates.append(unit)         # may still be dropped whole as a passage, never compressed
        elif unit.kind == PROSE:
            if selectable(unit):
                candidates.append(unit)
            if "narrative" in routes:
                unit.action, unit.reason, unit.compressible = COMPRESS, "prose", True
            else:
                _keep(plan, unit, "route_off")

    # passages: needs a question, enough passages and enough text to be worth the risk
    if plan.query and "passages" in routes and len(candidates) >= settings.min_passages:
        if sum(count_tokens(u.text) for u in candidates) >= settings.min_passage_tokens:
            for unit in candidates:
                if unit.reason == "exact":     # counted as kept above; now it is a passage candidate instead
                    plan.reasons["exact"] -= 1
                    if not plan.reasons["exact"]:
                        del plan.reasons["exact"]
                unit.selectable = True
                unit.action, unit.reason = SELECT, "passage"
                plan.passages.append(unit)
    return plan


def _keep(plan: Plan, unit: Unit, reason: str) -> None:
    unit.action, unit.reason = KEEP, reason
    plan.reasons[reason] = plan.reasons.get(reason, 0) + 1


def plan_history(messages: list, message_units: dict, settings: PipelineSettings,
                 message_tokens: Callable[[dict], int], keep: frozenset = frozenset()) -> list:
    """Indexes of the oldest whole turns to drop (route "history"); [] when the route is off or under budget.

    A turn that contains sensitive text is never dropped: losing "I am allergic to penicillin" from the history is
    worse than keeping the tokens. Neither is a turn holding a message index in `keep` (the context-engineering
    stage's compaction summary)."""
    if "history" not in settings.routes or settings.history_max_tokens <= 0:
        return []

    def protected(index: int) -> bool:
        return index in keep or any(unit.sensitive for unit in message_units.get(index, ()))

    dropped, _ = trim_history(
        messages, settings.history_max_tokens, settings.history_keep_messages, message_tokens, protected=protected
    )
    return dropped
