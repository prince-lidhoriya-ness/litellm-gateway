"""Client-side latency of N sequential requests, for telemetry-on vs telemetry-off comparison.

Targets the `obs-mock` model (prompt_compression/dev/mock_openai_server.py on the host, port 4010),
so provider time is a few ms and the measured time is proxy + prompt pipeline + telemetry.
(A client-sent `mock_response` is not honoured by the proxy; it still calls the provider.) Run once per configuration (see monitoring/README.md):

    .venv-compression/Scripts/python monitoring/scripts/measure_overhead.py --label on  -n 60
    .venv-compression/Scripts/python monitoring/scripts/measure_overhead.py --label off -n 60
    .venv-compression/Scripts/python monitoring/scripts/measure_overhead.py --compare
"""

import argparse
import json
import statistics
import time
import urllib.request
from pathlib import Path

GATEWAY_DIR = Path(__file__).resolve().parents[2]
RESULTS = GATEWAY_DIR / "monitoring" / "results"
# Two request shapes: a compressed one (classifier cache hit after the first, LLMLingua runs every time)
# and an uncompressed critical one.
PROMPTS = [
    "Hi there! Hope you're having a great day and a lovely week so far. Thanks so much again for all the help "
    "last time, really appreciate it, you're the best! Anyway, as I said before, just saying hello again, nothing "
    "urgent at all, have a nice evening and talk soon, cheers and kind regards!",
    "Return the answer as JSON with exactly these keys: id, name, price. Do not add any other fields. The order "
    "ID is ORD-2024-88731 and the SKU is BLK-4410-XL; check whether both match the invoice before answering.",
]


def master_key() -> str:
    for line in (GATEWAY_DIR / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("LITELLM_MASTER_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("LITELLM_MASTER_KEY not in .env")


def percentile(values, pct):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1)))]


def run(label: str, n: int, warmup: int, model: str, prompts: list) -> None:
    headers = {"Authorization": f"Bearer {master_key()}", "Content-Type": "application/json"}
    latencies = []
    for i in range(warmup + n):
        body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompts[i % len(prompts)]}],
                           "max_tokens": 5}).encode()
        started = time.perf_counter()
        with urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:4000/v1/chat/completions", data=body,
                                                           headers=headers), timeout=60) as resp:
            resp.read()
        if i >= warmup:
            latencies.append((time.perf_counter() - started) * 1000)
    result = {"label": label, "n": n, "model": model, "prompts": len(prompts),
              "p50_ms": round(percentile(latencies, 50), 1), "p95_ms": round(percentile(latencies, 95), 1),
              "mean_ms": round(statistics.fmean(latencies), 1), "latencies_ms": [round(x, 1) for x in latencies]}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"overhead_{label}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print({k: v for k, v in result.items() if k != "latencies_ms"})


def compare() -> None:
    for suffix in ("", "_uncompressed"):
        try:
            on = json.loads((RESULTS / f"overhead_on{suffix}.json").read_text())
            off = json.loads((RESULTS / f"overhead_off{suffix}.json").read_text())
        except FileNotFoundError:
            continue
        print(f"[{suffix.strip('_') or 'mixed'}] n={on['n']}")
        for key in ("p50_ms", "p95_ms", "mean_ms"):
            print(f"  {key}: off={off[key]} on={on[key]} added={round(on[key] - off[key], 1)} ms")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", choices=["on", "off"])
    parser.add_argument("-n", type=int, default=60)
    parser.add_argument("--warmup", type=int, default=6)
    parser.add_argument("--model", default="obs-mock")
    parser.add_argument("--compare", action="store_true")
    # Uncompressed prompt only: removes LLMLingua's CPU-time variance from the comparison.
    parser.add_argument("--uncompressed-only", action="store_true")
    args = parser.parse_args()
    if args.compare:
        compare()
    else:
        prompts = PROMPTS[1:] if args.uncompressed_only else PROMPTS
        label = f"{args.label}_uncompressed" if args.uncompressed_only else args.label
        run(label, args.n, args.warmup, args.model, prompts)


if __name__ == "__main__":
    main()
