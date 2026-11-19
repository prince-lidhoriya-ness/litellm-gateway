"""Fidelity guard: what a lossy step must not lose, and the check that undoes it per unit when it did.

Shared by every lossy action of the compression stage (actions.py: record and passage selection, log folding, LLMLingua-2
compression) and written without dependencies on either stage, so the context-engineering stage can use it as well
(reports/production-readiness-audit/STRATEGY.md, H4).

For every unit a lossy action changed, the guard computes the must-survive strings of the text it removed:

    identifiers      ticket ids, versions, ISO dates, section numbers, UPPER_SNAKE / snake_case / kebab-case / camelCase
                     names, paths, urls, key=value pairs (IDENTIFIER below)
    numbers + units  "30000ms", "256Mi", "129.90 USD", "$129.90", "15 %" (NUMBER_WITH_UNIT)
    severity lines   ERROR / FATAL / Exception / Traceback / exit code != 0 ... (SEVERITY, the same pattern as
                     context_engineering/extract.py, so both stages agree on what an error line is)

A must-survive string is *referenced* when it also appears in the reference text: the latest user message's verbatim
parts, the system prompt and the last two assistant turns. A referenced string that is missing from the output means
the step removed something the conversation points at: the caller retries lighter (compression) or reverts that unit
only. Nothing here calls a model: regular expressions only, a few milliseconds per unit.

The same identifier pattern drives identifier-safe compression (split_protected): identifier spans are cut out of a
prose run before LLMLingua-2 sees it and re-joined byte for byte, so the model cannot rewrite "NIMBUS-5044" as
"NIMBUS - 5044" (audit H3). Placeholder substitution is deliberately not used: LLMLingua-2 drops or splits placeholders.
"""

import re
from typing import Iterable

# Kept identical to context_engineering.extract._ERROR_LINE (tests/test_fidelity.py fails if the two drift apart).
SEVERITY = re.compile(
    r"(traceback|\b(error|errors|exception|fatal|panic|failed|failure|fail|denied|refused|timed? ?out|warning|warn)\b"
    r"|exit (code|status) [1-9]|assert(ion)?error|\bE\s{2,})",
    re.I,
)

_URL = r"https?://[^\s<>\"'`]+"
_ISO = r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:[.,]\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?"
_KEY_VALUE = r"[A-Za-z_][\w.\-]*=[^\s,;\"'`)\]}]+"
_THOUSANDS = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?"
_DOTTED_NUMBER = r"v?\d+(?:\.\d+)+(?:[-+][0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*)?"   # 3.11.4, 5.2, 10.0.0.1, 1.2.0-rc.1
_JOINED = r"(?:~/|\.{1,2}/|/)?[A-Za-z0-9]+(?:[-_./:@#][A-Za-z0-9]+)+/?"        # NIMBUS-5044, IDLE_TIMEOUT, a/b.py
_CAMEL = r"[a-z]+[A-Z][A-Za-z0-9]*"
_MIXED = r"[A-Za-z]+\d[A-Za-z0-9]*|\d+[A-Za-z][A-Za-z0-9]*"                     # v2, 256Mi, 30000ms, x86
IDENTIFIER = re.compile(
    rf"(?<![\w])(?:{_URL}|{_ISO}|{_KEY_VALUE}|{_THOUSANDS}|{_DOTTED_NUMBER}|{_JOINED}|{_CAMEL}|{_MIXED})(?![\w])"
)
_UNITS = (r"ms|s|sec|secs|seconds?|mins?|minutes?|h|hrs?|hours?|days?|weeks?|months?|years?|%|percent|"
          r"b|kb|mb|gb|tb|kib|mib|gib|tib|ki|mi|gi|usd|eur|gbp|inr|rps|qps|tokens?|requests?|users?|items?|cores?")
NUMBER_WITH_UNIT = re.compile(
    rf"(?<![\w.])(?:[$€£₹]\s?\d+(?:[.,]\d+)*|\d+(?:[.,]\d+)*\s?(?:{_UNITS}))(?![\w])", re.I
)
# Trailing characters that end a sentence rather than an identifier ("see https://x.y/z." or "v1.2,").
_TRAILING = ".,;:!?"
# Identifiers shorter than this are too common to tell anything apart ("v2", "5.2" stay: they carry a digit).
_MIN_LENGTH = 3


