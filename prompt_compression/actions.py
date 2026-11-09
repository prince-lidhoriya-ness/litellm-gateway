"""Actions: carry out the router's plan.

    keep      nothing happens (the unit's text is left as it is; sensitive spans can be redacted, REDACT_SENSITIVE)
    select    whole units are dropped: passages the question does not need, log or JSON lines it does not name
    compress  consecutive prose units are merged into one run and sent to LLMLingua-2, capped at settings.max_ratio

Select runs before compress, so a dropped passage never reaches the compressor. Every counter is per message, because
the pipeline reports per message.
"""

import time
from dataclasses import dataclass, field
from typing import Callable

from prompt_compression import deadline as deadlines
from prompt_compression import rules
from prompt_compression.router import Plan
from prompt_compression.segmenter import label_split
from prompt_compression.selectors import drop_trailing_comma, select_passages, select_records
from prompt_compression.settings import PipelineSettings

COUNTERS = ("passages_dropped", "record_lines_dropped", "compress_calls", "compressed_blocks", "ratio_cap_hits", "redactions",
            "compress_cache_hits")


@dataclass
class Outcome:
    stats: dict = field(default_factory=dict)         # message index -> counters
    acted: dict = field(default_factory=dict)         # message index -> action names, in order
    compress_ms: dict = field(default_factory=dict)   # message index -> milliseconds spent in LLMLingua-2
    # Why compression stopped before every run was tried: "request_budget" (max_compress_calls_per_request) or
    # "deadline" (the pipeline's deadline passed); None when every run was tried.
    compress_stopped: str = None
    compress_calls: int = 0                            # model calls in the whole request (cache hits excluded)

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
    """Compress runs longest first over the whole request, within the per-message and per-request call budgets and the
    request's deadline. Stopping early is not an error: the remaining runs are sent as they are."""
    runs = [(message, run) for message, run in _runs(plan) if len(_run_text(run)) >= settings.min_chars]
    runs.sort(key=lambda item: -len(_run_text(item[1])))          # the longest runs first: most to gain per call
    deadline = deadlines.current()
    spent: dict = {}
    for message, run in runs:
        counters = outcome.counters(message)
        if counters["compress_calls"] >= settings.max_compress_calls:
            continue
        if settings.max_compress_calls_per_request > 0 and outcome.compress_calls >= settings.max_compress_calls_per_request:
            outcome.compress_stopped = "request_budget"
            break
        if deadline.expired():
            outcome.compress_stopped = "deadline"
            break
        started = time.perf_counter()
        try:
            text = _compress_with_cap(_run_text(run), settings, compressor, counters, outcome)
        except deadlines.DeadlineExceeded:
            outcome.compress_stopped = "deadline"
            break
        finally:
            spent[message] = spent.get(message, 0.0) + (time.perf_counter() - started) * 1000
        if text is None:
            continue
        tail_sep = run[-1].sep
        run[0].text, run[0].sep = text, tail_sep
        for unit in run[1:]:
            unit.dropped = True
        counters["compressed_blocks"] += 1
        outcome.note(message, "compressed")
    for message, milliseconds in spent.items():
        outcome.compress_ms[message] = round(milliseconds, 1)


def _call(text: str, rate: float, compressor, counters: dict, outcome: Outcome):
    output = compressor.compress(text, rate)
    if getattr(output, "cached", False):
        counters["compress_cache_hits"] += 1
    else:
        counters["compress_calls"] += 1
        outcome.compress_calls += 1
    return output


def _compress_with_cap(text: str, settings: PipelineSettings, compressor, counters: dict, outcome: Outcome):
    cap = settings.max_ratio
    output = _call(text, settings.rate, compressor, counters, outcome)
    ratio = output.origin_tokens / max(output.compressed_tokens, 1)
    if ratio > cap and settings.rate < 1.0:
        lighter = min(1.0, settings.rate * ratio / cap)
        output = _call(text, lighter, compressor, counters, outcome)
        ratio = output.origin_tokens / max(output.compressed_tokens, 1)
        if ratio > cap * 1.05:
            counters["ratio_cap_hits"] += 1
            return None
    if not output.text.strip() or output.compressed_tokens >= output.origin_tokens:
        return None
    return output.text
