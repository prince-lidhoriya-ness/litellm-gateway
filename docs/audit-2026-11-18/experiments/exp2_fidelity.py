"""Experiment 2: identifier and fact fidelity of the production LLMLingua-2 call (LLMLinguaCompressor, the gateway's own adapter).

Each planted item is one sentence inside a ~90-word prose paragraph. Paragraphs are joined with blank lines and compressed
in ONE call, the way the gateway merges a run of prose units (pipeline/actions). Survival is measured two ways:
  exact       the original string appears verbatim in the output
  normalized  the string appears after removing all whitespace (separates formatting damage from information loss)
"""
import json
import os
import random
import sys
import time

GW = r"C:\Users\P7120489\litellm-gateway"
SP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GW)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from prompt_compression.compressor_adapter import LLMLinguaCompressor  # noqa: E402
from prompt_compression.settings import DEFAULT_COMPRESSION_MODEL, DEFAULT_COMPRESSION_REVISION  # noqa: E402

ITEMS = [
    ("id", "The escalation reference for the Lisbon case is ESC-20417, which the regional desk logged last week.", "ESC-20417"),
    ("amount", "The approved contingency budget was 184,500 dollars after the finance review.", "184,500"),
    ("ip", "The failing worker is 10.42.7.19 and it must be drained before the rerun starts.", "10.42.7.19"),
    ("date", "The incident started on 2026-03-14 and the team closed it three days later.", "2026-03-14"),
    ("config_key", "Before the rerun, set MAX_RETRY_LIMIT to 5 in the staging configuration file.", "MAX_RETRY_LIMIT"),
    ("error_code", "The call returned E_CONN_RESET_0x7f on the third attempt according to the gateway log.", "E_CONN_RESET_0x7f"),
    ("name", "Tanaka approved the revised rollout plan after the second review meeting.", "Tanaka"),
    ("path", "The migration script lives at scripts/db/migrate_v2.sql and must run as the service user.", "scripts/db/migrate_v2.sql"),
    ("inline_code_call", "The retry call is `client.post(url, timeout=30)` and it fails only under heavy load.", "client.post(url, timeout=30)"),
    ("inline_code_attr", "The counter is kept in `Exporter.retries` and it is never reset between batches.", "Exporter.retries"),
    ("expression", "The backoff is computed as self.backoff * attempt inside the send loop of the client.", "self.backoff * attempt"),
    ("version", "Upgrade the image to litellm v1.106.0 before enabling the new callback chain.", "v1.106.0"),
    ("commit_hash", "The commit abedab6 added the EKS manifests and updated the deployment readme.", "abedab6"),
    ("email", "Send the findings to ops-oncall@example.com once the review has been completed.", "ops-oncall@example.com"),
    ("negation", "The fix must not be deployed to production before the staging test has passed.", "must not be deployed"),
    ("bound", "Do not retry more than 3 times when the provider returns a 400 response to a request.", "more than 3 times"),
    ("threshold", "Requests above 32,000 tokens skip compression entirely, so very large prompts gain nothing.", "32,000"),
    ("json_key", "Set the field \"stream_timeout\" to 300 in the router settings of the proxy.", "stream_timeout"),
    ("condition", "Only enable the response cache when the caller explicitly sets the cache header.", "Only enable the response cache"),
    ("percent", "The measured savings were 39% on the selection benchmark and 11% on the narrative benchmark.", "39%"),
]
FILLER = [
    "The team met on Tuesday to review the status of the rollout and the open questions from the previous week.",
    "Most of the discussion focused on how the changes would affect the on-call rota and the handover between shifts.",
    "Several people asked whether the new process would add time to each review, and the answer was that it should not.",
    "The notes from the meeting were shared with the wider group, and the owners agreed to update their sections by Friday.",
    "No decision was taken on the vendor question, which will return to the agenda once the cost figures are complete.",
]


def paragraph(rng, sentence):
    sentences = [rng.choice(FILLER) for _ in range(4)]
    sentences.insert(rng.randint(1, 3), sentence)
    return " ".join(sentences)


def normalized(s):
    return "".join(s.split()).lower()


def main():
    rng = random.Random(7)
    comp = LLMLinguaCompressor(DEFAULT_COMPRESSION_MODEL, DEFAULT_COMPRESSION_REVISION, cache_size=0)
    t0 = time.perf_counter()
    comp.load()
    print(f"model load {time.perf_counter() - t0:.1f}s", flush=True)
    results = {}
    for rate in (0.4, 0.6):
        paragraphs = [paragraph(rng, s) for _, s, _ in ITEMS]
        text = "\n\n".join(paragraphs)
        t1 = time.perf_counter()
        out = comp.compress(text, rate)
        seconds = time.perf_counter() - t1
        compressed = out.text
        rows = []
        for kind, sentence, needle in ITEMS:
            rows.append({
                "kind": kind,
                "exact": needle in compressed,
                "normalized": normalized(needle) in normalized(compressed),
            })
        n = len(rows)
        results[str(rate)] = {
            "origin_tokens": out.origin_tokens, "compressed_tokens": out.compressed_tokens,
            "ratio": round(out.origin_tokens / max(1, out.compressed_tokens), 2),
            "seconds_one_call": round(seconds, 2),
            "exact_survival": f"{sum(r['exact'] for r in rows)}/{n}",
            "normalized_survival": f"{sum(r['normalized'] for r in rows)}/{n}",
            "rows": rows,
        }
        print(f"rate={rate} ratio={results[str(rate)]['ratio']} secs={seconds:.1f} "
              f"exact={results[str(rate)]['exact_survival']} normalized={results[str(rate)]['normalized_survival']}", flush=True)
        for r in rows:
            if not r["normalized"]:
                print("   LOST:", r["kind"], flush=True)
        # show how identifiers were rewritten at this rate
        for kind, _, needle in ITEMS[:4]:
            i = normalized(compressed).find(normalized(needle)[:4])
        with open(os.path.join(SP, "exp2_sample_rate_%s.txt" % rate), "w", encoding="utf-8") as fh:
            fh.write(compressed)
    # timing scaling: one call on increasing sizes (rate 0.4), to see the cost per token on this CPU
    scale = []
    base = " ".join(FILLER)
    for reps in (2, 8, 20):
        text = "\n\n".join([base] * reps)
        t2 = time.perf_counter()
        o = comp.compress(text, 0.4)
        scale.append({"origin_tokens": o.origin_tokens, "seconds": round(time.perf_counter() - t2, 2)})
        print("scale", scale[-1], flush=True)
    results["scaling_rate_0.4"] = scale
    with open(os.path.join(SP, "exp2_results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)


if __name__ == "__main__":
    main()
