"""Actions: carry out the router's plan.

    keep      nothing happens (the unit's text is left as it is; sensitive spans can be redacted, REDACT_SENSITIVE)
    select    whole units are dropped: passages the question does not need, log or JSON lines it does not name
    compress  consecutive prose units are merged into one run and sent to LLMLingua-2, capped at settings.max_ratio

Select runs before compress, so a dropped passage never reaches the compressor. Every counter is per message, because
the pipeline reports per message.
"""

import dataclasses
import time
from dataclasses import dataclass, field
from typing import Callable

from prompt_compression import rules
from prompt_compression.router import Plan
from prompt_compression.segmenter import label_split
from prompt_compression.selectors import drop_trailing_comma, select_passages, select_records
from prompt_compression.settings import PipelineSettings

COUNTERS = ("passages_dropped", "record_lines_dropped", "compress_calls", "compressed_blocks", "ratio_cap_hits", "redactions")


@dataclass
class Outcome:
    stats: dict = field(default_factory=dict)         # message index -> counters
    acted: dict = field(default_factory=dict)         # message index -> action names, in order
    compress_ms: dict = field(default_factory=dict)   # message index -> milliseconds spent in LLMLingua-2

    def counters(self, message: int) -> dict:
        return self.stats.setdefault(message, {name: 0 for name in COUNTERS})

    def note(self, message: int, action: str) -> None:
        names = self.acted.setdefault(message, [])
        if action not in names:
            names.append(action)


def execute(plan: Plan, settings: PipelineSettings, compressor, count_tokens: Callable[[str], int]) -> Outcome:
    outcome = Outcome()
    if settings.redact_sensitive:
        _redact(plan, outcome)
    _select_records(plan, settings, outcome)
    _select_passages(plan, settings, count_tokens, outcome)
    _compress(plan, settings, compressor, outcome)
    return outcome


# ---- keep (with optional redaction) ------------------------------------------------------------------------------

def _redact(plan: Plan, outcome: Outcome) -> None:
    for unit in plan.units:
        if unit.sensitive and unit.rule_hits:
            text, _, count = rules.redact_with_count(unit.text)
            if count:
                unit.text = text
                outcome.counters(unit.message)["redactions"] += count
                outcome.note(unit.message, "redacted")


# ---- select or drop ----------------------------------------------------------------------------------------------

def _one_object_per_line(lines: list) -> bool:
    body = [line for line in lines if line.strip() not in ("[", "]", "{", "}", "")]
    return bool(body) and sum(1 for line in body if line.strip().startswith("{")) >= 0.8 * len(body)


def _select_records(plan: Plan, settings: PipelineSettings, outcome: Outcome) -> None:
    for unit in plan.records:
        head, body = label_split(unit.text)      # a label line above the data ("Here is the log:") stays as it is
        lines = body.split("\n")
        if len(lines) < settings.record_min_lines:
            continue
        if unit.subtype == "json" and not _one_object_per_line(lines):
            continue
        flags = select_records(lines, plan.query, unit.subtype, settings.record_context_lines)
        if flags is None:
            continue
        kept = [line for line, keep in zip(lines, flags) if keep]
        if unit.subtype == "json":
            kept = drop_trailing_comma(kept)
        outcome.counters(unit.message)["record_lines_dropped"] += len(lines) - len(kept)
        unit.text = head + "\n".join(kept)
        outcome.note(unit.message, "selected_records")


def _select_passages(plan: Plan, settings: PipelineSettings, count_tokens, outcome: Outcome) -> None:
    if not plan.passages:
        return
    flags = select_passages([u.text for u in plan.passages], plan.query, settings.passage_keep_ratio, count_tokens)
    if flags is None:                                   # no lexical signal: drop nothing
        return
    for unit, keep in zip(plan.passages, flags):
        if not keep:
            unit.dropped = True
            outcome.counters(unit.message)["passages_dropped"] += 1
            outcome.note(unit.message, "selected_passages")


# ---- compress ----------------------------------------------------------------------------------------------------

def _runs(plan: Plan) -> list:
    """(message, [units]) for every run of consecutive compressible prose units inside one message part."""
    runs, current, key = [], [], None

    def flush():
        if current:
            runs.append((current[0].message, list(current)))
            current.clear()

    for unit in plan.units:
        unit_key = (unit.message, unit.part)
        if unit_key != key:
            flush()
            key = unit_key
        if unit.dropped:
            continue
        if unit.compressible and unit.filled and not unit.sensitive:
            current.append(unit)
        else:
            flush()
    flush()
    return runs


def _run_text(run: list) -> str:
    return "".join(u.full for u in run[:-1]) + run[-1].text


def _compress(plan: Plan, settings: PipelineSettings, compressor, outcome: Outcome) -> None:
    by_message: dict = {}
    for message, run in _runs(plan):
        if len(_run_text(run)) >= settings.min_chars:
            by_message.setdefault(message, []).append(run)
    for message, runs in by_message.items():
        runs.sort(key=lambda run: -len(_run_text(run)))          # the longest runs first: most to gain per call
        counters = outcome.counters(message)
        spent = 0.0
        for run in runs:
            if counters["compress_calls"] >= settings.max_compress_calls:
                break
            started = time.perf_counter()
            text = _compress_with_cap(_run_text(run), settings, compressor, counters)
            spent += (time.perf_counter() - started) * 1000
            if text is None:
                continue
            tail_sep = run[-1].sep
            run[0].text, run[0].sep = text, tail_sep
            for unit in run[1:]:
                unit.dropped = True
            counters["compressed_blocks"] += 1
            outcome.note(message, "compressed")
        outcome.compress_ms[message] = round(spent, 1)


def _compress_with_cap(text: str, settings: PipelineSettings, compressor, counters: dict):
    cap = settings.max_ratio
    counters["compress_calls"] += 1
    output = compressor.compress(text, settings.rate)
    ratio = output.origin_tokens / max(output.compressed_tokens, 1)
    if ratio > cap and settings.rate < 1.0:
        lighter = min(1.0, settings.rate * ratio / cap)
        counters["compress_calls"] += 1
        output = compressor.compress(text, lighter)
        ratio = output.origin_tokens / max(output.compressed_tokens, 1)
        if ratio > cap * 1.05:
            counters["ratio_cap_hits"] += 1
            return None
    if not output.text.strip() or output.compressed_tokens >= output.origin_tokens:
        return None
    return output.text
