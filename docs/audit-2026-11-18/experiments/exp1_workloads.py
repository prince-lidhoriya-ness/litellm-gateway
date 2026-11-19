"""Experiment 1: real hook chain (context_engineering -> prompt_compression) over synthetic workloads.

Runs the production callback objects directly (same async_pre_call_hook LiteLLM awaits), with the real LLMLingua-2
model and the real sensitivity encoder loaded from the local Hugging Face cache. No provider is called.
Token counts use the same cl100k_base measure the gateway reports (estimates, not provider billing).
"""
import asyncio
import copy
import json
import os
import random
import sys
import time

GW = r"C:\Users\P7120489\litellm-gateway"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp1_results.json")
sys.path.insert(0, GW)
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("PROMPT_COMPRESSION_LOG_LEVEL", "ERROR")
os.environ.setdefault("CONTEXT_ENGINEERING_LOG_LEVEL", "ERROR")

from prompt_compression.texts import count_tokens, text_parts  # noqa: E402
from prompt_compression.prompt_compression_callback import PromptCompressionCallback  # noqa: E402
from context_engineering.callback import ContextEngineeringCallback  # noqa: E402

SENTENCES = [
    "The regional team reviewed the quarterly results and agreed that the logistics backlog needed attention before the holiday season.",
    "Customers in the northern districts reported longer delivery times, which the support group traced to a change in the carrier schedule.",
    "Management asked for a short summary of the risks, the owners of each risk, and the date by which the mitigation should be in place.",
    "Procurement confirmed that two of the three suppliers could meet the revised volume, but the third asked for a longer lead time.",
    "The pilot in the warehouse near the port reduced average picking time, although the gains were smaller on weekends when staffing was thin.",
    "Finance noted that the forecast had been revised twice in one month and proposed a monthly review with a fixed set of assumptions.",
    "Several engineers raised concerns that the new reporting dashboard hid the raw numbers behind aggregated charts, making audits harder.",
    "The steering group decided to postpone the migration of the legacy inventory system until the vendor released the patch for the batch jobs.",
    "Operations leads described the handover process as informal, with important instructions often passed along in chat rather than written down.",
    "A short training session was scheduled for new staff, covering escalation paths, the on-call rota, and the basic checks before a shipment leaves the dock.",
    "The auditors found no material errors but recommended clearer ownership of the reconciliation step between the two accounting systems.",
    "Over the next quarter the team plans to measure on-time delivery weekly instead of monthly, so that problems surface while they are still small.",
    "Feedback from the pilot suggested that the approval workflow should allow regional managers to delegate sign-off to a named deputy.",
    "The vendor's support contract expires in the spring, and the renewal discussion will need to include the response times that were agreed last year.",
    "Staff turnover in the dispatch team was higher than expected, which made it harder to keep the experienced pickers on the night shift.",
    "A dashboard prototype showed that most delays happened between the packing station and the outbound gate, not in the warehouse itself.",
    "The project sponsor asked that every decision in the steering minutes include the alternatives that were considered and why they were rejected.",
    "Maintenance windows were moved to early Sunday mornings after complaints that the Saturday updates interrupted peak order processing.",
    "Because the data came from three different sources, the analysts spent most of the first week agreeing on common definitions for a shipped order.",
    "The local office has asked for more autonomy over pricing for regional promotions, arguing that central rules slow down their response to competitors.",
]
NEEDLE_SENTENCES = [
    "The escalation reference for the Lisbon case is ESC-20417, which Tanaka logged on 2026-03-14.",
    "The approved contingency budget was 184,500 dollars, pending review of the host 10.42.7.19 by the finance office.",
    "Before the rerun, set MAX_RETRY_LIMIT to 5 in the staging configuration.",
    "The failing call returned E_CONN_RESET_0x7f on the third attempt, as the gateway log recorded.",
]
NEEDLES = ["ESC-20417", "184,500", "10.42.7.19", "MAX_RETRY_LIMIT", "E_CONN_RESET_0x7f", "2026-03-14"]

