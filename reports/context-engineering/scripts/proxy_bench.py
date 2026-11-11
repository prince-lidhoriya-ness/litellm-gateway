"""Through the running proxy (bench_config.yaml) in front of the echo provider: end-to-end latency, throughput, error
rate and what reached the provider, for the four configurations.

    .venv-compression/Scripts/python reports/context-engineering/scripts/proxy_bench.py --base http://127.0.0.1:4100

Passes: "first" (concurrency 1, the first time the proxy sees each item; caches are shared across configurations, run in
the order baseline, compression, context_engineering, combined), "repeat" (the same again, warm), then "c8" (concurrency
8, warm). Within a pass the four configurations run one after another over the
whole dataset. Writes raw/proxy.jsonl and raw/proxy_runs.json.
"""

import argparse
import concurrent.futures
import json
import time
import urllib.error
import urllib.request

from bench_lib import CONFIGS, MAX_TOKENS, RAW, answer_in_context, key_strings_kept, load_items, write_jsonl

from context_engineering.tokens import messages_tokens


def post(base, key, body, timeout=600):
    request = urllib.request.Request(f"{base}/v1/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read())
        return payload, (time.perf_counter() - started) * 1000, None
    except urllib.error.HTTPError as exc:
        return None, (time.perf_counter() - started) * 1000, f"http_{exc.code}"
    except Exception as exc:
        return None, (time.perf_counter() - started) * 1000, type(exc).__name__


def one(base, key, model, item, config):
    body = {"model": model, "messages": item["messages"], "max_tokens": MAX_TOKENS, "temperature": 0,
            "metadata": dict(CONFIGS[config])}
    payload, ms, error = post(base, key, body)
    row = {"item": item["id"], "family": item["family"], "config": config, "latency_ms": round(ms, 1), "error": error,
           "tokens_original": messages_tokens(item["messages"])}
    if payload is not None:
        try:
            received = json.loads(payload["choices"][0]["message"]["content"])["received_messages"]
        except Exception:
            received = None
        if received is not None:
            row.update({"tokens_forwarded": messages_tokens(received), "messages_forwarded": len(received),
                        "key_strings_kept": key_strings_kept(item, received),
                        "answer_in_context": answer_in_context(item, received)})
        row["usage"] = payload.get("usage")
    return row


def run_pass(base, key, model, items, name, concurrency, order=None):
    rows, runs = [], []
    for config in order or list(CONFIGS):
        started = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            batch = list(pool.map(lambda it: one(base, key, model, it, config), items))
        wall = time.perf_counter() - started
        for row in batch:
            row.update({"pass": name, "concurrency": concurrency})
        rows += batch
        errors = sum(1 for r in batch if r["error"])
        runs.append({"pass": name, "config": config, "concurrency": concurrency, "requests": len(batch),
                     "errors": errors, "wall_s": round(wall, 2), "rps": round(len(batch) / wall, 2)})
        print(f"{name} c={concurrency} {config}: {len(batch)} req in {wall:.1f}s ({len(batch) / wall:.2f} rps), "
              f"errors={errors}", flush=True)
    return rows, runs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:4100")
    parser.add_argument("--key", default="sk-bench-local")
    parser.add_argument("--model", default="bench-echo")
    parser.add_argument("--cold-reverse", action="store_true",
                        help="only a first pass, combined -> context_engineering -> compression -> baseline, on a "
                             "freshly started proxy: the cold figures for the configurations that ran later above")
    args = parser.parse_args()
    items = load_items()
    for _ in range(120):                      # wait for the proxy
        try:
            urllib.request.urlopen(f"{args.base}/health/liveliness", timeout=2)
            break
        except Exception:
            time.sleep(2)
    # Two throwaway requests so imports, model loads and connection pools are not in the cold pass.
    for item in items[:2]:
        one(args.base, args.key, args.model, item, "combined")
    rows, runs = [], []
    if args.cold_reverse:
        rows, runs = run_pass(args.base, args.key, args.model, items, "first_reversed", 1, list(CONFIGS)[::-1])
        write_jsonl(RAW / "proxy_reversed.jsonl", rows)
        (RAW / "proxy_reversed_runs.json").write_text(json.dumps(runs, indent=1), encoding="utf-8")
        return
    for name, concurrency in (("first", 1), ("repeat", 1), ("c8", 8)):
        r, s = run_pass(args.base, args.key, args.model, items, name, concurrency)
        rows += r
        runs += s
    write_jsonl(RAW / "proxy.jsonl", rows)
    (RAW / "proxy_runs.json").write_text(json.dumps(runs, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
