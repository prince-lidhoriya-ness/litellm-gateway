"""Split message text into blocks and mark which blocks are exact text.

Why this exists: the local check in reports/compression-fit/REPORT.md found that token-level compression damages
exactly the text that is read for exact strings. LLMLingua-2 at about 2x kept none of the six field names of a log
line, split identifiers such as MAX_WINDOW_PB into "MAX WINDOW _ PB", and dropped the "/04/" from a date. So only
running prose goes to the compressor; code, structured records and identifier-dense text stay byte for byte.

split_segments() never changes a character: "".join(seg.text + seg.sep for seg in segments) == text always.
Each segment has a kind:

    code        fenced block, or lines that look like source code, shell commands or SQL
    structured  JSON, JSON lines, log lines, tables, CSV, key=value or key: value configuration, stack traces
    exact       prose-looking text that is dense in numbers, identifiers, paths, e-mail addresses, camelCase or names
                (capitalised words in the middle of a sentence)
    prose       everything else; the only kind a compressor may touch

Rules are heuristics and err on the side of "exact". They are cheap regexes, no model, so they add well under a
millisecond per paragraph.
"""

import json
import math
import re
from dataclasses import dataclass

CODE = "code"
STRUCTURED = "structured"
EXACT = "exact"
PROSE = "prose"


@dataclass(frozen=True)
class Segment:
    kind: str
    subtype: str
    text: str
    sep: str = ""   # whitespace that followed the block in the original (blank lines between paragraphs)

    @property
    def protected(self) -> bool:
        """True when a compressor must not touch the text."""
        return self.kind != PROSE

    @property
    def full(self) -> str:
        return self.text + self.sep


def join_segments(segments) -> str:
    return "".join(segment.full for segment in segments)


# ---------------------------------------------------------------------------------------------------------------
# splitting

_PARAGRAPH_BREAK = re.compile(r"(\n[ \t]*\n(?:[ \t]*\n)*)")


def _fenced_chunks(text: str) -> list[tuple[bool, str]]:
    """[(is_fenced_code, chunk)] covering the text exactly. An unterminated fence runs to the end."""
    chunks: list[tuple[bool, str]] = []
    buffer: list[str] = []
    fence = None
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if fence is None:
            if stripped.startswith("```") or stripped.startswith("~~~"):
                if buffer:
                    chunks.append((False, "".join(buffer)))
                    buffer = []
                fence = stripped[:3]
            buffer.append(line)
            continue
        buffer.append(line)
        if stripped.startswith(fence):
            chunks.append((True, "".join(buffer)))
            buffer = []
            fence = None
    if buffer:
        chunks.append((fence is not None, "".join(buffer)))
    return chunks


def split_segments(text: str, exact_density: float = 0.15) -> list[Segment]:
    segments: list[Segment] = []
    for fenced, chunk in _fenced_chunks(text):
        if fenced:
            segments.append(Segment(CODE, "fence", chunk))
            continue
        parts = _PARAGRAPH_BREAK.split(chunk)
        for index in range(0, len(parts), 2):
            block = parts[index]
            sep = parts[index + 1] if index + 1 < len(parts) else ""
            if not block:
                if segments and sep:
                    previous = segments[-1]
                    segments[-1] = Segment(previous.kind, previous.subtype, previous.text, previous.sep + sep)
                elif sep:
                    segments.append(Segment(PROSE, "empty", "", sep))
                continue
            kind, subtype = classify_block(block, exact_density)
            segments.append(Segment(kind, subtype, block, sep))
    return segments


# ---------------------------------------------------------------------------------------------------------------
# classification

_TIMESTAMP = re.compile(r"^\s*\[?(?:\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}|\d{2}:\d{2}:\d{2})")
_LEVEL = re.compile(r"\b(?:TRACE|DEBUG|INFO|NOTICE|WARN|WARNING|ERROR|FATAL|CRITICAL)\b")
_LEVEL_START = re.compile(r"^\s*\[?(?:TRACE|DEBUG|INFO|NOTICE|WARN|WARNING|ERROR|FATAL|CRITICAL)\b")
_KV_PAIR = re.compile(r"\b[\w.\-]{1,40}=(?:\"[^\"\n]*\"|\S+)")
_STACK = re.compile(
    r"^\s*(?:Traceback \(most recent call last\)|File \".+\", line \d+|at [\w$.<>\[\]]+\(.*\)|Caused by:|"
    r"\w+(?:Error|Exception)\b[:\s])"
)
# Configuration keys are lowercase/snake/dotted or ALL_CAPS; a capitalised word is a person ("Alice: ...") in a transcript.
_KV_LINE = re.compile(r"^\s*(?:-\s+)?(?:[a-z][a-z0-9_.\-]*|[A-Z][A-Z0-9_]+)\s*[:=]\s*\S")
_CODE_LINE = re.compile(
    r"^\s*(?:def |class |import |from \S+ import |return\b|elif\b|else:|try:|except\b|finally:|with .+:\s*$|"
    r"for .+ in .+:\s*$|while .+:\s*$|if .+[:{]\s*$|function\b|const |let |var |public |private |protected |static |"
    r"#include|using |package |namespace |SELECT\b|INSERT\b|UPDATE\b|DELETE\b|CREATE\b|ALTER\b|DROP\b|FROM\b|WHERE\b|"
    r"\$ |git |npm |pip |docker |curl |sudo |@\w+)|"
    r"[{};]\s*$|=>|->|::|^\s*[\w.\[\]]+\s*=\s*[\w.\[\]]+\(.*\)\s*$"
)
_INDENTED = re.compile(r"^(?: {4}|\t)\S")
_SYMBOLS = set("{}[]()<>=;|\\`$^&*~")


