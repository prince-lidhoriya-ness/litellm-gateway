"""Context Analyzer: what is in the request, by category, and what may be edited.

Pinned (never edited by any stage):
  * system and developer messages (the stable prefix)
  * the first user message (its constraints are often irreplaceable) and the latest user message (the query)
  * everything after the last assistant message (the tool results the model is about to read)
"""

import hashlib
import json
import re

from context_engineering import tokens as tk
from context_engineering.structures import (
    CURRENT_QUERY, DUPLICATE_MARKER, HISTORY, RETRIEVED, STUB_MARKER, SUMMARY_MARKER, SYSTEM, TOOL_DEFINITIONS,
    TOOL_OUTPUT, ContextItem, ContextProfile,
)

SYSTEM_ROLES = frozenset({"system", "developer"})
TOOL_ROLES = frozenset({"tool", "function"})

# Volatile content in a system prompt changes every request and defeats prefix caching.
VOLATILE_PATTERNS = {
    "iso_datetime": re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?"),
    "clock_time": re.compile(r"\b\d{1,2}:\d{2}:\d{2}\b"),
    "uuid": re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I),
    "request_id": re.compile(r"\b(?:request|req|trace|session)[ _-]?id\s*[:=]\s*\S+", re.I),
    "unix_timestamp": re.compile(r"\b1[6-9]\d{8}(?:\d{3})?\b"),
}

_ERROR = re.compile(
    r"(traceback \(most recent call last\)|\b(error|exception|fatal|panic|failed|failure)\b|exit (code|status) [1-9]"
    r"|\bnon-zero exit\b|command not found|permission denied)",
    re.I,
)


def is_error_output(text: str) -> bool:
    return bool(_ERROR.search(text[:20000]))


def content_sha(message: dict) -> str:
    return hashlib.sha256(tk.message_text(message).encode("utf-8", "surrogatepass")).hexdigest()


def is_gateway_made(text: str) -> bool:
    return text.startswith((STUB_MARKER, DUPLICATE_MARKER, SUMMARY_MARKER))


def volatile_hits(text: str) -> list[str]:
    return [name for name, pattern in VOLATILE_PATTERNS.items() if pattern.search(text)]


def tool_names(messages: list) -> dict:
    """tool_call_id -> function name, from assistant tool_calls."""
    names = {}
    for message in messages:
        for call in message.get("tool_calls") or []:
            if isinstance(call, dict) and call.get("id"):
                names[call["id"]] = (call.get("function") or {}).get("name") or ""
    return names


def analyze(messages: list, tools=None, hash_salt: str = "", error_ranks: int = 3) -> ContextProfile:
    """`error_ranks`: only the newest this-many tool results are checked for error output (the masking error guard
    needs no more, and the check is the costliest regex here)."""
    last_user = max((i for i, m in enumerate(messages) if m.get("role") == "user"), default=None)
    first_user = min((i for i, m in enumerate(messages) if m.get("role") == "user"), default=None)
    last_assistant = max((i for i, m in enumerate(messages) if m.get("role") == "assistant"), default=None)
    names = tool_names(messages)
    tool_indexes = [i for i, m in enumerate(messages) if m.get("role") in TOOL_ROLES]
    rank = {index: len(tool_indexes) - 1 - position for position, index in enumerate(tool_indexes)}

    items = []
    totals = {category: 0 for category in (SYSTEM, TOOL_DEFINITIONS, HISTORY, TOOL_OUTPUT, RETRIEVED, CURRENT_QUERY)}
    turn = 0
    system_text = []
    for index, message in enumerate(messages):
        role = message.get("role") or ""
        if role == "user":
            turn += 1
        text = tk.message_text(message)
        made = is_gateway_made(text)
        if role in SYSTEM_ROLES:
            category = SYSTEM
            system_text.append(text)
        elif role in TOOL_ROLES:
            category = TOOL_OUTPUT
        elif index == last_user:
            category = CURRENT_QUERY
        elif made and text.startswith(SUMMARY_MARKER):
            category = RETRIEVED
        else:
            category = HISTORY
        pinned = (
            role in SYSTEM_ROLES
            or index in (first_user, last_user)
            or (last_assistant is not None and index > last_assistant)
            or (last_assistant is None and role in TOOL_ROLES)
        )
        tokens = tk.message_tokens(message)
        totals[category] += tokens
        call_id = message.get("tool_call_id") if role in TOOL_ROLES else None
        items.append(ContextItem(
            index=index, role=role, category=category, tokens=tokens, turn=turn,
            content_sha=hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest(),
            tool_name=(names.get(call_id) or message.get("name")) if role in TOOL_ROLES else None,
            tool_call_id=call_id, tool_rank=rank.get(index),
            is_error=role in TOOL_ROLES and rank.get(index, error_ranks) < error_ranks and is_error_output(text),
            pinned=pinned, gateway_made=made,
        ))
    tools_tokens = tk.tools_tokens(tools)
    totals[TOOL_DEFINITIONS] = tools_tokens
    prefix = "\x1e".join(system_text) + "\x1d" + (json.dumps(tools, sort_keys=True, ensure_ascii=False) if tools else "")
    prefix_sha = hashlib.sha256(prefix.encode("utf-8", "surrogatepass")).hexdigest()
    first_text = tk.message_text(messages[first_user]) if first_user is not None else ""
    conversation_key = hashlib.sha256(f"{hash_salt}\x1f{prefix_sha}\x1f{first_text}".encode("utf-8", "surrogatepass"))
    volatile = sorted({name for text in system_text for name in volatile_hits(text)})
    return ContextProfile(
        items=tuple(items), totals=totals, total_tokens=sum(totals.values()), tools_tokens=tools_tokens,
        last_user_index=last_user, last_assistant_index=last_assistant, prefix_sha=prefix_sha[:16],
        conversation_key=conversation_key.hexdigest()[:16], volatile=tuple(volatile),
        system_tokens=totals[SYSTEM],
    )
