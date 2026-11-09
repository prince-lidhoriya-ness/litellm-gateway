"""Redaction guardrail: replace rule-matched secrets and identifiers in every message before anything else runs.

Why this exists: REDACT_SENSITIVE used to be a step inside the compression pipeline, so everything that skipped the
pipeline skipped redaction too: prompts below the size gate, requests that opted out of compression, system and tool
messages, shadow mode and fail-open (PROJECT_AUDIT_REPORT.md, F-15S). As a guardrail it runs on every chat request and
every role, ignores the compression opt-out, applies in shadow mode, and the hook rejects the request (HTTP 503) if it
fails, whatever PROMPT_COMPRESSION_FAIL_MODE says.

Scope: message text (string content and text parts). Tool-call arguments are JSON strings and are left alone, so a
placeholder can never break their syntax; keep secrets out of tool arguments at the source.
This is the rule layer (rules.py) only: it removes what the rules can match. It is not a full DLP system.
"""

import copy

from prompt_compression import rules
from prompt_compression.texts import set_text, text_parts


def redact_messages(messages: list) -> tuple[list, int, list[str]]:
    """(messages with redacted text, spans replaced, rule names). The input list is never changed; an untouched
    request returns the same list object."""
    total, names = 0, set()
    redacted_messages = None
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            continue
        for part_index, text in text_parts(message):
            if not text:
                continue
            new_text, rule_names, count = rules.redact_with_count(text)
            if not count:
                continue
            if redacted_messages is None:
                redacted_messages = list(messages)
            if redacted_messages[index] is message:
                redacted_messages[index] = copy.deepcopy(message)
            set_text(redacted_messages[index], part_index, new_text)
            total += count
            names.update(rule_names)
    return (redacted_messages if redacted_messages is not None else messages), total, sorted(names)
