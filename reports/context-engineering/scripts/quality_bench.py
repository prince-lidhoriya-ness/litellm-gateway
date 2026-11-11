"""Answer quality with a real model: local Ollama llama3.2:3b through the proxy (bench_config.yaml, model bench-llama),
the same items in the four configurations.

    .venv-compression/Scripts/python reports/context-engineering/scripts/quality_bench.py --base http://127.0.0.1:4100

Every request gets a fresh 8-hex run tag at the start of its system message, so Ollama cannot reuse a KV prefix
from another configuration (these are cold-cache latencies; prefix reuse is measured on its own in cache_bench.py).
The configuration order rotates per item. Resumable: rows already in raw/quality.jsonl are skipped.
Scores: correct (an expected answer string occurs in the reply), completeness (share of the required strings),
instruction following (multi-turn items: the reply starts with "Answer:"), and the context checks of bench_lib.
"""

import argparse
import copy
import json
import time
import uuid

from bench_lib import CONFIGS, MAX_TOKENS, RAW, completeness, correct, follows_instruction, load_items, read_jsonl
from proxy_bench import post

from context_engineering.tokens import messages_tokens

# 16 items: about 90 minutes of CPU inference for the four configurations on this machine (Ollama evaluates about
# 29 prompt tokens/s here). long_chat 0-5 alternate old/recent facts; agent_tools 0-5 cover old_ref, old_unref, recent.
SUBSET = (["long_chat-%03d" % i for i in range(6)] + ["agent_tools-%03d" % i for i in range(6)]
          + ["agent_debug-000", "structured_chat-000", "doc_qa-000", "short_chat-000"])


def tagged(messages: list) -> list:
    messages = copy.deepcopy(messages)
    tag = f"[run:{uuid.uuid4().hex[:8]}] "
    if messages and messages[0]["role"] == "system":
        messages[0]["content"] = tag + messages[0]["content"]
    else:
        messages.insert(0, {"role": "system", "content": tag.strip()})
    return messages


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:4100")
    parser.add_argument("--key", default="sk-bench-local")
    parser.add_argument("--model", default="bench-llama")
    args = parser.parse_args()
    out = RAW / "quality.jsonl"
    done = {(r["item"], r["config"]) for r in read_jsonl(out)}
    items = load_items(ids=set(SUBSET))
    configs = list(CONFIGS)
    for n, item in enumerate(items):
        order = configs[n % 4:] + configs[:n % 4]
        for config in order:
            if (item["id"], config) in done:
                continue
            messages = tagged(item["messages"])
            body = {"model": args.model, "messages": messages, "max_tokens": MAX_TOKENS, "temperature": 0,
                    "seed": 7, "metadata": dict(CONFIGS[config])}
            payload, ms, error = post(args.base, args.key, body, timeout=1200)
            answer = ""
            usage = None
            if payload is not None:
                answer = payload["choices"][0]["message"].get("content") or ""
                usage = payload.get("usage")
            row = {"item": item["id"], "family": item["family"], "variant": item.get("variant", ""), "config": config,
                   "latency_ms": round(ms, 1), "error": error, "answer": answer, "usage": usage,
                   "tokens_original": messages_tokens(item["messages"]),
                   "correct": correct(item, answer) if not error else None,
                   "completeness": completeness(item, answer) if not error else None,
                   "instruction": follows_instruction(item, answer) if not error else None,
                   "at": time.strftime("%Y-%m-%d %H:%M:%S")}
            with out.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"{item['id']} {config}: {ms / 1000:.1f}s correct={row['correct']} prompt_tokens="
                  f"{(usage or {}).get('prompt_tokens')} error={error}", flush=True)


if __name__ == "__main__":
    main()
