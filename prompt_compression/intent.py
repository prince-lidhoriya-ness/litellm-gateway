"""Task intent of a request: may whole passages or records be dropped, or does the task need all of the text?

Why this exists: passage and record selection keep what the question names and drop the rest. That is right for a lookup
("What was the error code of request req-17?") and wrong for a task that reads the whole text: summarising, translating,
rewriting or reviewing a document. Before this check a "Summarize the whole report" request lost 3 of its 7 sections,
because "summarize" is a stopword and the remaining words picked a QA-style half of the document
(PROJECT_AUDIT_REPORT.md, F-07).

The check is deliberately lexical and conservative: any of these words in the instruction or the question of the latest
user message makes the request a "transform" request. Selection is then off; prose may still be compressed (that keeps
every passage, only shorter). A missed lookup costs some savings; a missed transform would cost content.
"""

import re

LOOKUP = "lookup"
TRANSFORM = "transform"

_TRANSFORM_TERMS = (
    r"summar\w*", r"tl;?\s?dr", r"overview", r"outline", r"recap", r"digest", r"synopsis", r"abstract",
    r"translat\w*", r"rewrit\w*", r"re-?word\w*", r"rephras\w*", r"paraphras\w*", r"proof-?read\w*", r"copy-?edit\w*",
    r"edit", r"polish", r"improve", r"simplify", r"shorten", r"condense", r"review", r"critique", r"compare",
    r"key (?:points|findings|takeaways|ideas)", r"main (?:points|ideas|findings|themes)", r"takeaways", r"highlights",
    r"entire", r"whole", r"every", r"each", r"list all", r"extract all", r"find all", r"all (?:of )?the",
)
_TRANSFORM = re.compile(r"\b(?:" + "|".join(_TRANSFORM_TERMS) + r")\b", re.IGNORECASE)


def detect(text: str) -> str:
    """TRANSFORM when the text asks for a task over the whole input, else LOOKUP."""
    return TRANSFORM if text and _TRANSFORM.search(text) else LOOKUP