def _clean(token: str) -> str:
    return token.rstrip(_TRAILING)


def identifiers(text: str) -> list[str]:
    """Identifier-like strings of `text`, in order of first appearance, without duplicates."""
    found, seen = [], set()
    for match in IDENTIFIER.finditer(text or ""):
        token = _clean(match.group(0))
        # A key=value pair is one span for compression, but a question names its value on its own ("req-00045" for
        # "req=req-00045"), so the value is a must-survive string as well.
        key, equals, value = token.partition("=")
        candidates = [token, value] if equals and value else [token]
        for candidate in candidates:
            if len(candidate) < _MIN_LENGTH and not any(ch.isdigit() for ch in candidate):
                continue
            if candidate and candidate not in seen:
                seen.add(candidate)
                found.append(candidate)
    return found


def numbers_with_units(text: str) -> list[str]:
    found, seen = [], set()
    for match in NUMBER_WITH_UNIT.finditer(text or ""):
        token = match.group(0)
        if token not in seen:
            seen.add(token)
            found.append(token)
    return found


def severity_lines(text: str) -> list[str]:
    return [line for line in (text or "").splitlines() if line.strip() and SEVERITY.search(line)]


def must_survive(text: str) -> list[str]:
    """Identifiers and numbers with units of `text` (the text a lossy step removed or rewrote)."""
    out, seen = [], set()
    for token in identifiers(text) + numbers_with_units(text):
        if token not in seen:
            seen.add(token)
            out.append(token)
    return out


def referenced(strings: Iterable[str], reference: str) -> list[str]:
    """The strings that the reference text mentions (case-insensitive: "ORD-7731" in a question names "ord-7731")."""
    if not reference:
        return []
    lowered = reference.lower()
    return [s for s in strings if len(s) >= _MIN_LENGTH and s.lower() in lowered]


def missing(strings: Iterable[str], output: str) -> list[str]:
    """The strings that do not occur byte for byte in `output`."""
    return [s for s in strings if s not in output]


def missing_referenced(removed: str, output: str, reference: str) -> list[str]:
    """Referenced must-survive strings of `removed` that the output lost. [] means the step passed."""
    return missing(referenced(must_survive(removed), reference), output)


def missing_identifiers(original: str, output: str) -> list[str]:
    """Every identifier of `original` must be in `output` byte for byte (identifier-safe compression, audit H3)."""
    return missing(identifiers(original), output)


def split_protected(text: str) -> list[tuple[bool, str]]:
    """[(protected, piece)]: the identifier spans of `text` (protected) and the text between them, in order. Joining
    the pieces gives `text` back exactly. Numbers with units stay in the prose: LLMLingua-2 keeps digits
    (force_reserve_digit) and a unit word dropped from a gap is caught by the referenced-string check."""
    pieces: list[tuple[bool, str]] = []
    position = 0
    for match in IDENTIFIER.finditer(text):
        start, end = match.start(), match.start() + len(_clean(match.group(0)))
        if end <= start:
            continue
        if start > position:
            pieces.append((False, text[position:start]))
        pieces.append((True, text[start:end]))
        position = end
    if position < len(text):
        pieces.append((False, text[position:]))
    return pieces


class Tally:
    """Fidelity counters of one request, per lossy route: checked, retried and reverted units, and why reverted."""

    ROUTES = ("compress", "records", "passages", "logfold")

    def __init__(self):
        self.counts: dict = {}

    def add(self, route: str, result: str, reason: str = "", amount: int = 1) -> None:
        entry = self.counts.setdefault(route, {"checked": 0, "retried": 0, "reverted": 0, "reasons": {}})
        entry[result] += amount
        if reason:
            entry["reasons"][reason] = entry["reasons"].get(reason, 0) + amount

    def as_dict(self) -> dict:
        return {route: {**entry, "reasons": dict(entry["reasons"])} for route, entry in sorted(self.counts.items())}
