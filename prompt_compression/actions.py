"""Actions: carry out the router's plan.

    keep      nothing happens (the unit's text is left as it is; sensitive spans can be redacted, REDACT_SENSITIVE)
    fold      runs of near-identical log lines become one marker line each (logfold.py); question-independent
    select    whole units are dropped: passages the question does not need, log or JSON lines it does not name
    compress  consecutive prose units are merged into one run and sent to LLMLingua-2, capped at settings.max_ratio

Order: fold (lossless in intent) and selection run before compress, so a dropped passage never reaches the compressor.

Every lossy removal is visible to the model and to operations (reports/production-readiness-audit/STRATEGY.md, C1.3
and invariant 17): a dropped span of log lines or passages is replaced by one gateway marker line, and each action
counts what it did. After each action the fidelity guard (fidelity.py) checks the changed unit: a must-survive string
of the removed text that the conversation references (the question, the system prompt, the last assistant turns) and
that the output lost makes the action retry lighter (compress, once, at rate + 0.25) or undo itself for that unit only.
Compression is identifier-safe (STRATEGY.md, H3): identifier spans are cut out of a run before LLMLingua-2 sees it and
re-joined byte for byte, and a run whose output does not contain every identifier of its input byte for byte is sent
as it was.

Every counter is per message, because the pipeline reports per message.
"""

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from prompt_compression import deadline as deadlines
from prompt_compression import fidelity, logfold, rules
from prompt_compression.fidelity import Tally
from prompt_compression.router import Plan
from prompt_compression.segmenter import label_split
from prompt_compression.settings import PipelineSettings
from prompt_compression.texts import count_tokens as _count_tokens
from prompt_compression.unit_selectors import drop_trailing_comma, select_passages, select_records_detailed

COUNTERS = ("passages_dropped", "record_lines_dropped", "compress_calls", "compressed_blocks", "ratio_cap_hits", "redactions",
            "compress_cache_hits", "log_lines_folded", "omission_markers", "fidelity_reverts")

MARKER = "[gateway: "
# Text between two identifier spans shorter than this is kept verbatim: too little prose for a model call to help.
_MIN_GAP_CHARS = 40
# The lighter retry after a fidelity failure keeps this much more of the tokens (STRATEGY.md, H4).
_FIDELITY_RETRY_STEP = 0.25
_LABEL_WORDS = 8
_LABEL_CHARS = 60
_MARKER_LABELS = 3


@dataclass
class Outcome:
    stats: dict = field(default_factory=dict)         # message index -> counters
    acted: dict = field(default_factory=dict)         # message index -> action names, in order
    compress_ms: dict = field(default_factory=dict)   # message index -> milliseconds spent in LLMLingua-2
    # Why compression stopped before every run was tried: "request_budget" (max_compress_calls_per_request) or
    # "deadline" (the pipeline's deadline passed); None when every run was tried.
    compress_stopped: str = None
    compress_calls: int = 0                            # model calls in the whole request (cache hits excluded)
    fidelity: Tally = field(default_factory=Tally)

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
    _fold_logs(plan, count_tokens, outcome)
    _select_records(plan, settings, count_tokens, outcome)
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


# ---- fold (lossless in intent, question-independent) ---------------------------------------------------------------

def _fold_logs(plan: Plan, count_tokens, outcome: Outcome) -> None:
    fallback = {id(unit) for unit in plan.select_if_unfolded}
    for unit in plan.folds:
        head, body = label_split(unit.text)
        lines = body.split("\n")
        folds = logfold.plan_folds(lines, count_tokens)
        if not folds:
            if id(unit) in fallback:            # nothing repeats: record selection may run (opt-in, lookup, pressure)
                unit.action, unit.reason = "select", "records"
                plan.records.append(unit)
            continue
        kept = []
        for fold in folds:
            removed = "\n".join(lines[fold.first:fold.last + 1])
            outcome.fidelity.add("logfold", "checked")
            # Folded lines never include a severity line (logfold.py), so only referenced strings can fail here: a
            # question that names a value inside a folded run keeps that run.
            remaining = "\n".join(lines[:fold.first] + lines[fold.last + 1:])
            lost = fidelity.missing_referenced(removed, remaining, plan.reference)
            if lost:
                outcome.fidelity.add("logfold", "reverted", "referenced")
                outcome.counters(unit.message)["fidelity_reverts"] += 1
                continue
            kept.append(fold)
        if not kept:
            continue
        counters = outcome.counters(unit.message)
        counters["log_lines_folded"] += sum(fold.count for fold in kept)
        counters["omission_markers"] += len(kept)
        unit.text = head + "\n".join(logfold.apply(lines, kept))
        outcome.note(unit.message, "folded_logs")


