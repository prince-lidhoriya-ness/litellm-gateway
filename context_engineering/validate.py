"""Invariants every stage's output must keep. A stage whose output breaks one is undone: the engine continues with the
last valid messages (the output of the previous stage), so a failure never reaches the provider.

    serialisable   the messages are still JSON-serialisable
    system         system/developer messages are unchanged and in order ("system_edit" allows volatile relocation)
    query          the latest user message is unchanged ("query_suffix" allows text appended to its end)
    current step   every message after the last assistant message is unchanged (the results the model will read)
    tool pairing   every tool result answers a tool_call of an earlier assistant message, and every tool_call that had
                   a result still has one
    roles          every message has a known role
    no growth      the estimated token count did not grow ("query_suffix" allows the relocated lines)
"""

import json

from context_engineering import tokens as tk

KNOWN_ROLES = frozenset({"system", "developer", "user", "assistant", "tool", "function"})


def _last(messages: list, role: str):
    return max((i for i, m in enumerate(messages) if m.get("role") == role), default=None)


def _pairs(messages: list) -> tuple[set, set]:
    """(tool_call ids issued, tool_call ids answered after being issued)."""
    issued, answered = set(), set()
    for message in messages:
        for call in message.get("tool_calls") or []:
            if isinstance(call, dict) and call.get("id"):
                issued.add(call["id"])
        if message.get("role") == "tool" and message.get("tool_call_id") in issued:
            answered.add(message["tool_call_id"])
    return issued, answered


def check(original: list, result: list, allow: frozenset = frozenset()) -> list[str]:
    problems = []
    try:
        json.dumps(result, ensure_ascii=False, default=None)
    except (TypeError, ValueError):
        problems.append("serialisable")
    if any(not isinstance(m, dict) or m.get("role") not in KNOWN_ROLES for m in result):
        problems.append("roles")
        return problems
    if "system_edit" not in allow:
        before = [m for m in original if m.get("role") in ("system", "developer")]
        after = [m for m in result if m.get("role") in ("system", "developer")]
        if before != after:
            problems.append("system")
    last_user_before, last_user_after = _last(original, "user"), _last(result, "user")
    if last_user_before is not None:
        if last_user_after is None:
            problems.append("query")
        else:
            a, b = original[last_user_before], result[last_user_after]
            if "query_suffix" in allow:
                same = tk.message_text(b).startswith(tk.message_text(a)) and a.get("role") == b.get("role")
            else:
                same = a == b
            if not same:
                problems.append("query")
    tail_start = _last(original, "assistant")
    if tail_start is not None:
        tail = original[tail_start:]
        if len(result) < len(tail):
            problems.append("current_step")
        else:
            offset = len(result) - len(tail)
            for position, message in enumerate(tail):
                if tail_start + position == last_user_before:
                    continue                      # judged by the "query" check above
                if result[offset + position] != message:
                    problems.append("current_step")
                    break
    issued, answered = _pairs(result)
    issued_before, answered_before = _pairs(original)
    # A client may already send an unanswered or orphaned result; only orphans this stage created count.
    orphans_before = {m.get("tool_call_id") for m in original if m.get("role") == "tool"} - issued_before
    if any(m.get("role") == "tool" and m.get("tool_call_id") not in issued
           and m.get("tool_call_id") not in orphans_before for m in result):
        problems.append("tool_pairing")
    if any(call_id in issued and call_id not in answered for call_id in answered_before):
        problems.append("tool_pairing")
    if "query_suffix" not in allow and tk.messages_tokens(result) > tk.messages_tokens(original):
        problems.append("no_growth")
    return sorted(set(problems))
