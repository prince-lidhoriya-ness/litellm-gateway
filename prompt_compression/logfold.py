"""Log template folding: collapse runs of near-identical log lines into a marker (route "logfold").

Why (reports/production-readiness-audit/STRATEGY.md, C1.1): CI and service logs are dominated by repeated templates
("GET /api/orders/<*> 200 <*>ms"). Folding a run of them saves tokens on exactly the logs where question-driven record
selection saved nothing (a question without an identifier) or deleted the answer (a root cause two lines from the
matched line). Folding does not read the question, so the output is the same whatever the user asks and byte-stable
for a given log, which keeps the provider's prefix cache warm.

Rules:
  * a line's template masks quoted values and every token that carries a digit (timestamps, ids, numbers, hex, uuids);
    for key=value tokens only the value is masked, so "latency_ms=<*>" still names the field
  * a run is a sequence of consecutive lines with the same template; its first and last lines always stay, and the
    lines in between are replaced by one marker line that names how many lines were folded, their line numbers in the
    block, the template, and the first and last timestamp when the lines carry one
  * a line that matches the severity pattern (ERROR, FATAL, Exception, Traceback, exit code != 0, ...) is never folded
    and ends a run; so does a blank line
  * a run is folded only when the marker is shorter than the lines it replaces

Nothing is invented: the marker holds only gateway-labelled metadata and the template, which is the line's own text
with values masked.
"""

import re
from dataclasses import dataclass
from typing import Callable

from prompt_compression.fidelity import SEVERITY

MARKER_PREFIX = "[gateway: "
_QUOTED = re.compile(r"\"[^\"\n]*\"|'[^'\n]*'")
_SPACES = re.compile(r"(\s+)")
_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?|(?<!\d)\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?!\d)"
)
_TEMPLATE_MAX_CHARS = 160
# A run needs at least this many lines to fold: first + at least two folded lines + last.
MIN_RUN = 4


@dataclass(frozen=True)
class Fold:
    first: int          # 0-based index of the first folded line (the run's first line stays above it)
    last: int           # 0-based index of the last folded line (the run's last line stays below it)
    template: str
    first_time: str
    last_time: str

    @property
    def count(self) -> int:
        return self.last - self.first + 1


def template(line: str) -> str:
    """The line with its values masked: quoted strings, and every token (or key=value value) that carries a digit."""
    masked = _QUOTED.sub("\"<*>\"", line.strip())
    out = []
    for token in _SPACES.split(masked):
        if not token or token.isspace():
            out.append(" " if token else "")
            continue
        key, equals, value = token.partition("=")
        if equals and key and not any(ch.isdigit() for ch in key):
            out.append(f"{key}=<*>" if any(ch.isdigit() for ch in value) else token)
        elif any(ch.isdigit() for ch in token):
            out.append("<*>")
        else:
            out.append(token)
    return "".join(out)


def timestamp(line: str) -> str:
    match = _TIMESTAMP.search(line)
    return match.group(0) if match else ""


def marker(fold: Fold) -> str:
    shown = fold.template if len(fold.template) <= _TEMPLATE_MAX_CHARS else fold.template[:_TEMPLATE_MAX_CHARS] + "..."
    times = f", first {fold.first_time}, last {fold.last_time}" if fold.first_time and fold.last_time else ""
    return (f"{MARKER_PREFIX}{fold.count} similar lines folded (lines {fold.first + 1}-{fold.last + 1}), "
            f"template \"{shown}\"{times}]")


def plan_folds(lines: list, count_tokens: Callable[[str], int]) -> list:
    """The folds for a block's lines, in order. Each fold keeps its run's first and last line."""
    templates = [None if not line.strip() or SEVERITY.search(line) else template(line) for line in lines]
    folds, start = [], 0
    while start < len(lines):
        end = start
        if templates[start] is not None:
            while end + 1 < len(lines) and templates[end + 1] == templates[start]:
                end += 1
        if end - start + 1 >= MIN_RUN:
            first, last = start + 1, end - 1
            fold = Fold(first, last, templates[start], timestamp(lines[first]), timestamp(lines[last]))
            if count_tokens(marker(fold)) < count_tokens("\n".join(lines[first:last + 1])):
                folds.append(fold)
        start = end + 1
    return folds


def apply(lines: list, folds: list) -> list:
    """The lines with every fold replaced by its marker line."""
    out, position = [], 0
    for fold in folds:
        out.extend(lines[position:fold.first])
        out.append(marker(fold))
        position = fold.last + 1
    out.extend(lines[position:])
    return out