# ---- select or drop ----------------------------------------------------------------------------------------------

def _one_object_per_line(lines: list) -> bool:
    body = [line for line in lines if line.strip() not in ("[", "]", "{", "}", "")]
    return bool(body) and sum(1 for line in body if line.strip().startswith("{")) >= 0.8 * len(body)


def _policy(selection) -> str:
    parts = []
    if selection.matched:
        parts.append("lines matching " + ", ".join(selection.matched))
    if selection.severity_lines:
        parts.append("all error/warning lines with their neighbours")
    if selection.correlated:
        parts.append("lines sharing " + ", ".join(selection.correlated[:5]) + (" ..." if len(selection.correlated) > 5 else ""))
    if selection.time_window_s:
        parts.append(f"lines within {selection.time_window_s:g} s of a match")
    return "; ".join(parts) or "lines the question names"


def _spans(flags: list) -> list:
    """(first, last) 0-based index pairs of consecutive dropped lines."""
    spans, start = [], None
    for index, keep in enumerate(flags + [True]):
        if not keep and start is None:
            start = index
        elif keep and start is not None:
            spans.append((start, index - 1))
            start = None
    return spans


def _records_with_markers(lines: list, flags: list, subtype: str, selection, count_tokens) -> tuple[str, int]:
    """The kept lines with the omission markers, and the number of markers. A log gets one marker line in place of
    each dropped span (the first names the selection policy); JSON, JSON lines and tables get one marker line above
    the block, so the data itself stays parseable."""
    spans = _spans(flags)
    total = len(lines)
    dropped = sum(last - first + 1 for first, last in spans)
    tail = "Ask the user for the full data if the answer is not here.]"
    if subtype != "log":
        kept = [line for line, keep in zip(lines, flags) if keep]
        if subtype == "json":
            kept = drop_trailing_comma(kept)
        tokens = count_tokens("\n".join(line for line, keep in zip(lines, flags) if not keep))
        summary = (f"{MARKER}{dropped} of {total} lines omitted ({tokens} tokens); kept: {_policy(selection)}. {tail}")
        return summary + "\n" + "\n".join(kept), 1
    out, position = [], 0
    for number, (first, last) in enumerate(spans):
        out.extend(line for line, keep in zip(lines[position:first], flags[position:first]) if keep)
        removed = "\n".join(lines[first:last + 1])
        lines_label = f"line {first + 1}" if first == last else f"lines {first + 1}-{last + 1}"
        if number == 0:
            out.append(f"{MARKER}{lines_label} omitted ({last - first + 1} lines, {count_tokens(removed)} tokens); "
                       f"kept: {_policy(selection)}. {tail}")
        else:
            out.append(f"{MARKER}{lines_label} omitted ({last - first + 1} lines)]")
        position = last + 1
    out.extend(line for line, keep in zip(lines[position:], flags[position:]) if keep)
    return "\n".join(out), len(spans)


