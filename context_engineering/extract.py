"""Deterministic, verbatim extraction. No model, no paraphrase: every line or sentence returned exists in the input.

Used by masking (the key lines kept in an observation stub) and compaction (constraints, decisions, open tasks and
identifiers kept from older turns). Determinism matters twice: the same input must give the same stub on every
request (prefix caching), and nothing invented may enter the context (fidelity).
"""

import json
import re

from context_engineering import tokens as tk

_ERROR_LINE = re.compile(
    r"(traceback|\b(error|errors|exception|fatal|panic|failed|failure|fail|denied|refused|timed? ?out|warning|warn)\b"
    r"|exit (code|status) [1-9]|assert(ion)?error|\bE\s{2,})",
    re.I,
)
# Words that name a thing exactly: carry a digit, an underscore, a slash, a dot or dash between characters, or camelCase.
_IDENTIFIER = re.compile(
    r"(?:[A-Za-z]:\\|/|\./|~/)?[\w.\-/\\]*?(?:\d|_|[a-z][A-Z]|\w[./\\-]\w)[\w.\-/\\:]*"
)
_URL = re.compile(r"https?://[^\s)>\]\"']+")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])|\n+")

CONSTRAINT = re.compile(
    r"\b(must|must not|mustn't|never|always|do not|don't|should|shouldn't|required?|requirement|only use|only|"
    r"make sure|ensure|prefer|avoid|without|at most|at least|no more than|deadline|constraint|keep)\b",
    re.I,
)
DECISION = re.compile(
    r"\b(decided|decide|decision|we will|we'll|i will|i'll|let's|chose|choose|chosen|going with|agreed|approach|"
    r"plan is|switched to|use (?:the|a)|settled on|instead of)\b",
    re.I,
)
OPEN_TASK = re.compile(
    r"(\b(todo|fixme|next step|next steps|pending|remaining|still need|not yet|unresolved|open question|follow[- ]up|"
    r"blocked|to do)\b|\?\s*$)",
    re.I,
)


def identifiers(text: str, limit: int = 200) -> list[str]:
    """Identifier-like tokens in order of first appearance (urls, paths, ids, numbers with letters, snake/camelCase)."""
    found: list[str] = []
    seen = set()
    for match in list(_URL.finditer(text)) + list(_IDENTIFIER.finditer(text)):
        token = match.group(0).strip(".,;:()[]{}<>\"'`")
        if len(token) < 3 or token in seen or token.isdigit() and len(token) < 4:
            continue
        if not any(ch.isalpha() for ch in token) and not any(ch.isdigit() for ch in token):
            continue
        seen.add(token)
        found.append(token)
        if len(found) >= limit:
            break
    return found


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s and s.strip()]


def matching_sentences(text: str, pattern: re.Pattern, max_chars: int = 400) -> list[str]:
    return [s for s in sentences(text) if len(s) <= max_chars and pattern.search(s)]


def json_shape(text: str):
    """A one-line structural description of a JSON document, or None. Keys and lengths only, no values."""
    stripped = text.strip()
    if not stripped or stripped[0] not in "[{":
        return None
    try:
        value = json.loads(stripped)
    except (TypeError, ValueError):
        return None
    if isinstance(value, dict):
        keys = list(value)[:20]
        return f"JSON object with {len(value)} keys: {', '.join(map(str, keys))}" + (" ..." if len(value) > 20 else "")
    if isinstance(value, list):
        item_keys = sorted({k for item in value[:50] if isinstance(item, dict) for k in item})[:20]
        described = f"JSON array of {len(value)} items"
        return described + (f"; item keys: {', '.join(map(str, item_keys))}" if item_keys else "")
    return None


def key_lines(text: str, follow_up: str = "", max_tokens: int = 150, head_tail: int = 3) -> list[str]:
    """Lines worth keeping from a tool output, verbatim and in their original order.

    Priority when the budget runs out: error lines, lines naming an identifier that the follow-up text (the assistant
    message right after the tool result) mentions, then the first and last `head_tail` lines."""
    lines = text.splitlines()
    if not lines:
        return []
    priority: dict = {}
    referenced = {token for token in identifiers(follow_up) if len(token) >= 4} if follow_up else set()
    for position, line in enumerate(lines):
        if not line.strip():
            continue
        if _ERROR_LINE.search(line):
            priority.setdefault(position, 0)
        elif referenced and any(token in line for token in referenced):
            priority.setdefault(position, 1)
    for position in list(range(min(head_tail, len(lines)))) + list(range(max(0, len(lines) - head_tail), len(lines))):
        if lines[position].strip():
            priority.setdefault(position, 2)
    chosen, used = set(), 0
    for position in sorted(priority, key=lambda p: (priority[p], p)):
        line = lines[position]
        if len(line) > 500:
            line = line[:500]
        cost = tk.text_tokens(line) + 1
        if used + cost > max_tokens:
            continue
        chosen.add(position)
        used += cost
    return [lines[p][:500] for p in sorted(chosen)]
