"""Experiment 3: multi-turn behaviour through the real hooks, one worker's state carried across the conversation.

For every request k of a growing conversation the client sends its full history (as real clients do). We record:
  * tokens in / out and per-stage reduction (cl100k estimate)
  * prefix reuse: the share of the previous SENT request that is still a byte-identical message prefix of this
    SENT request (message granularity, a lower bound on what a token-level provider cache would reuse)
  * hook latency split into classify / compress, compress calls, cache hits, deadline stops
Variants: chain (CE then PC), pc_only, ce_only. Each variant gets fresh callback instances (fresh caches).
"""
import asyncio
import copy
import json
import os
import random
import sys
import time

SP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SP)
import exp1_workloads as e  # noqa: E402  (sets env, puts the gateway on sys.path, seeds its own generators)

from prompt_compression.prompt_compression_callback import PromptCompressionCallback  # noqa: E402
from context_engineering.callback import ContextEngineeringCallback  # noqa: E402


def build_chat(turns, seed):
    rng = random.Random(seed)
    msgs = [e.msg("system", "You are a helpful analyst who answers in clear prose.")]
    for i in range(turns):
        question = f"Question {i}: " + rng.choice(e.SENTENCES) + " " + rng.choice(e.SENTENCES)
        msgs.append(e.msg("user", question))
        msgs.append(e.msg("assistant", e.para(6)))
    return msgs


def build_agent(cycles, seed):
    rng = random.Random(seed)
    msgs = [e.msg("system", e.SYSTEM), e.msg("user", "The nightly export fails after the third retry. Find the cause and fix it.")]
    for i in range(cycles):
        call_id = f"call_{i}"
        msgs.append({"role": "assistant", "content": None, "tool_calls": [{"id": call_id, "type": "function", "function": {
            "name": "grep", "arguments": json.dumps({"pattern": f"retries|post_{i % 4}", "path": "exporter"})}}]})
        msgs.append(e.msg("tool", e.tool_output(45, error=(i == 4)), tool_call_id=call_id))
        if i % 3 == 2:
            msgs.append(e.msg("assistant", "The output points at the send path; I will read the surrounding lines to confirm."))
    return msgs


def request_points(msgs, kind):
    """Indexes k where the client's request is msgs[:k] (the request ends with a user or tool message)."""
    points = []
    for k in range(1, len(msgs) + 1):
        if msgs[k - 1].get("role") in ("user", "tool"):
            points.append(k)
    return points


def reuse(prev_sent, cur_sent):
    n = 0
    for a, b in zip(prev_sent, cur_sent):
        if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
            break
        n += 1
    return e.total_tokens(prev_sent[:n]), e.total_tokens(prev_sent), n


async def simulate(label, full, tools, use_ce, use_pc):
    ce = ContextEngineeringCallback() if use_ce else None
    pc = PromptCompressionCallback() if use_pc else None
    prev = None
    rows = []
    for k in request_points(full, label):
        raw = copy.deepcopy(full[:k])
        data = {"model": "gpt-4o", "messages": raw, "metadata": {}}
        if tools:
            data["tools"] = tools
        t0 = time.perf_counter()
        if ce is not None:
            data = await ce.async_pre_call_hook(None, None, data, "acompletion")
        if pc is not None:
            data = await pc.async_pre_call_hook(None, None, data, "acompletion")
        wall = (time.perf_counter() - t0) * 1000
        sent = data["messages"]
        pcm = data["metadata"].get("prompt_compression", {}) if use_pc else {}
        cem = data["metadata"].get("context_engineering", {}) if use_ce else {}
        entries = pcm.get("messages", []) or []
        classify_ms = round(sum(x.get("classify_ms", 0) or 0 for x in entries), 1)
        compress_ms = round(sum(x.get("compress_ms", 0) or 0 for x in entries), 1)
        cache_hits = sum((x.get("segments") or {}).get("compress_cache_hits", 0) for x in entries)
        calls = sum((x.get("segments") or {}).get("compress_calls", 0) for x in entries)
        in_tok = e.total_tokens(raw)
        out_tok = e.total_tokens(sent)
        if prev is not None:
            reusable, prev_total, n_same = reuse(prev, sent)
            reuse_pct = round(100 * reusable / prev_total, 1) if prev_total else 100.0
            first_change = n_same
        else:
            reuse_pct, first_change = None, None
        rows.append({
            "k": k, "in_tokens": in_tok, "sent_tokens": out_tok,
            "reduction_pct": round(100 * (in_tok - out_tok) / in_tok, 1),
            "prefix_reuse_pct_vs_prev": reuse_pct, "first_changed_message": first_change,
            "ce_status": cem.get("status"), "ce_masked": len(cem.get("masked") or []) if cem else None,
            "ce_breakpoints": bool(data.get("cache_control_injection_points")),
            "pc_status": pcm.get("status"), "pc_stop": pcm.get("compress_stopped"),
            "pc_calls": calls, "pc_cache_hits": cache_hits, "classify_ms": classify_ms, "compress_ms": compress_ms,
            "wall_ms": round(wall, 1),
        })
        prev = sent
    return rows


def summarize(label, rows):
    reuse_vals = [r["prefix_reuse_pct_vs_prev"] for r in rows if r["prefix_reuse_pct_vs_prev"] is not None]
    breaks = [r for r in rows if r["prefix_reuse_pct_vs_prev"] is not None and r["prefix_reuse_pct_vs_prev"] < 95.0]
    walls = [r["wall_ms"] for r in rows]
    stops = sum(1 for r in rows if r["pc_stop"] == "deadline")
    print(f"--- {label}: requests={len(rows)} mean_prefix_reuse={round(sum(reuse_vals) / max(1, len(reuse_vals)), 1)}% "
          f"min={min(reuse_vals) if reuse_vals else None}% reuse<95%: {len(breaks)} turns "
          f"deadline_stops={stops} wall_ms first={walls[0]} median={sorted(walls)[len(walls) // 2]} max={max(walls)} "
          f"last={walls[-1]}", flush=True)
    for r in rows:
        print(f"  k={r['k']:>3} in={r['in_tokens']:>6} sent={r['sent_tokens']:>6} red={r['reduction_pct']:>5}% "
              f"reuse={r['prefix_reuse_pct_vs_prev']}% firstchg={r['first_changed_message']} "
              f"pc={r['pc_status']}/{r['pc_stop']} calls={r['pc_calls']} hits={r['pc_cache_hits']} "
              f"cls={r['classify_ms']} cmp={r['compress_ms']} ce={r['ce_status']} masked={r['ce_masked']} "
              f"wall={r['wall_ms']}", flush=True)


async def main():
    chat = build_chat(24, seed=11)
    agent = build_agent(20, seed=12)
    out = {}
    for label, full, tools in (("chat", chat, None), ("agent", agent, e.TOOLS)):
        for variant, use_ce, use_pc in (("chain", True, True), ("pc_only", False, True), ("ce_only", True, False)):
            rows = await simulate(f"{label}:{variant}", full, tools, use_ce, use_pc)
            out[f"{label}:{variant}"] = rows
            summarize(f"{label}:{variant}", rows)
    with open(os.path.join(SP, "exp3_results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)


if __name__ == "__main__":
    asyncio.run(main())