def _select_records(plan: Plan, settings: PipelineSettings, count_tokens, outcome: Outcome) -> None:
    for unit in plan.records:
        head, body = label_split(unit.text)      # a label line above the data ("Here is the log:") stays as it is
        lines = body.split("\n")
        if len(lines) < settings.record_min_lines:
            continue
        if unit.subtype == "json" and not _one_object_per_line(lines):
            continue
        selection = select_records_detailed(
            lines, plan.query, unit.subtype, settings.record_context_lines,
            severity_context=settings.record_severity_context, correlate=settings.record_correlate,
            time_window_s=settings.record_time_window_s,
        )
        if selection is None or all(selection.flags):
            continue
        flags = selection.flags
        removed = "\n".join(line for line, keep in zip(lines, flags) if not keep)
        kept_text = "\n".join(line for line, keep in zip(lines, flags) if keep)
        outcome.fidelity.add("records", "checked")
        reason = None
        if fidelity.severity_lines(removed):
            reason = "severity"                      # the selector keeps every severity line; a backstop
        elif fidelity.missing_referenced(removed, kept_text, plan.reference):
            reason = "referenced"
        if reason:
            outcome.fidelity.add("records", "reverted", reason)
            outcome.counters(unit.message)["fidelity_reverts"] += 1
            continue
        text, markers = _records_with_markers(lines, flags, unit.subtype, selection, count_tokens)
        counters = outcome.counters(unit.message)
        counters["record_lines_dropped"] += len(lines) - sum(flags)
        counters["omission_markers"] += markers
        unit.text = head + text
        unit.marker = True
        outcome.note(unit.message, "selected_records")


def _passage_label(text: str) -> str:
    """The first heading or the first words of a passage: what its omission marker names it by."""
    first = text.strip().split("\n", 1)[0].strip().lstrip("#").strip()
    if first and len(first) <= _LABEL_CHARS and not first.endswith((".", "!", "?")):
        return first
    words = text.split()
    label = " ".join(words[:_LABEL_WORDS])
    label = label[:_LABEL_CHARS]
    return label + (" ..." if len(words) > _LABEL_WORDS or len(label) == _LABEL_CHARS else "")


def _select_passages(plan: Plan, settings: PipelineSettings, count_tokens, outcome: Outcome) -> None:
    if not plan.passages:
        return
    flags = select_passages([u.text for u in plan.passages], plan.query, settings.passage_keep_ratio, count_tokens,
                            require_identifier=settings.intent_gate)
    if flags is None:                                   # no lexical signal: drop nothing
        return
    kept_text = "\n".join(u.text for u, keep in zip(plan.passages, flags) if keep)
    for position, (unit, keep) in enumerate(zip(plan.passages, flags)):
        if keep:
            continue
        outcome.fidelity.add("passages", "checked")
        if fidelity.missing_referenced(unit.text, kept_text, plan.reference):
            outcome.fidelity.add("passages", "reverted", "referenced")
            outcome.counters(unit.message)["fidelity_reverts"] += 1
            flags[position] = True
            continue
        unit.dropped = True
        outcome.counters(unit.message)["passages_dropped"] += 1
        outcome.note(unit.message, "selected_passages")
    _mark_dropped_passages(plan, outcome)


def _mark_dropped_passages(plan: Plan, outcome: Outcome) -> None:
    """One marker per run of consecutive dropped passages, in place of the first one: the model sees where text was
    taken out and what it was about, instead of a document that silently reads as complete."""
    selected = {id(unit) for unit in plan.passages}
    total = plan.passage_total or len(plan.passages)
    run: list = []

    def flush() -> None:
        if not run:
            return
        labels = ", ".join(f"\"{_passage_label(u.text)}\"" for u in run[:_MARKER_LABELS])
        more = f" and {len(run) - _MARKER_LABELS} more" if len(run) > _MARKER_LABELS else ""
        noun = "passage" if len(run) == 1 else "passages"
        first = run[0]
        first.text = (f"{MARKER}{len(run)} of {total} {noun} omitted here: {labels}{more}. "
                      f"Ask the user for them if the answer is not here.]")
        first.dropped, first.marker, first.compressible = False, True, False
        outcome.counters(first.message)["omission_markers"] += 1
        run.clear()

    key = None
    for unit in plan.units:
        unit_key = (unit.message, unit.part)
        if unit_key != key:
            flush()
            key = unit_key
        if id(unit) in selected and unit.dropped:
            run.append(unit)
        elif unit.filled or id(unit) in selected:
            flush()
    flush()


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
        if unit.compressible and unit.filled and not unit.sensitive and not unit.marker:
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
            text = _compress_guarded(_run_text(run), settings, compressor, counters, outcome, plan.reference)
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


