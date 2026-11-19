"""Router: the task type picks the action for every unit. It only decides; actions.py does the work.

Inputs are the units that "Segment and classify" produced (what kind of text, sensitive or not) and the request
context (the question, which message is the latest user message). Output is a Plan:

    keep      code, structured data, identifier-dense text, sensitive text, the instruction and the question
    fold      log blocks: runs of near-identical lines become one marker line (logfold.py), whatever the question
    select    whole units that the task does not need can be dropped: old chat turns, passages, log lines
    compress  running prose goes to LLMLingua-2

Evidence for each rule is in reports/compression-fit/REPORT.md, sections 4 and 7.

Three limits on "select" (PROJECT_AUDIT_REPORT.md, F-06 and F-07; production-readiness STRATEGY.md, M3 and §3.1):
  scope     with selection_scope "latest_user" (default) only units of the latest user message may be selected; earlier
            turns are history and are never re-selected against a new question
  intent    only a positive "lookup" selects (intent.py); "diagnose" and "transform", the default, select nothing
  pressure  when the context-engineering stage reports a pressure below settings.selection_min_pressure, nothing is
            selected: lossy selection exists to make a request fit, not to save

"fold" does not read the question, so it applies to every eligible message, not only the latest one: the same log
gives the same bytes on every request.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

from prompt_compression.intent import LOOKUP
from prompt_compression.segmenter import CODE, EXACT, PROSE, STRUCTURED
from prompt_compression.unit_selectors import trim_history
from prompt_compression.settings import PRESSURE_LEVELS, PipelineSettings
from prompt_compression.units import COMPRESS, FOLD, KEEP, SELECT, Unit

RECORD_SUBTYPES = ("log", "jsonl", "csv", "tsv", "table", "json")


@dataclass
class Plan:
    units: list
    query: Optional[str] = None
    passages: list = field(default_factory=list)    # units a passage selection may drop
    records: list = field(default_factory=list)     # structured blocks a record selection may thin out
    folds: list = field(default_factory=list)       # log blocks whose repeated lines may be folded
    select_if_unfolded: list = field(default_factory=list)   # folds that fall back to record selection if none applies
    # Text the fidelity guard checks removals against: the verbatim parts of the latest user message, the system prompt
    # and the last two assistant turns (pipeline.py fills it in after routing). Empty: nothing counts as referenced.
    reference: str = ""
    passage_total: int = 0                          # passage candidates, for the omission marker ("3 of 12")
    reasons: dict = field(default_factory=dict)     # reason -> number of units kept verbatim for it
    intent: str = LOOKUP


def selection_permitted(settings: PipelineSettings, intent: str, pressure: Optional[str] = None) -> bool:
    """May passage or record selection run on this request at all? (intent gate and pressure gate)"""
    if settings.intent_gate and intent != LOOKUP:
        return False
    if pressure in PRESSURE_LEVELS and settings.selection_min_pressure in PRESSURE_LEVELS:
        return PRESSURE_LEVELS.index(pressure) >= PRESSURE_LEVELS.index(settings.selection_min_pressure)
    return True


def route(units: list, settings: PipelineSettings, query: Optional[str], last_user_index: Optional[int],
          count_tokens: Callable[[str], int], intent: str = LOOKUP, pressure: Optional[str] = None) -> Plan:
    plan = Plan(units=units, query=(query or "").strip() or None, intent=intent)
    routes = settings.routes
    selection_allowed = selection_permitted(settings, intent, pressure)

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
            record_selectable = (plan.query and "records" in routes and unit.subtype in RECORD_SUBTYPES
                                 and selectable(unit))
            if "logfold" in routes and unit.subtype == "log":
                # Folding first: lossless in intent and question-independent. Record selection is the second step and
                # runs only on a log that has nothing to fold (STRATEGY.md, C1.2).
                unit.action, unit.reason = FOLD, "logfold"
                plan.folds.append(unit)
                if record_selectable:
                    plan.select_if_unfolded.append(unit)
            elif record_selectable:
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
            plan.passage_total = len(plan.passages)
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