rng = random.Random(20261118)


def para(k=5, needle=None):
    sentences = [rng.choice(SENTENCES) for _ in range(k)]
    if needle is not None:
        sentences.insert(rng.randint(1, k - 1), needle)
    return " ".join(sentences)


def doc(n_paras, needles=True):
    paragraphs = []
    for i in range(n_paras):
        needle = NEEDLE_SENTENCES[i % len(NEEDLE_SENTENCES)] if needles and i % 7 == 3 else None
        paragraphs.append(para(5, needle))
    return "\n\n".join(paragraphs)


CODE_LINES = [
    "def load_batch(path, limit=100):", "    rows = read_rows(path)", "    if not rows:", "        return []",
    "    out = [normalize(r) for r in rows[:limit]]", "    return out", "class Exporter:", "    retries = 3",
    "    def send(self, payload):", "        resp = self.client.post(self.url, json=payload, timeout=30)",
    "        if resp.status_code == 429:", "            time.sleep(self.backoff * attempt)",
    "    except ConnectionResetError as exc:", "        log.error('reset: %s', exc)", "        raise",
]
ERRORS = [
    "Traceback (most recent call last):",
    '  File "exporter/client.py", line 88, in send',
    "    resp = self.client.post(self.url, json=payload, timeout=30)",
    "ConnectionResetError: [Errno 104] Connection reset by peer",
]


def tool_output(n_lines, error=False):
    lines = []
    for i in range(n_lines):
        name = rng.choice(["exporter/client.py", "exporter/batch.py", "exporter/config.py", "tests/test_export.py"])
        lines.append(f"{name}:{rng.randint(1, 900)}: {rng.choice(CODE_LINES).strip()}")
    if error:
        lines = ERRORS + lines
    return "\n".join(lines)


def msg(role, content, **extra):
    return {"role": role, "content": content, **extra}


def msg_tokens(m):
    text = "\n".join(t for _, t in text_parts(m))
    calls = " ".join(
        (c.get("function") or {}).get("name", "") + " " + (c.get("function") or {}).get("arguments", "")
        for c in (m.get("tool_calls") or []) if isinstance(c, dict)
    )
    return count_tokens(text) + count_tokens(calls)


def total_tokens(messages):
    return sum(msg_tokens(m) for m in messages)


def all_text(messages):
    parts = []
    for m in messages:
        parts.extend(t for _, t in text_parts(m))
        for c in m.get("tool_calls") or []:
            if isinstance(c, dict):
                parts.append((c.get("function") or {}).get("arguments", ""))
    return "\n".join(parts)