def _compress_guarded(original: str, settings: PipelineSettings, compressor, counters: dict, outcome: Outcome,
                      reference: str) -> Optional[str]:
    """Compressed text for one run, or None to send the run as it was (capped, identifier-checked, fidelity-checked)."""
    text = _compress_with_cap(original, settings.rate, settings, compressor, counters, outcome)
    if text is None:
        return None
    outcome.fidelity.add("compress", "checked")
    if fidelity.missing_identifiers(original, text):
        outcome.fidelity.add("compress", "reverted", "identifier")
        counters["fidelity_reverts"] += 1
        return None
    if not fidelity.missing_referenced(original, text, reference):
        return text
    lighter = min(1.0, settings.rate + _FIDELITY_RETRY_STEP)
    if lighter < 1.0:
        outcome.fidelity.add("compress", "retried")
        text = _compress_with_cap(original, lighter, settings, compressor, counters, outcome)
        if (text is not None and not fidelity.missing_identifiers(original, text)
                and not fidelity.missing_referenced(original, text, reference)):
            return text
    outcome.fidelity.add("compress", "reverted", "referenced")
    counters["fidelity_reverts"] += 1
    return None


def _call_pieces(pieces: list, rate: float, compressor, counters: dict, outcome: Outcome) -> list:
    """Compressed text per piece. One model call for the whole list when the compressor batches (the LLMLingua-2
    adapter does); otherwise one call per piece, counted as one call for the run."""
    compress_many = getattr(compressor, "compress_many", None)
    if compress_many is not None:
        outputs, calls = compress_many(pieces, rate)
    else:
        outputs = [compressor.compress(piece, rate) for piece in pieces]
        calls = 0 if all(getattr(output, "cached", False) for output in outputs) else 1
    if calls:
        counters["compress_calls"] += 1
        outcome.compress_calls += 1
    else:
        counters["compress_cache_hits"] += 1
    return [output.text for output in outputs]


def _safe_compress(text: str, rate: float, compressor, counters: dict, outcome: Outcome) -> Optional[str]:
    """The run with its prose gaps compressed and its identifier spans untouched; None when there is no prose gap
    long enough to compress."""
    pieces = fidelity.split_protected(text)
    gaps = [index for index, (protected, piece) in enumerate(pieces)
            if not protected and len(piece.strip()) >= _MIN_GAP_CHARS]
    if not gaps:
        return None
    cores = [pieces[index][1].strip() for index in gaps]
    compressed = _call_pieces(cores, rate, compressor, counters, outcome)
    out = [piece for _, piece in pieces]
    for index, core in zip(gaps, compressed):
        piece = pieces[index][1]
        lead = piece[:len(piece) - len(piece.lstrip())]
        trail = piece[len(piece.rstrip()):]
        core = (core or "").strip()
        if core:
            out[index] = lead + core + trail
        else:
            # Nothing left of the gap: one space between its neighbours if it had any whitespace, so two identifiers
            # never run together.
            out[index] = " " if (lead or trail or any(ch.isspace() for ch in piece)) else piece
    return "".join(out)


def _compress_with_cap(text: str, rate: float, settings: PipelineSettings, compressor, counters: dict,
                       outcome: Outcome) -> Optional[str]:
    cap = settings.max_ratio
    before = _count_tokens(text)
    output = _safe_compress(text, rate, compressor, counters, outcome)
    if output is None:
        return None
    ratio = before / max(_count_tokens(output), 1)
    if ratio > cap and rate < 1.0:
        lighter = min(1.0, rate * ratio / cap)
        output = _safe_compress(text, lighter, compressor, counters, outcome)
        if output is None:
            return None
        ratio = before / max(_count_tokens(output), 1)
        if ratio > cap * 1.05:
            counters["ratio_cap_hits"] += 1
            return None
    if not output.strip() or _count_tokens(output) >= before:
        return None
    return output
