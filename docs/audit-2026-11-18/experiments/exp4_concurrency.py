"""Experiment 4: concurrency and timeouts on ONE worker (one callback instance, as in production per worker).

Part A  prompt_compression: N simultaneous cold requests (about 1,450-token prose each), then a second wave launched immediately,
        without waiting for orphaned pipelines to finish. Records status, stop reason, hook latency, and how long the
        worker keeps running pipelines after the hook has already returned (in_flight drain time).
Part B  context_engineering: one request of growing agentic size (tool outputs), timing vs the 2 s stage timeout.
"""
import asyncio
import json
import os
import random
import sys
import time
from collections import Counter

SP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SP)
import exp1_workloads as e  # noqa: E402

from prompt_compression.prompt_compression_callback import PromptCompressionCallback  # noqa: E402
from context_engineering.callback import ContextEngineeringCallback  # noqa: E402


def doc_for(seed, paragraphs=12):
    rng = random.Random(seed)
    out = []
    for _ in range(paragraphs):
        out.append(" ".join(rng.choice(e.SENTENCES) for _ in range(5)))
    return "\n\n".join(out)


async def one(pc, text, tag):
    data = {"model": "gpt-4o", "messages": [{"role": "user", "content": text + "\n\nWhat changed in the budget?"}],
            "metadata": {}}
    t = time.perf_counter()
    out = await pc.async_pre_call_hook(None, None, data, "acompletion")
    wall = round((time.perf_counter() - t) * 1000, 1)
    m = out["metadata"].get("prompt_compression", {})
    return {"tag": tag, "status": m.get("status"), "reason": m.get("reason") or m.get("error"),
            "stop": m.get("compress_stopped"), "calls": sum((x.get("segments") or {}).get("compress_calls", 0)
                                                           for x in m.get("messages", []) or []),
            "elapsed_ms_reported": m.get("elapsed_ms"), "wall_ms": wall}


async def wave(pc, n, base_seed, tag):
    started = time.perf_counter()
    results = await asyncio.gather(*[one(pc, doc_for(base_seed + i), f"{tag}-{i}") for i in range(n)])
    batch_s = round(time.perf_counter() - started, 2)
    in_flight_at_return = pc.in_flight
    drain_started = time.perf_counter()
    while pc.in_flight > 0 and time.perf_counter() - drain_started < 180:
        await asyncio.sleep(0.2)
    drain_s = round(time.perf_counter() - drain_started, 2)
    return results, batch_s, in_flight_at_return, drain_s


def report(label, results, batch_s, in_flight_at_return, drain_s):
    statuses = Counter(f"{r['status']}/{r['reason'] or r['stop'] or '-'}" for r in results)
    walls = sorted(r["wall_ms"] for r in results)
    print(f"== {label}: n={len(results)} batch_wall={batch_s}s in_flight_at_return={in_flight_at_return} "
          f"orphan_drain_after_return={drain_s}s", flush=True)
    print(f"   outcomes: {dict(statuses)}", flush=True)
    print(f"   hook wall ms: min={walls[0]} median={walls[len(walls) // 2]} max={walls[-1]}", flush=True)
    for r in results:
        print(f"     {r['tag']:>10} status={r['status']} reason={r['reason']} stop={r['stop']} calls={r['calls']} "
              f"wall={r['wall_ms']}", flush=True)


async def part_a(out):
    pc = PromptCompressionCallback()
    # single request baseline on an idle worker
    single = await one(pc, doc_for(500), "single")
    print("baseline single:", single, flush=True)
    out["baseline_single"] = single
    r1 = await wave(pc, 8, 1000, "w1")
    report("wave1 N=8 (cold, simultaneous)", *r1)
    out["wave1"] = {"results": r1[0], "batch_s": r1[1], "in_flight_at_return": r1[2], "drain_s": r1[3]}
    # second wave with no wait for the orphaned pipelines of wave 1
    r2 = await wave(pc, 4, 2000, "w2")
    report("wave2 N=4 (launched right after wave1, cold)", *r2)
    out["wave2"] = {"results": r2[0], "batch_s": r2[1], "in_flight_at_return": r2[2], "drain_s": r2[3]}


def agentic_messages(target_tokens):
    msgs = [e.msg("system", e.SYSTEM), e.msg("user", "Find the cause of the nightly export failure and fix it.")]
    total = e.total_tokens(msgs)
    i = 0
    while total < target_tokens:
        call_id = f"call_{i}"
        msgs.append({"role": "assistant", "content": None, "tool_calls": [{"id": call_id, "type": "function", "function": {
            "name": "grep", "arguments": json.dumps({"pattern": f"retries|post_{i % 4}", "path": "exporter"})}}]})
        msgs.append(e.msg("tool", e.tool_output(45), tool_call_id=call_id))
        total = e.total_tokens(msgs)
        i += 1
    msgs.append(e.msg("user", "Go ahead and make the fix, then run the tests."))
    return msgs


async def part_b(out):
    ce = ContextEngineeringCallback()
    rows = []
    for target in (5000, 20000, 60000, 120000):
        msgs = agentic_messages(target)
        before = e.total_tokens(msgs)
        data = {"model": "gpt-4o", "messages": msgs, "metadata": {}, "tools": e.TOOLS}
        t = time.perf_counter()
        res = await ce.async_pre_call_hook(None, None, data, "acompletion")
        wall = round((time.perf_counter() - t) * 1000, 1)
        m = res["metadata"].get("context_engineering", {})
        row = {"target": target, "tokens_before": before, "status": m.get("status"), "error": m.get("error"),
               "reason": m.get("reason"), "elapsed_ms_reported": m.get("elapsed_ms"), "wall_ms": wall,
               "tokens_after": m.get("tokens_after"), "masked": len(m.get("masked") or [])}
        rows.append(row)
        print("CE", row, flush=True)
    out["ce_timing"] = rows


async def part_c(out, n=12, target=20000):
    """Concurrent context-engineering requests on one worker: default executor, 2 s stage timeout, no admission control."""
    ce = ContextEngineeringCallback()
    reqs = [agentic_messages(target) for _ in range(n)]

    async def one_ce(msgs, i):
        data = {"model": "gpt-4o", "messages": msgs, "metadata": {}, "tools": e.TOOLS}
        t = time.perf_counter()
        res = await ce.async_pre_call_hook(None, None, data, "acompletion")
        wall = round((time.perf_counter() - t) * 1000, 1)
        m = res["metadata"].get("context_engineering", {})
        return {"i": i, "status": m.get("status"), "error": m.get("error"), "wall_ms": wall}

    started = time.perf_counter()
    rows = await asyncio.gather(*[one_ce(m, i) for i, m in enumerate(reqs)])
    batch = round(time.perf_counter() - started, 2)
    statuses = Counter(f"{r['status']}/{(r['error'] or '-').split(':')[0]}" for r in rows)
    walls = sorted(r["wall_ms"] for r in rows)
    print(f"== part C: CE n={n} target={target} batch_wall={batch}s outcomes={dict(statuses)} "
          f"wall_ms min={walls[0]} median={walls[len(walls) // 2]} max={walls[-1]}", flush=True)
    out["ce_concurrent"] = {"n": n, "target": target, "batch_s": batch, "outcomes": dict(statuses), "rows": rows}


async def main():
    out = {}
    await part_a(out)
    await part_b(out)
    await part_c(out)
    with open(os.path.join(SP, "exp4_results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)


if __name__ == "__main__":
    asyncio.run(main())