def _lines(block: str) -> list[str]:
    return [line for line in block.splitlines() if line.strip()]


def _is_log_line(line: str) -> bool:
    pairs = len(_KV_PAIR.findall(line))
    if pairs >= 3:
        return True
    if _TIMESTAMP.match(line) and (_LEVEL.search(line) or pairs >= 1):
        return True
    return bool(_LEVEL_START.match(line) and pairs >= 1)


def _exactish(token: str) -> bool:
    """A word whose exact characters matter: digits, underscores, paths, addresses, camelCase."""
    word = token.strip(".,;:!?()[]{}\"'`")
    if not word:
        return False
    if any(ch.isdigit() for ch in word):
        return True
    if "_" in word or "/" in word or "\\" in word or "@" in word or "://" in word:
        return True
    return bool(re.search(r"[a-z][A-Z]", word))


_PROPER = re.compile(r"^[A-Z][a-z][A-Za-z'\-]*$")


def _proper_noun(token: str, previous: str | None) -> bool:
    """A capitalised word in the middle of a sentence: a name of a person, place or product.

    Words that start a sentence are not counted, nor are speaker labels ("Alice:") of a transcript."""
    if token.endswith(":"):
        return False
    if previous is not None and not previous.endswith((".", "!", "?", ":")):
        return bool(_PROPER.match(token.strip(".,;!?()[]{}\"'`")))
    return False


def exact_share(text: str) -> tuple[int, int]:
    """(words whose exact characters matter, all words): digits, underscores, paths, camelCase and names.

    Names count because the benchmark showed they are what a question over a document asks for ("who was chief
    executive before ...") and token pruning dropped "Tanaka" from a paragraph that had only two digit-words."""
    tokens = text.split()
    exact = 0
    for index, token in enumerate(tokens):
        previous = tokens[index - 1] if index else None
        if _exactish(token) or _proper_noun(token, previous):
            exact += 1
    return exact, len(tokens)


def _json_like(stripped: str, lines: list[str]) -> str | None:
    if stripped[0] in "{[" and stripped[-1] in "}]":
        try:
            json.loads(stripped)
            return "json"
        except ValueError:
            pass
    if len(lines) >= 2:
        records = sum(1 for line in lines if line.strip().startswith("{") and line.strip().rstrip(",").endswith("}"))
        if records >= math.ceil(0.8 * len(lines)):
            return "jsonl"
    # truncated or hand-edited JSON that no longer parses
    if stripped[0] in "{[" and stripped.count('":') >= 2:
        return "json"
    return None


def _table_like(lines: list[str]) -> str | None:
    n = len(lines)
    if n >= 2 and sum(1 for line in lines if line.count("|") >= 2) >= math.ceil(0.8 * n):
        return "table"
    if n >= 3:
        for separator, name in ((",", "csv"), ("\t", "tsv")):
            counts = [line.count(separator) for line in lines]
            common = max(set(counts), key=counts.count)
            sentences = sum(1 for line in lines if line.rstrip().endswith("."))
            minimum = 2 if separator == "," else 1
            if common >= minimum and counts.count(common) >= math.ceil(0.8 * n) and sentences <= 0.4 * n:
                return name
    return None


_LABEL_LINE = re.compile(r"^[^\n]{1,80}:[ \t]*$")


def label_split(block: str) -> tuple[str, str]:
    """(label line with its newline, rest) when the first line is a short label ending with a colon, else ("", block).

    Prompts often put a label directly above data ("Here is the log:" then the lines, no blank line between)."""
    first, newline, rest = block.partition("\n")
    if newline and rest.strip() and _LABEL_LINE.match(first):
        return first + newline, rest
    return "", block


def classify_block(block: str, exact_density: float = 0.15) -> tuple[str, str]:
    stripped = block.strip()
    if not stripped:
        return PROSE, "empty"
    label, body = label_split(block)
    if label:
        kind, subtype = classify_block(body, exact_density)
        if kind in (CODE, STRUCTURED):
            return kind, subtype
    lines = _lines(block)
    n = len(lines)

    json_kind = _json_like(stripped, lines)
    if json_kind:
        return STRUCTURED, json_kind
    if sum(1 for line in lines if _STACK.match(line)) >= 2:
        return STRUCTURED, "stack"
    if sum(1 for line in lines if _is_log_line(line)) >= max(1, math.ceil(0.5 * n)):
        return STRUCTURED, "log"
    table = _table_like(lines)
    if table:
        return STRUCTURED, table
    if n >= 2 and sum(1 for line in lines if _KV_LINE.match(line) and len(line) <= 200) >= math.ceil(0.6 * n):
        return STRUCTURED, "kv"

    code_lines = sum(1 for line in lines if _CODE_LINE.search(line))
    if code_lines >= math.ceil(0.4 * n):
        return CODE, "code"
    if n >= 2 and sum(1 for line in lines if _INDENTED.match(line)) >= math.ceil(0.6 * n):
        return CODE, "indent"
    non_space = [ch for ch in stripped if not ch.isspace()]
    if n >= 2 and non_space and sum(ch in _SYMBOLS for ch in non_space) / len(non_space) >= 0.15:
        return CODE, "symbols"

    exact, words = exact_share(stripped)
    if exact >= 2 and words and exact / words >= exact_density:
        return EXACT, "ids"
    return PROSE, "prose"
