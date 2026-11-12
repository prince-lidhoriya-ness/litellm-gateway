"""Conversation builders for the tests: OpenAI-format messages with tool calls, logs, JSON, code and long prose."""

import dataclasses
import json

from context_engineering.settings import ContextSettings

SYSTEM = "You are a careful coding assistant for the payments team. Answer precisely."


def settings(**overrides) -> ContextSettings:
    """Code defaults with the request-size gate off; tests switch techniques on explicitly."""
    base = ContextSettings()
    values = dict(min_tokens=0)
    values.update(overrides)
    return dataclasses.replace(base, **values)


def log_output(n: int = 120, tag: str = "svc") -> str:
    return "\n".join(
        f"2026-03-14T19:{i % 60:02d}:00Z INFO {tag}=cart req=req-{i:06x} status=200 latency_ms={100 + i} user=u-{i}"
        for i in range(n)
    )


def error_output(n: int = 60) -> str:
    lines = [f"tests/test_api.py::test_case_{i} PASSED" for i in range(n)]
    lines.insert(n // 2, "FAILED tests/test_api.py::test_login - AssertionError: 401 != 200")
    lines.append("=== 1 failed, %d passed in 3.21s ===" % n)
    return "\n".join(lines)


def json_output(n: int = 80) -> str:
    return json.dumps([{"order_id": f"ORD-{i:04d}", "customer": f"c-{i}", "total": i + 0.5} for i in range(n)])


def tool_round(call_id: str, name: str, arguments: dict, output: str, reply: str) -> list:
    return [
        {"role": "assistant", "content": None, "tool_calls": [
            {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}]},
        {"role": "tool", "tool_call_id": call_id, "content": output},
        {"role": "assistant", "content": reply},
    ]


def agent_conversation(rounds: int = 8, output=log_output, pending_last: bool = False) -> list:
    """One user task, then `rounds` tool calls with large outputs; each reply names one record of its output."""
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": "Investigate the failing cart requests. Never change the database schema."}]
    for i in range(rounds):
        messages += tool_round(f"call_{i}", "read_logs", {"file": f"logs/cart-{i}.log"}, output(),
                               f"Round {i}: request req-{i:06x} looks fine, checking the next file.")
    if pending_last:
        messages.append({"role": "assistant", "content": None, "tool_calls": [
            {"id": "call_last", "type": "function", "function": {"name": "run_tests", "arguments": "{}"}}]})
        messages.append({"role": "tool", "tool_call_id": "call_last", "content": error_output()})
    return messages


PROSE_TOPICS = [
    "the billing service retries failed card captures three times with exponential backoff before giving up",
    "the warehouse dashboard refreshes every five minutes and caches stock counts per region",
    "the onboarding emails are sent by a nightly batch job that reads from the marketing queue",
    "the search index is rebuilt on Sundays and partial updates are streamed from the catalog",
    "the mobile app stores session tokens in the secure enclave and refreshes them hourly",
    "the reporting cluster runs on spot instances and checkpoints every query plan",
    "the support chatbot hands off to a human after two unresolved intents",
    "the invoice generator renders templates with a sandboxed engine and archives the output",
    "the fraud model scores transactions in real time and flags anything above the review threshold",
    "the data retention policy deletes raw event logs after ninety days",
]


def chat_turn(i: int, extra: str = "") -> list:
    topic = PROSE_TOPICS[i % len(PROSE_TOPICS)]
    user = f"Question {i}: explain how {topic}. {extra}".strip()
    answer = (f"Answer {i}: In short, {topic}. " + " ".join(
        f"Detail {j} about this part of the system covers monitoring, ownership, alerting and the rollback runbook."
        for j in range(12)))
    return [{"role": "user", "content": user}, {"role": "assistant", "content": answer}]


def long_chat(turns: int = 14, last_question: str = "What did we say about the fraud model threshold?") -> list:
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": "We are documenting our platform. You must keep answers under 200 words."},
                {"role": "assistant", "content": "Understood. I will keep every answer under 200 words."}]
    for i in range(turns):
        messages += chat_turn(i)
    messages.append({"role": "user", "content": last_question})
    return messages
