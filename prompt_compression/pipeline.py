"""The pipeline, stage by stage, over an OpenAI-style messages list (the gate runs in the hook before this).

    1. Segment and classify   every eligible message is split into blocks (what kind of text: segmenter.py) and each
                              block is checked for sensitivity (sensitivity.py: rules, and the NLI model on prose)
    2. Router                 the task type picks an action per block: keep, select or drop, compress (router.py)
    3. Actions                keep does nothing; select drops whole units; compress calls LLMLingua-2 (actions.py)
    4. Reassemble             the blocks of each message are joined back in their original order

Never touched: system/developer messages, tool and function results, assistant messages that carry
tool_calls/function_call, non-text content parts (images, audio), and anything outside data["messages"] such as tool
definitions. Roles and order are kept; only the text of eligible messages changes, and the oldest whole turns can be
dropped when the "history" route is on. The report keeps original message indexes and adds "new_index" for the position
in the returned list.
"""

import copy
import logging
import time
from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import Optional

try:
    # Spans are no-ops unless the host process (e.g. the LiteLLM proxy with OTel) configures a provider.
    from opentelemetry import trace as _otel_trace

    _tracer = _otel_trace.get_tracer("prompt_compression")
except ImportError:  # OTel is optional for the pipeline itself
    _tracer = None

from prompt_compression import actions, router
from prompt_compression.compressor_adapter import LLMLinguaCompressor
from prompt_compression.segmenter import EXACT, PROSE, split_segments
from prompt_compression.sensitivity import GENERAL_CATEGORY, SENSITIVE_CATEGORY, SensitivityDetector, get_detector
from prompt_compression.settings import PipelineSettings
from prompt_compression.texts import all_text_tokens, count_tokens, message_tokens, set_text, text_parts
from prompt_compression.units import Unit

logger = logging.getLogger("prompt_compression.pipeline")

PRESERVED_ROLES = frozenset({"system", "developer", "tool", "function"})
# Prose runs shorter than this are not worth a model call: nothing could be done with them anyway.
_MIN_MODEL_CHARS = 40

# Kept under their old names: observability/observed_callback.py imports them from here.
_text_parts = text_parts


def _span(name: str, attributes: dict):
    """Child span of whatever span is current; never carries message text."""
    if _tracer is None:
        return nullcontext()
    return _tracer.start_as_current_span(name, attributes=attributes)


def _set_attributes(span, attributes: dict) -> None:
    if span is not None and hasattr(span, "set_attributes"):
        span.set_attributes(attributes)


@dataclass
class PipelineReport:
    request_category: Optional[str] = None
    classifier_model: str = ""
    compression_model: str = ""
    tokens_before: int = 0
    tokens_after: int = 0
    elapsed_ms: float = 0.0
    messages: list = field(default_factory=list)
    mode: str = "enforce"
    routes: list = field(default_factory=list)
    history_dropped: int = 0
    # Sum over all messages of the block counts ("code", "structured", "exact", "prose", "sensitive", ...).
    segments: dict = field(default_factory=dict)
    # Why blocks were kept verbatim: reason -> number of blocks ("code", "sensitive", "edge", ...).
    kept: dict = field(default_factory=dict)

    @property
    def ratio(self) -> float:
        return round(self.tokens_before / self.tokens_after, 3) if self.tokens_after else 1.0

    def as_metadata(self) -> dict:
        return {
            "category": self.request_category,
            "classifier_model": self.classifier_model,
            "compression_model": self.compression_model,
            "tokens_before": self.tokens_before,
            "tokens_after": self.tokens_after,
            "compression_ratio": self.ratio,
            "elapsed_ms": self.elapsed_ms,
            "mode": self.mode,
            "routes": list(self.routes),
            "history_dropped": self.history_dropped,
            "segments": dict(self.segments),
            "kept": dict(self.kept),
            "messages": self.messages,
        }


def _tail_paragraph(text: str, max_chars: int = 600) -> Optional[str]:
    """The last non-empty paragraph, if it is short enough to be a question or an instruction."""
    blocks = [segment.text for segment in split_segments(text) if segment.text.strip()]
    if not blocks:
        return None
    tail = blocks[-1].strip()
    return tail if len(tail) <= max_chars else None


