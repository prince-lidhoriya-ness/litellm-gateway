"""Functional validation against a running proxy (bench_config.yaml, echo provider). One check set per proxy start:

    validate_live.py --expect full        CONTEXT_COMPACTION/JIT on (the benchmark profile)
    validate_live.py --expect disabled    CONTEXT_ENGINEERING_ENABLED=false
    validate_live.py --expect nomask      OBSERVATION_MASKING_ENABLED=false (compaction still on)
    validate_live.py --expect shadow      CONTEXT_ENGINEERING_MODE=shadow
    validate_live.py --expect timeout     CONTEXT_ENGINEERING_TIMEOUT_S=0.0001 (fail open)

Prints one PASS/FAIL line per check and appends them to raw/validation.jsonl.
"""

import argparse
import json
import time
import urllib.request

from bench_lib import CONFIGS, RAW, context_text, load_items
from proxy_bench import post

from context_engineering.tokens import messages_tokens

STUB = "[gateway: observation "
SUMMARY = "[gateway: earlier conversation compacted"


def forwarded(base, key, messages, config="combined"):
    payload, ms, error = post(base, key, {"model": "bench-echo", "messages": messages, "max_tokens": 16,
                                           "metadata": dict(CONFIGS[config])})
    if error:
        return None, error
    return json.loads(payload["choices"][0]["message"]["content"])["received_messages"], None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:4100")
    parser.add_argument("--key", default="sk-bench-local")
    parser.add_argument("--expect", required=True, choices=["full", "disabled", "nomask", "shadow", "timeout"])
    args = parser.parse_args()
    agent = load_items(ids={"agent_tools-000"})[0]
    chat = load_items(ids={"long_chat-000"})[0]
    doc = load_items(ids={"doc_qa-000"})[0]
    results = []

    def check(name, ok, detail=""):
        results.append({"profile": args.expect, "check": name, "ok": bool(ok), "detail": detail,
                        "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"{'PASS' if ok else 'FAIL'}  [{args.expect}] {name}  {detail}", flush=True)

    with urllib.request.urlopen(f"{args.base}/health/liveliness", timeout=10) as r:
        check("gateway starts and answers /health/liveliness", r.status == 200)

    a, err = forwarded(args.base, args.key, agent["messages"])
    c, err2 = forwarded(args.base, args.key, chat["messages"])
    stubs = [m for m in (a or []) if m.get("role") == "tool" and str(m.get("content")).startswith(STUB)]
    summaries = [m for m in (c or []) if str(m.get("content")).startswith(SUMMARY)]
    check("requests succeed", a is not None and c is not None, f"{err or ''} {err2 or ''}".strip())

    if args.expect == "full":
        d, _ = forwarded(args.base, args.key, doc["messages"], "compression")
        check("existing compression works (doc QA, compression only)",
              d is not None and messages_tokens(d) < messages_tokens(doc["messages"]),
              f"{messages_tokens(doc['messages'])} -> {messages_tokens(d or [])} tokens")
        ce, _ = forwarded(args.base, args.key, agent["messages"], "context_engineering")
        check("context engineering works alone (agent, CE only)",
              any(str(m.get("content")).startswith(STUB) for m in ce or []),
              f"{messages_tokens(agent['messages'])} -> {messages_tokens(ce or [])} tokens")
        check("both layers together: old tool outputs masked", len(stubs) >= 1, f"{len(stubs)} stubs")
        check("both layers together: older turns compacted", len(summaries) == 1, f"{len(summaries)} summary")
        check("tool-call ids and order intact",
              [m.get("tool_call_id") for m in a if m.get("role") == "tool"] ==
              [m.get("tool_call_id") for m in agent["messages"] if m.get("role") == "tool"])
        check("latest question unchanged", a[-1] == agent["messages"][-1] and c[-1] == chat["messages"][-1])
        check("structured payloads kept (key strings)", all(k in context_text(c) for k in chat["key_strings"]) or
              any(r.get("action") for r in []), "codename present in compacted chat context"
              if all(k in context_text(c) for k in chat["key_strings"]) else "codename not in context")
        ref = stubs[0]["content"].split(STUB, 1)[1].split()[0] if stubs else ""
        restored, _ = forwarded(args.base, args.key,
                                agent["messages"] + [{"role": "assistant", "content": f"Answer: I need {ref} in full."},
                                                     {"role": "user", "content": "Go ahead."}])
        index = next((i for i, m in enumerate(a) if str(m.get("content")).startswith(STUB + ref)), None)
        check("masked original recovered when its ref is mentioned",
              index is not None and restored is not None and restored[index] == agent["messages"][index], ref)
        base, _ = forwarded(args.base, args.key, agent["messages"], "baseline")
        check("baseline (both opt-outs) forwards the original", base == agent["messages"])
        with urllib.request.urlopen(f"{args.base}/metrics", timeout=10) as r:
            text = r.read().decode()
        wanted = ["context_engine_requests_total", "context_engine_tokens_saved_total", "context_engine_masked_total",
                  "context_engine_compactions_total", "context_engine_duration_seconds",
                  "gateway_optimization_tokens_total", "prompt_pipeline_tokens_saved_total"]
        missing = [w for w in wanted if w not in text]
        check("metrics exposed on /metrics", not missing, f"missing {missing}" if missing else f"{len(wanted)} series")
    elif args.expect in ("disabled", "shadow", "timeout"):
        check(f"{args.expect}: agent request forwarded with no CE change", not stubs, f"{len(stubs)} stubs")
        check(f"{args.expect}: chat forwarded with no compaction", not summaries)
    elif args.expect == "nomask":
        check("OBSERVATION_MASKING_ENABLED=false: no stubs", not stubs, f"{len(stubs)} stubs")
        check("OBSERVATION_MASKING_ENABLED=false: compaction still works", len(summaries) == 1)

    path = RAW / "validation.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        for row in results:
            handle.write(json.dumps(row) + "\n")
    raise SystemExit(0 if all(r["ok"] for r in results) else 1)


if __name__ == "__main__":
    main()