TOOLS = [
    {"type": "function", "function": {"name": "grep", "description": "Search the repository for a pattern and return matching lines with file and line number. Use it to locate code before reading files.",
                                      "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a file from the repository and return its contents with line numbers. Large files are truncated.",
                                      "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "start": {"type": "integer"}, "end": {"type": "integer"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "run_tests", "description": "Run the unit test suite for a path and return the summary and failing test output.",
                                      "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
]
SYSTEM = ("You are a senior backend engineer working in the export service repository. Diagnose the problem with the tools, "
          "make the smallest correct change, and explain the root cause in plain language. Never invent file contents.")


def workloads():
    W = {}
    W["W1_short_question"] = {"messages": [msg("user", "How do I reverse a list in Python?")], "needles": [], "code": []}
    W["W2_long_doc_lookup"] = {
        "messages": [msg("system", "You are a support analyst. Answer from the document only."),
                     msg("user", doc(30) + "\n\nWhat was the escalation reference, and who logged it? Answer briefly.")],
        "needles": ["ESC-20417", "Tanaka"], "code": []}
    W["W3_long_doc_summarize"] = {
        "messages": [msg("system", "You are a support analyst."),
                     msg("user", doc(30) + "\n\nSummarize the whole document in five key points.")],
        "needles": ["ESC-20417", "184,500"], "code": []}
    code_body = "\n".join(
        f"def handler_{i}(request, retries={i % 5}):\n    value = request.get('field_{i}')\n    return normalize(value, retries)\n"
        for i in range(40))
    log_body = "\n".join(f"2026-03-14 10:{i:02d}:04 ERROR worker-{i % 3} request req-{i} timed out after 120s" for i in range(40))
    W["W4_code_heavy_review"] = {
        "messages": [msg("system", "You are a code reviewer."),
                     msg("user", "Review this module for correctness bugs and say what to fix first.\n\n```python\n" + code_body
                         + "\n```\n\nThe failing test output is below.\n\n" + log_body)],
        "needles": ["req-17", "worker-2"], "code": []}
    debug_user_1 = ("The nightly export keeps failing after the third retry. Here is what I see in the send path:\n"
                    "        resp = self.client.post(self.url, json=payload, timeout=30)\n"
                    "        if resp.status_code == 429:\n"
                    "            time.sleep(self.backoff * attempt)\n"
                    "The loop body looks right to me, so I suspect the backoff is the problem.")
    debug_user_2 = ("Here is the traceback from the last run, which is the same every night:\n" + "\n".join(ERRORS) +
                    "\nThe batch size in config is MAX_BATCH_ROWS = 500 and the host is 10.42.7.19.")
    debug_user_3 = ("I also changed the call to client.post(url, timeout=30) in the helper, and the error still happens after attempt three. "
                    "Could the retry counter in Exporter.retries be reset somewhere else? The ticket reference is ESC-20417.")
    debug_asst = ("The retries look correct in isolation. Check whether the connection pool is closed between attempts, because a reset "
                  "after the third attempt usually means the server closed an idle keep-alive connection that the client then reused. "
                  "Logging the connection id on each attempt would confirm this quickly and is a safe change to make first.")
    W["W5_debug_session"] = {
        "messages": [msg("system", "You are a senior backend engineer. Be precise about code."),
                     msg("user", debug_user_1), msg("assistant", debug_asst),
                     msg("user", debug_user_2), msg("assistant", debug_asst),
                     msg("user", debug_user_3), msg("assistant", debug_asst),
                     msg("user", "Why does the retry fail on the third attempt? Which line do I change first?")],
        "needles": ["ESC-20417", "10.42.7.19", "MAX_BATCH_ROWS"],
        "code": ["        resp = self.client.post(self.url, json=payload, timeout=30)", "        if resp.status_code == 429:",
                 "            time.sleep(self.backoff * attempt)"]}

    agent = [msg("system", SYSTEM), msg("user", "The nightly export fails after the third retry. Find the cause and fix it.")]
    for i in range(12):
        call_id = f"call_{i}"
        agent.append({"role": "assistant", "content": None, "tool_calls": [{"id": call_id, "type": "function", "function": {
            "name": rng.choice(["grep", "read_file"]), "arguments": json.dumps({"pattern": "post|retries", "path": f"exporter/file_{i}.py"})}}]})
        agent.append(msg("tool", tool_output(45, error=(i == 4)), tool_call_id=call_id))
        if i % 3 == 2:
            agent.append(msg("assistant", "The output points at the send path. I will read the surrounding lines next to confirm the retry logic."))
    agent.append(msg("user", "Go ahead and make the fix, then run the tests."))
    W["W6_agentic_tool_loop"] = {"messages": agent, "tools": TOOLS, "needles": [], "code": []}

    chat = [msg("system", "You are a helpful analyst.")]
    for i in range(30):
        chat.append(msg("user", "Question " + str(i) + ": " + rng.choice(SENTENCES)))
        chat.append(msg("assistant", para(6)))
    W["W7_long_chat"] = {"messages": chat + [msg("user", "Summarise what we decided about the vendor contract.")], "needles": [], "code": []}

    big = [msg("system", "You are a support analyst.")]
    big.append(msg("user", doc(230, needles=True) + "\n\nWhat was the escalation reference? Answer briefly."))
    W["W8_large_40k_prose"] = {"messages": big, "needles": ["ESC-20417"], "code": []}
    return W


async def run(cb_ce, cb_pc, messages, tools=None, ce=True, pc=True):
    data = {"model": "gpt-4o", "messages": copy.deepcopy(messages), "metadata": {}}
    if tools:
        data["tools"] = tools
    started = time.perf_counter()
    if ce:
        data = await cb_ce.async_pre_call_hook(None, None, data, "acompletion")
    if pc:
        data = await cb_pc.async_pre_call_hook(None, None, data, "acompletion")
    wall = round((time.perf_counter() - started) * 1000, 1)
    return data, wall


async def main():
    ce = ContextEngineeringCallback()
    pc = PromptCompressionCallback()
    W = workloads()
    results = []
    for name, spec in W.items():
        before = total_tokens(spec["messages"])
        tools = spec.get("tools")
        ce_only, ce_ms = await run(ce, pc, spec["messages"], tools, ce=True, pc=False)
        pc_only, pc_ms = await run(ce, pc, spec["messages"], tools, ce=False, pc=True)
        chain, chain_ms = await run(ce, pc, spec["messages"], tools, ce=True, pc=True)
        ce_meta = chain["metadata"].get("context_engineering", {})
        pc_meta = chain["metadata"].get("prompt_compression", {})
        ce_alone_meta = ce_only["metadata"].get("context_engineering", {})
        pc_alone_meta = pc_only["metadata"].get("prompt_compression", {})
        after_chain = total_tokens(chain["messages"])
        final_text = all_text(chain["messages"])
        needles_total = len(spec["needles"])
        needles_kept = sum(1 for n in spec["needles"] if n in final_text)
        code_total = len(spec["code"])
        code_kept = sum(1 for line in spec["code"] if line in final_text)
        results.append({
            "workload": name,
            "tokens_before": before,
            "tokens_after_ce_only": total_tokens(ce_only["messages"]),
            "tokens_after_pc_only": total_tokens(pc_only["messages"]),
            "tokens_after_chain": after_chain,
            "reduction_chain_pct": round(100 * (before - after_chain) / before, 1) if before else 0.0,
            "reduction_ce_only_pct": round(100 * (before - total_tokens(ce_only["messages"])) / before, 1) if before else 0.0,
            "reduction_pc_only_pct": round(100 * (before - total_tokens(pc_only["messages"])) / before, 1) if before else 0.0,
            "ce_status": ce_alone_meta.get("status"), "ce_saved_by_technique": ce_meta.get("saved_by_technique"),
            "ce_masked": ce_meta.get("masked") and len(ce_meta.get("masked")),
            "pc_status_alone": pc_alone_meta.get("status"), "pc_reason_alone": pc_alone_meta.get("reason") or pc_alone_meta.get("error"),
            "pc_status_chain": pc_meta.get("status"), "pc_category": pc_meta.get("category"),
            "pc_intent": pc_meta.get("intent"), "pc_compress_calls": pc_meta.get("compress_calls"),
            "pc_compress_stopped": pc_meta.get("compress_stopped"), "pc_kept": pc_meta.get("kept"),
            "pc_routes_action_counts": None,
            "wall_ms_ce_only": ce_ms, "wall_ms_pc_only": pc_ms, "wall_ms_chain": chain_ms,
            "pc_elapsed_ms_reported": pc_meta.get("elapsed_ms"),
            "needles_kept": f"{needles_kept}/{needles_total}", "code_lines_kept": f"{code_kept}/{code_total}",
        })
        print(f"{name}: before={before} chain={after_chain} ({results[-1]['reduction_chain_pct']}%) "
              f"ce={results[-1]['reduction_ce_only_pct']}% pc={results[-1]['reduction_pc_only_pct']}% "
              f"pc_status={results[-1]['pc_status_chain']} stop={results[-1]['pc_compress_stopped']} "
              f"calls={results[-1]['pc_compress_calls']} wall={chain_ms}ms needles={results[-1]['needles_kept']} "
              f"code={results[-1]['code_lines_kept']}", flush=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)
    print("wrote", OUT)


if __name__ == "__main__":
    asyncio.run(main())
