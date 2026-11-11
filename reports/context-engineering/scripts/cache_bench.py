"""Prefix reuse between consecutive turns, per configuration: what a provider's prompt cache could reuse, and what
Ollama's KV-prefix cache actually reuses on this machine.

    .venv-compression/Scripts/python reports/context-engineering/scripts/cache_bench.py --base http://127.0.0.1:4100

For each sequence item, turn N is the item itself and turn N+1 appends an assistant reply and a new question. Both
turns go through the proxy with the echo provider (bench-echo) to capture exactly what each configuration forwards.
  common_prefix_tokens   tokens of the leading messages that are byte-identical in the two forwarded requests (what
                         a provider prefix cache could reuse, at message granularity)
Then both forwarded requests are replayed, in order, straight to Ollama (/api/chat, num_ctx 8192, 1 output token)
with a per-configuration run tag, and Ollama's own prompt_eval_duration is recorded for turn N (cold) and N+1.
Writes raw/cache.jsonl.
"""

import argparse
import copy
import json
import time
import urllib.request
import uuid

from bench_lib import CONFIGS, MAX_TOKENS, RAW, common_prefix_tokens, load_items, write_jsonl
from proxy_bench import post

from context_engineering.tokens import message_tokens

SEQUENCES = ["long_chat-000", "long_chat-001", "agent_tools-000"]
FOLLOW_UP = [{"role": "assistant", "content": "Answer: Noted, I will keep that in mind."},
             {"role": "user", "content": "Thanks. In one sentence, what should we check next?"}]


def forwarded(base, key, messages, config):
    body = {"model": "bench-echo", "messages": messages, "max_tokens": MAX_TOKENS, "metadata": dict(CONFIGS[config])}
    payload, _, error = post(base, key, body)
    if error:
        raise RuntimeError(error)
    return json.loads(payload["choices"][0]["message"]["content"])["received_messages"]


def for_ollama(messages: list, tag: str) -> list:
    out = []
    for i, m in enumerate(copy.deepcopy(messages)):
        m["content"] = m.get("content") or ""
        if isinstance(m["content"], list):
            m["content"] = "\n".join(p.get("text", "") for p in m["content"] if isinstance(p, dict))
        if i == 0:
            m["content"] = f"[run:{tag}] " + m["content"]
        for call in m.get("tool_calls") or []:
            arguments = call.get("function", {}).get("arguments")
            if isinstance(arguments, str):
                try:
                    call["function"]["arguments"] = json.loads(arguments)
                except ValueError:
                    call["function"]["arguments"] = {}
        out.append(m)
    return out


def ollama(messages: list) -> dict:
    body = {"model": "llama3.2:3b", "messages": messages, "stream": False,
            "options": {"num_ctx": 8192, "temperature": 0, "num_predict": 1}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    result = json.loads(urllib.request.urlopen(request, timeout=1800).read())
    return {"wall_s": round(time.perf_counter() - started, 2), "prompt_eval_count": result.get("prompt_eval_count"),
            "prompt_eval_s": round((result.get("prompt_eval_duration") or 0) / 1e9, 2)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:4100")
    parser.add_argument("--key", default="sk-bench-local")
    parser.add_argument("--no-ollama", action="store_true")
    args = parser.parse_args()
    rows = []
    for item in load_items(ids=set(SEQUENCES)):
        turn_n = item["messages"]
        turn_n1 = item["messages"] + FOLLOW_UP
        for config in CONFIGS:
            a = forwarded(args.base, args.key, turn_n, config)
            b = forwarded(args.base, args.key, turn_n1, config)
            row = {"item": item["id"], "family": item["family"], "config": config,
                   "tokens_n": sum(map(message_tokens, a)), "tokens_n1": sum(map(message_tokens, b)),
                   "common_prefix_tokens": common_prefix_tokens(a, b, message_tokens)}
            if not args.no_ollama:
                tag = uuid.uuid4().hex[:8]
                row["ollama_n"] = ollama(for_ollama(a, tag))
                row["ollama_n1"] = ollama(for_ollama(b, tag))
            rows.append(row)
            print(json.dumps(row), flush=True)
    write_jsonl(RAW / "cache.jsonl", rows)


if __name__ == "__main__":
    main()