class PromptPipeline:
    def __init__(
        self,
        settings: Optional[PipelineSettings] = None,
        detector: Optional[SensitivityDetector] = None,
        compressor: Optional[LLMLinguaCompressor] = None,
    ):
        self.settings = settings or PipelineSettings.from_env()
        self.detector = detector or get_detector()
        self.compressor = compressor or LLMLinguaCompressor(self.settings.compression_model)

    def load(self) -> None:
        self.detector.load()
        self.compressor.load()

    # ---- stage 1: segment and classify ----------------------------------------------------------------------------

    def _segment(self, index: int, parts: list) -> list:
        units = []
        for part_index, text in parts:
            for segment in split_segments(text, self.settings.exact_density):
                units.append(Unit(index, part_index, segment.kind, segment.subtype, segment.text, segment.sep))
        return units

    @staticmethod
    def _mark(unit: Unit, sensitivity) -> None:
        unit.sensitive = True
        unit.sensitive_source = sensitivity.source
        unit.rule_hits = tuple(sensitivity.rule_hits)

    def _check_many(self, texts: list) -> list:
        """One batched model call when the detector supports it (the embedding backend), else one call per text."""
        if not texts:
            return []
        check_many = getattr(self.detector, "check_many", None)
        return check_many(texts) if check_many else [self.detector.check(text) for text in texts]

    def _classify(self, units: list, use_model: bool, model_exempt: frozenset = frozenset()) -> dict:
        """Fill in Unit.sensitive and return the message-level summary of the checks.

        `model_exempt` holds id()s of units the router keeps verbatim whatever they contain (the instruction and the
        question of the latest user message): the rules and topics still check them, the model does not. Its opinion
        could not change what is sent, and on short lookup questions ("What was the user id of request req-1?") it
        was wrong 17 times in 40 log prompts, which only mislabelled the request (evals/REPORT.md, 4.2)."""
        info = {"score": 0.0, "source": "none", "classify_ms": 0.0, "chunks": 0, "cache_hit": False}
        checks = []
        for unit in units:
            if unit.filled:
                result = self.detector.rules_only(unit.text)
                if result.sensitive:
                    self._mark(unit, result)
        if use_model:
            # Exact-text blocks are only checked when a route could drop them whole (a passage, an old turn): kept
            # verbatim they are protected anyway, and the model's opinion would change nothing.
            selecting = bool(self.settings.routes & {"history", "passages"})
            kinds = (PROSE, EXACT) if selecting else (PROSE,)
            # When a route can drop whole passages or turns, each passage is judged on its own (short ones together
            # with their neighbour), so a borderline score protects that passage and not the whole document: scoring
            # the run in 200-token windows let one company-finance paragraph that fell into a short window keep a
            # whole document verbatim, and moving the window edges flipped the decision (evals/REPORT.md, 4.2).
            # With only the narrative route the run is compressed as a whole, so it is judged as a whole.
            groups = [g for run in _model_runs(units, kinds, model_exempt)
                      for g in (_passage_groups(run) if selecting else [run])]
            groups = [g for g in groups if len(_joined(g).strip()) >= _MIN_MODEL_CHARS]
            results = self._check_many([_joined(g) for g in groups])
            for group, result in zip(groups, results):
                checks.append(result)
                if result.sensitive:
                    for unit in group:
                        self._mark(unit, result)
        if checks:
            info["classify_ms"] = round(sum(c.elapsed_ms for c in checks if not c.cache_hit), 1)
            info["chunks"] = sum(c.chunks for c in checks)
            info["cache_hit"] = all(c.cache_hit for c in checks)
            info["score"] = max(c.score for c in checks)
            info["source"] = "model"
        sensitive_units = [u for u in units if u.sensitive]
        if any(u.sensitive_source == "rules" for u in sensitive_units):
            info["source"], info["score"] = "rules", 1.0
        elif any(u.sensitive_source == "error" for u in sensitive_units):
            info["source"], info["score"] = "error", 1.0
        info["rule_hits"] = sorted({hit for u in sensitive_units for hit in u.rule_hits})
        info["category"] = SENSITIVE_CATEGORY if sensitive_units else GENERAL_CATEGORY
        return info

    # ---- the whole request ----------------------------------------------------------------------------------------

    def process(self, messages: list) -> tuple[list, PipelineReport]:
        started = time.perf_counter()
        settings = self.settings
        new_messages = copy.deepcopy(messages)
        report = PipelineReport(
            classifier_model=self.detector.model_name,
            compression_model=self.compressor.model_name,
            mode=settings.mode,
            routes=sorted(settings.routes),
        )
        report.tokens_before = all_text_tokens(messages)

        last_user_index = max((i for i, m in enumerate(messages) if m.get("role") == "user"), default=None)
        query = None
        if last_user_index is not None:
            query = _tail_paragraph("\n".join(text for _, text in text_parts(messages[last_user_index])))

        # 1. Segment and classify
        entries: dict = {}
        message_units: dict = {}
        for index, message in enumerate(new_messages):
            role = message.get("role")
            entry = {"index": index, "role": role}
            entries[index] = entry
            if role in PRESERVED_ROLES or message.get("tool_calls") or message.get("function_call"):
                entry["action"] = "preserved_role"
                continue
            parts = text_parts(message)
            if not parts:
                entry["action"] = "no_text"
                continue
            units = self._segment(index, parts)
            skip_model = not settings.routes or (settings.preserve_last_user and index == last_user_index)
            exempt = frozenset()
            if settings.protect_edges and index == last_user_index:
                # The same units router.route() marks as edges: first and last filled unit of the latest user message.
                # Only when there is content between them: a one- or two-paragraph prompt is all edges, and the model
                # stays the only judge of its label.
                filled = [u for u in units if u.filled]
                if len(filled) >= 3:
                    exempt = frozenset(id(u) for u in filled[:1] + filled[-1:])
            with _span("prompt.classify", {"prompt.message.index": index, "prompt.message.role": role or ""}) as span:
                info = self._classify(units, use_model=not skip_model, model_exempt=exempt)
                _set_attributes(span, {
                    "prompt.classifier.label": info["category"],
                    "prompt.classifier.score": info["score"],
                    "prompt.classifier.source": info["source"],
                    "prompt.classifier.model": self.detector.model_name,
                    "prompt.classifier.rule_hits": info["rule_hits"],
                    "prompt.classifier.chunks": info["chunks"],
                    "prompt.classifier.cache_hit": info["cache_hit"],
                })
            entry.update({
                "category": info["category"], "score": round(info["score"], 4), "source": info["source"],
                "rule_hits": info["rule_hits"], "classify_ms": info["classify_ms"], "chunks": info["chunks"],
                "cache_hit": info["cache_hit"],
            })
            message_units[index] = units

        # 2. Router
        with _span("prompt.route", {"prompt.route.routes": sorted(settings.routes)}) as span:
            dropped = set(router.plan_history(new_messages, message_units, settings, message_tokens))
            for index in sorted(dropped):
                entries[index] = {"index": index, "role": new_messages[index].get("role"), "action": "dropped_history",
                                  "tokens_before": message_tokens(messages[index]), "tokens_after": 0}
                message_units.pop(index, None)
            report.history_dropped = len(dropped)
            units = [unit for index in sorted(message_units) for unit in message_units[index]]
            plan = router.route(units, settings, query, last_user_index, count_tokens)
            _set_attributes(span, {
                "prompt.route.units": len(units), "prompt.route.history_dropped": len(dropped),
                **{f"prompt.route.kept.{reason}": number for reason, number in plan.reasons.items()},
            })
        report.kept = dict(plan.reasons)

        # 3. Actions
        with _span("prompt.compress", {"prompt.route.rate": settings.rate}) as span:
            before = sum(count_tokens(unit.full) for unit in units)
            outcome = actions.execute(plan, settings, self.compressor, count_tokens)
            after = sum(count_tokens(unit.full) for unit in units if not unit.dropped)
            _set_attributes(span, {"prompt.tokens.before": before, "prompt.tokens.after": after})

        # 4. Reassemble
        new_index = {}
        for original_index in range(len(new_messages)):
            if original_index not in dropped:
                new_index[original_index] = len(new_index)
        for index, message_unit_list in message_units.items():
            message = new_messages[index]
            by_part: dict = {}
            for unit in message_unit_list:
                if not unit.dropped:
                    by_part.setdefault(unit.part, []).append(unit.full)
            for part_index, original_text in text_parts(message):
                joined = "".join(by_part.get(part_index, []))
                if joined != original_text and joined.strip():
                    set_text(message, part_index, joined)
            self._finish_entry(entries[index], index, message, messages[index], message_unit_list, outcome, report)
        for index, entry in entries.items():
            if index in new_index:
                entry["new_index"] = new_index[index]

        report.messages = [entries[index] for index in sorted(entries)]
        new_messages = [message for index, message in enumerate(new_messages) if index not in dropped]
        categories = [e["category"] for e in report.messages if "category" in e]
        report.request_category = (
            SENSITIVE_CATEGORY if SENSITIVE_CATEGORY in categories else GENERAL_CATEGORY if categories else None
        )
        report.tokens_after = all_text_tokens(new_messages)
        report.elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        return new_messages, report

    def _finish_entry(self, entry: dict, index: int, message: dict, original: dict, units: list,
                      outcome: actions.Outcome, report: PipelineReport) -> None:
        filled = [u for u in units if u.filled]
        counters = outcome.stats.get(index, {})
        names = list(outcome.acted.get(index, []))
        original_tokens = message_tokens(original)
        text_length = sum(len(text) for _, text in text_parts(original))
        if names:
            action = "+".join(names)
        elif filled and all(u.reason == "last_user" for u in filled):
            action = "preserved_last_user"
        elif any(u.sensitive for u in filled):
            action = "sensitive"
        elif any(u.reason in ("code", "structured", "exact", "edge") for u in filled):
            action = "guarded"
        elif text_length < self.settings.min_chars:
            action = "below_min_chars"
        else:
            action = "unchanged"
        segments = {
            "blocks": len(filled),
            "code": sum(1 for u in filled if u.kind == "code"),
            "structured": sum(1 for u in filled if u.kind == "structured"),
            "exact": sum(1 for u in filled if u.kind == "exact"),
            "prose": sum(1 for u in filled if u.kind == PROSE),
            "sensitive": sum(1 for u in filled if u.sensitive),
            "edge_protected": sum(1 for u in filled if u.edge),
            **{name: counters.get(name, 0) for name in actions.COUNTERS},
        }
        entry.update({
            "redactions": counters.get("redactions", 0),
            "compress_ms": outcome.compress_ms.get(index, 0.0),
            "tokens_before": original_tokens,
            "tokens_after": message_tokens(message),
            "action": action,
            "segments": segments,
        })
        for key, value in segments.items():
            report.segments[key] = report.segments.get(key, 0) + value


def _joined(units: list) -> str:
    return "".join(u.full for u in units[:-1]) + units[-1].text


def _passage_groups(run: list) -> list:
    """Split a run into passages judged one by one: each unit alone, except that units shorter than _MIN_MODEL_CHARS
    are joined to the next one (or, at the end of the run, to the previous group), so no short sentence is judged
    without context or skipped."""
    groups, current = [], []
    for unit in run:
        current.append(unit)
        if len(_joined(current).strip()) >= _MIN_MODEL_CHARS:
            groups.append(current)
            current = []
    if current:
        if groups:
            groups[-1].extend(current)
        else:
            groups.append(current)
    return groups


def _model_runs(units: list, kinds: tuple, exempt: frozenset = frozenset()) -> list:
    """Runs of consecutive units of the given kinds inside one message part: the text the model is asked about.
    Units whose id() is in `exempt` are left out and split the run."""
    runs, current = [], []
    for unit in units:
        eligible = unit.kind in kinds and unit.filled and not unit.sensitive and id(unit) not in exempt
        if eligible and (not current or unit.part == current[-1].part):
            current.append(unit)
            continue
        if current:
            runs.append(current)
        current = [unit] if eligible else []
    if current:
        runs.append(current)
    return runs
