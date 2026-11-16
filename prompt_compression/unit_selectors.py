"""Whole-unit selection: drop passages, records or old turns instead of pruning tokens.

The research report (reports/compression-fit/REPORT.md, sections 4.2, 4.3, 4.5) found that removing whole units that
the question does not need is the one lossy step that did not damage exact strings: a question-aware block selector
kept 1.000 of QA items, 0.950 of log and JSON items and 0.900 of code items at about 2x, while every token-level
compressor lost at least 0.150. Two caveats travel with that result and shape the guards here:

  * the local questions shared a rare token with the answer-bearing unit, the easiest case for lexical selection, so
    every selector here does nothing when it finds no lexical signal;
  * nothing was measured on chat history, so trimming is off unless a token budget is set, never splits a turn, and
    never touches tool calls or their results.

No third-party dependency: BM25 is a few lines of plain Python. A GPU-hosted question-aware model (CPC or
LongLLMLingua, report section 5.3) can replace `rank_units` later without touching the callers.
"""

import math
import re
from typing import Callable, Optional, Sequence

_TOKEN = re.compile(r"[a-z0-9]+(?:[_\-.][a-z0-9]+)*")
# Function words and question words carry no evidence about which passage is meant.
_STOPWORDS = frozenset(
    "a an and are as at be been by can could did do does for from had has have how i if in into is it its me more "
    "most much many of on or our please s so some tell than that the their them then there these they this to was "
    "we were what when where which who whom whose why will with would you your about above after all also any "
    "because before between both but each few here just like not only other out over own same should such too very "
    "up down off again further once give show explain describe summarize summary list say said say".split()
)


def tokenize(text: str) -> list[str]:
    return [token for token in _TOKEN.findall(text.lower()) if len(token) > 1 and token not in _STOPWORDS]


