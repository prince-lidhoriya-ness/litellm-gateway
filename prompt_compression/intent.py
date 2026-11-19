"""Task intent of a request: may whole passages or records be dropped, or does the task need all of the text?

Three intents (reports/production-readiness-audit/STRATEGY.md, M3):

    lookup     the question names a record or value: an identifier-like word (a digit, "_", "-" or "." inside it) and no
               diagnose or transform term. "What was the error code of request req-17?" is not one ("error"), "What is
               the status of order ord-7731?" is.
    diagnose   the question asks why something happened or what went wrong (why, fail, error, root cause, wrong, broke,
               debug, investigate, crash, slow, ...). The evidence for a failure is rarely the line that names the
               record, so nothing is selected.
    transform  a task over the whole input (summarise, translate, rewrite, review, list all, ...) and **every request
               that is neither of the above**: the conservative default.

Passage and record selection run only on a positive lookup (router.py; the selector also checks that the identifier
singles out at most 30% of the lines or passages). Prose may still be compressed for every intent: that keeps every
passage, only shorter. The check is lexical on purpose: a gate whose default is safe is more predictable than a model,
and the mistake it makes (a missed saving) is cheap. Before this rewrite the default was "lookup", and wording alone
decided whether a root-cause line was deleted (audit C1, §3.2).
"""

import re
from typing import Optional

LOOKUP = "lookup"
DIAGNOSE = "diagnose"
TRANSFORM = "transform"
INTENTS = (LOOKUP, DIAGNOSE, TRANSFORM)

_TRANSFORM_TERMS = (
    r"summar\w*", r"tl;?\s?dr", r"overview", r"outline", r"recap", r"digest", r"synopsis", r"abstract",
    r"translat\w*", r"rewrit\w*", r"re-?word\w*", r"rephras\w*", r"paraphras\w*", r"proof-?read\w*", r"copy-?edit\w*",
    r"edit", r"polish", r"improve", r"simplify", r"shorten", r"condense", r"review", r"critique", r"compare",
    r"key (?:points|findings|takeaways|ideas)", r"main (?:points|ideas|findings|themes)", r"takeaways", r"highlights",
    r"entire", r"whole", r"every", r"each", r"list all", r"extract all", r"find all", r"all (?:of )?the",
    r"extract\w*", r"list\w*", r"enumerat\w*",
)
_DIAGNOSE_TERMS = (
    r"why", r"how come", r"fail\w*", r"error\w*", r"root[- ]?cause\w*", r"cause[sd]?", r"wrong", r"broke\w*",
    r"break\w*", r"debug\w*", r"investigat\w*", r"crash\w*", r"slow\w*", r"hang\w*", r"hung", r"stuck", r"bug\w*",
    r"issue\w*", r"problem\w*", r"incident\w*", r"outage\w*", r"exception\w*", r"timeout\w*", r"timed out",
    r"diagnos\w*", r"troubleshoot\w*", r"not working", r"doesn'?t work", r"stopped", r"degrad\w*", r"latency",
)
_TRANSFORM = re.compile(r"\b(?:" + "|".join(_TRANSFORM_TERMS) + r")\b", re.IGNORECASE)
_DIAGNOSE = re.compile(r"\b(?:" + "|".join(_DIAGNOSE_TERMS) + r")\b", re.IGNORECASE)
_WORD = re.compile(r"[A-Za-z0-9]+(?:[_\-.][A-Za-z0-9]+)*")


def names_identifier(text: str) -> bool:
    """True when the text holds an identifier-like word: a digit, or "_", "-" or "." between characters."""
    for word in _WORD.findall(text or ""):
        if len(word) > 1 and (any(ch.isdigit() for ch in word) or any(ch in word for ch in "_-.")):
            return True
    return False


def detect(text: str, query: Optional[str] = None) -> str:
    """The intent of a request, from its instruction text (first and last paragraph of the latest user message) and
    its question (`query`, the last paragraph; the instruction text when None)."""
    if not text or not text.strip():
        return TRANSFORM
    if _TRANSFORM.search(text):
        return TRANSFORM
    if _DIAGNOSE.search(text):
        return DIAGNOSE
    return LOOKUP if names_identifier(query if query is not None else text) else TRANSFORM