def rank_units(query: str, units: Sequence[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """BM25 score of each unit for the query. All zeros means the query shares no token with any unit."""
    query_terms = set(tokenize(query))
    docs = [tokenize(unit) for unit in units]
    if not query_terms or not docs:
        return [0.0] * len(units)
    n = len(docs)
    average = sum(len(doc) for doc in docs) / n or 1.0
    document_frequency = {term: sum(1 for doc in docs if term in doc) for term in query_terms}
    if n >= 5:
        # a term found in most units cannot tell them apart
        query_terms = {term for term in query_terms if document_frequency[term] <= 0.6 * n}
        if not query_terms:
            return [0.0] * len(units)
    scores = []
    for doc in docs:
        counts: dict[str, int] = {}
        for token in doc:
            if token in query_terms:
                counts[token] = counts.get(token, 0) + 1
        score = 0.0
        for term, count in counts.items():
            df = document_frequency[term]
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            score += idf * count * (k1 + 1) / (count + k1 * (1 - b + b * len(doc) / average))
        scores.append(score)
    return scores


def select_passages(
    units: Sequence[str], query: str, keep_ratio: float, count_tokens: Callable[[str], int]
) -> Optional[list[bool]]:
    """Keep-flags for whole passages, or None when there is no lexical signal (then nothing is dropped).

    Positive-scoring passages are kept best first until `keep_ratio` of the tokens is reached; if they run out first,
    the shortfall is filled with the neighbours of kept passages, because the evidence for a question often sits next
    to the passage that matches it. Original order is the caller's business.
    """
    scores = rank_units(query, units)
    if not units or max(scores) <= 0:
        return None
    tokens = [count_tokens(unit) for unit in units]
    target = keep_ratio * sum(tokens)
    kept: set[int] = set()
    used = 0
    for index in sorted(range(len(units)), key=lambda i: (-scores[i], i)):
        if scores[index] <= 0:
            break
        if kept and used >= target:
            break
        kept.add(index)
        used += tokens[index]
    if used < target:
        rest = [i for i in range(len(units)) if i not in kept]
        rest.sort(key=lambda i: (min(abs(i - j) for j in kept), i))
        for index in rest:
            if used >= target:
                break
            kept.add(index)
            used += tokens[index]
    return [index in kept for index in range(len(units))]


_BRACKET_ONLY = re.compile(r"^\s*[\[\]{}(),]*\s*$")


def _query_identifiers(query: str) -> set[str]:
    """Words of the question that name a record: they carry a digit, an underscore, a dash or a dot between characters."""
    found = set()
    for token in tokenize(query):
        if any(ch.isdigit() for ch in token) or "_" in token or "-" in token or "." in token:
            found.add(token)
    return found


def select_records(
    lines: Sequence[str], query: str, subtype: str, context_lines: int = 1, max_match_share: float = 0.3
) -> Optional[list[bool]]:
    """Keep-flags for the lines of a log, JSON-lines, CSV or one-object-per-line JSON block.

    Only acts when the question names a record: some identifier-like word of the question must occur in at least one
    line and in at most `max_match_share` of the lines (a word found on most lines is a field name and is ignored).
    Matching lines and their neighbours are kept, plus the header line of a table and bracket-only lines of a JSON
    array. Anything else returns None (keep every line).
    """
    identifiers = _query_identifiers(query)
    if not identifiers or not lines:
        return None
    lowered = [line.lower() for line in lines]
    # An identifier that occurs on most lines is a field name ("latency_ms"), not a record id: it says nothing about
    # which record is meant, so only identifiers that single out a few lines count.
    hit_set: set[int] = set()
    for identifier in identifiers:
        matched = [i for i, line in enumerate(lowered) if identifier in line]
        if matched and len(matched) <= max_match_share * len(lines):
            hit_set.update(matched)
    hits = sorted(hit_set)
    if not hits or len(hits) > max_match_share * len(lines):
        return None
    keep = [False] * len(lines)
    for index in hits:
        for neighbour in range(max(0, index - context_lines), min(len(lines), index + context_lines + 1)):
            keep[neighbour] = True
    if subtype in ("csv", "tsv", "table"):
        keep[0] = True
    for index, line in enumerate(lines):
        if _BRACKET_ONLY.match(line):
            keep[index] = True
    return keep


def drop_trailing_comma(lines: list[str]) -> list[str]:
    """After records were removed from a JSON array, the last record must not end with a comma."""
    out = list(lines)
    for index in range(len(out) - 1, -1, -1):
        stripped = out[index].strip()
        if stripped in ("]", "}", ""):
            continue
        if stripped.endswith(","):
            out[index] = out[index].rstrip()[:-1]
        break
    return out


# ---------------------------------------------------------------------------------------------------------------
# chat history

PRESERVED_ROLES = frozenset({"system", "developer"})


def _is_tool_related(message: dict) -> bool:
    return message.get("role") in ("tool", "function") or bool(message.get("tool_calls") or message.get("function_call"))


def trim_history(
    messages: list, max_tokens: int, keep_messages: int, message_tokens: Callable[[dict], int],
    protected: Optional[Callable[[int], bool]] = None,
) -> tuple[list[int], int]:
    """Indices of messages to drop: the oldest whole turns, only while the prompt exceeds `max_tokens`.

    A turn is a user message and everything up to the next user message. Dropped turns are contiguous from the oldest
    end (after leading system/developer messages), the last `keep_messages` messages always stay, and the walk stops at
    the first turn that contains a tool call or tool result, so a call is never separated from its result, or a
    message for which `protected(index)` is true. Returns (indices dropped, tokens removed).
    """
    if max_tokens <= 0:
        return [], 0
    total = sum(message_tokens(m) for m in messages)
    if total <= max_tokens:
        return [], 0
    start = 0
    while start < len(messages) and messages[start].get("role") in PRESERVED_ROLES:
        start += 1
    protected_from = max(start, len(messages) - max(1, keep_messages))
    turns: list[list[int]] = []
    for index in range(start, protected_from):
        if messages[index].get("role") == "user" or not turns:
            turns.append([])
        turns[-1].append(index)
    dropped: list[int] = []
    removed = 0
    for turn in turns:
        if total - removed <= max_tokens:
            break
        # a turn that runs into the protected tail would be cut in half: leave it
        if turn[-1] + 1 >= protected_from and messages[protected_from].get("role") != "user":
            break
        if any(_is_tool_related(messages[i]) or (protected is not None and protected(i)) for i in turn):
            break
        if messages[turn[0]].get("role") != "user":
            break
        dropped.extend(turn)
        removed += sum(message_tokens(messages[i]) for i in turn)
    return dropped, removed
