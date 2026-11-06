"""Aggregates raw/llm_<run>.jsonl, raw/capture_<run>.jsonl and raw/throughput_<run>_*.jsonl into raw/results_<run>.json.

    .venv-compression/Scripts/python reports/playground-ab/scripts/analyze.py --run-id A1
Prints Markdown tables for the report. Bootstrap CIs (2000 resamples, seed 7) for paired mean differences; exact McNemar
test for paired accuracy.
"""

import argparse
import json
import math
import random
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "raw"
FAMS = ("qa", "logs", "code", "pii")


def read(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


def pct(values, q):
    v = sorted(values)
    if not v:
        return None
    k = (len(v) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def boot_mean_ci(diffs, n=2000, seed=7):
    if not diffs:
        return (None, None)
    rng = random.Random(seed)
    means = sorted(st.fmean(rng.choices(diffs, k=len(diffs))) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def pairs(rows):
    by = defaultdict(dict)
    for r in rows:
        by[r["item"]][r["arm"]] = r
    return {k: v for k, v in by.items() if "baseline" in v and "compressed" in v}


def was_changed(r):
    """The pipeline's own report (cl100k, same text) says it removed tokens; immune to the nonce's +-1 token."""
    pc = r.get("pc") or {}
    return (pc.get("status") == "ok") and (pc.get("tokens_after") or 0) < (pc.get("tokens_before") or 0)


def ptok(r):
    return ((r.get("usage") or {}).get("prompt_tokens")) or r.get("spend_prompt_tokens") or 0


def ctok(r):
    return ((r.get("usage") or {}).get("completion_tokens")) or r.get("spend_completion_tokens") or 0


def r3(x):
    return None if x is None else round(x, 3)


def llm_section(rows):
    P = pairs(rows)
    out = {"n_pairs": len(P), "errors": sum(1 for r in rows if r.get("http_status") != 200)}
    fams = {}
    for fam in FAMS + ("all",):
        items = [v for v in P.values() if fam == "all" or v["baseline"]["family"] == fam]
        if not items:
            continue
        b = [v["baseline"] for v in items]
        c = [v["compressed"] for v in items]
        pb, pc_ = sum(map(ptok, b)), sum(map(ptok, c))
        tb, tc = pb + sum(map(ctok, b)), pc_ + sum(map(ctok, c))
        lat_d = [v["compressed"]["latency_s"] - v["baseline"]["latency_s"] for v in items]
        acc_b, acc_c = sum(r["correct"] for r in b), sum(r["correct"] for r in c)
        disc_b = sum(1 for v in items if v["baseline"]["correct"] and not v["compressed"]["correct"])
        disc_c = sum(1 for v in items if v["compressed"]["correct"] and not v["baseline"]["correct"])
        summaries = [v["compressed"].get("pc") or {} for v in items]
        changed = sum(1 for v in items if was_changed(v["compressed"]))
        pipe_ms = [s.get("elapsed_ms") for s in summaries if s.get("elapsed_ms") is not None]
        fams[fam] = {
            "n": len(items),
            "prompt_tokens_baseline": pb, "prompt_tokens_compressed": pc_,
            "prompt_token_reduction_pct": r3(100 * (pb - pc_) / pb) if pb else None,
            "total_tokens_baseline": tb, "total_tokens_compressed": tc,
            "total_token_reduction_pct": r3(100 * (tb - tc) / tb) if tb else None,
            "completion_tokens_baseline": sum(map(ctok, b)), "completion_tokens_compressed": sum(map(ctok, c)),
            "prompts_with_fewer_tokens": changed,
            "pipeline_ratio_mean": r3(st.fmean([s.get("compression_ratio") or 1.0 for s in summaries])),
            "accuracy_baseline": r3(acc_b / len(items)), "accuracy_compressed": r3(acc_c / len(items)),
            "correct_baseline": acc_b, "correct_compressed": acc_c,
            "lost_by_compression": disc_b, "gained_by_compression": disc_c, "mcnemar_p": r3(mcnemar(disc_b, disc_c)),
            "same_response": sum(1 for v in items if (v["baseline"]["response"] or "").strip()
                                 == (v["compressed"]["response"] or "").strip()),
            "latency_p50_baseline": r3(pct([r["latency_s"] for r in b], .5)),
            "latency_p50_compressed": r3(pct([r["latency_s"] for r in c], .5)),
            "latency_p95_baseline": r3(pct([r["latency_s"] for r in b], .95)),
            "latency_p95_compressed": r3(pct([r["latency_s"] for r in c], .95)),
            "latency_mean_baseline": r3(st.fmean(r["latency_s"] for r in b)),
            "latency_mean_compressed": r3(st.fmean(r["latency_s"] for r in c)),
            "latency_mean_diff": r3(st.fmean(lat_d)), "latency_mean_diff_ci95": [r3(x) for x in boot_mean_ci(lat_d)],
            "latency_p50_diff": r3(pct(lat_d, .5)),
            "pipeline_ms_p50": r3(pct(pipe_ms, .5)), "pipeline_ms_p95": r3(pct(pipe_ms, .95)),
            "pipeline_ms_max": r3(max(pipe_ms) if pipe_ms else None),
            "status": dict(Counter(s.get("status", "missing") for s in summaries)),
            "category": dict(Counter(s.get("category", "missing") for s in summaries)),
            "actions": dict(Counter(m.get("action") for s in summaries for m in (s.get("messages") or []))),
            "kept_reasons": dict(sum((Counter(s.get("kept") or {}) for s in summaries), Counter())),
            "spend_usd_baseline": r3(sum((r.get("spend_usd") or 0) for r in b) * 1000),
            "spend_usd_compressed": r3(sum((r.get("spend_usd") or 0) for r in c) * 1000),
        }
    out["families"] = fams
    # where compression did change the prompt: quality on that subset
    ch = [v for v in P.values() if was_changed(v["compressed"])]
    out["changed_subset"] = {
        "n": len(ch),
        "accuracy_baseline": r3(st.fmean(v["baseline"]["correct"] for v in ch)) if ch else None,
        "accuracy_compressed": r3(st.fmean(v["compressed"]["correct"] for v in ch)) if ch else None,
        "prompt_token_reduction_pct": r3(100 * (1 - sum(ptok(v["compressed"]) for v in ch)
                                                / sum(ptok(v["baseline"]) for v in ch))) if ch else None,
        "lost": [v["baseline"]["item"] for v in ch if v["baseline"]["correct"] and not v["compressed"]["correct"]],
        "gained": [v["baseline"]["item"] for v in ch if v["compressed"]["correct"] and not v["baseline"]["correct"]],
    }
    out["timeouts_or_errors"] = [v["compressed"]["item"] for v in P.values()
                                 if (v["compressed"].get("pc") or {}).get("status") == "error"]
    return out


def capture_section(rows):
    P = pairs(rows)
    fams = {}
    for fam in FAMS + ("all",):
        items = [v for v in P.values() if fam == "all" or v["baseline"]["family"] == fam]
        if not items:
            continue
        c = [v["compressed"] for v in items]
        b = [v["baseline"] for v in items]
        keys = [ok for r in c for ok in (r.get("key_strings_kept") or {}).values() if ok is not None]
        bk = [ok for r in b for ok in (r.get("key_strings_kept") or {}).values() if ok is not None]
        orig = sum(r["orig_tokens_cl100k"] for r in c)
        sent = sum((r.get("sent_tokens_cl100k") or r["orig_tokens_cl100k"]) for r in c)
        lat_d = [v["compressed"]["latency_s"] - v["baseline"]["latency_s"] for v in items]
        fams[fam] = {
            "n": len(items), "changed": sum(1 for r in c if r.get("changed")),
            "baseline_unchanged": sum(1 for r in b if not r.get("changed")),
            "tokens_orig_cl100k": orig, "tokens_sent_cl100k": sent,
            "token_reduction_pct": r3(100 * (orig - sent) / orig) if orig else None,
            "key_strings_kept_pct": r3(100 * sum(keys) / len(keys)) if keys else None,
            "key_strings_kept_baseline_pct": r3(100 * sum(bk) / len(bk)) if bk else None,
            "answer_in_prompt_pct": r3(100 * st.fmean(r.get("answer_in_prompt", 0) for r in c)),
            "overhead_mean_s": r3(st.fmean(lat_d)), "overhead_p50_s": r3(pct(lat_d, .5)),
            "overhead_p95_s": r3(pct(lat_d, .95)), "overhead_ci95": [r3(x) for x in boot_mean_ci(lat_d)],
            "baseline_latency_p50_s": r3(pct([r["latency_s"] for r in b], .5)),
        }
    return {"n_pairs": len(P), "families": fams}


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--run-id", required=True)
    run = a.parse_args().run_id
    res = {"run": run}
    llm = read(RAW / f"llm_{run}.jsonl")
    cap = read(RAW / f"capture_{run}.jsonl")
    if llm:
        res["llm"] = llm_section(llm)
    if cap:
        res["capture"] = capture_section(cap)
    res["throughput"] = {p.stem: read(p) for p in sorted(RAW.glob(f"throughput_{run}_*.jsonl"))}
    (RAW / f"results_{run}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=1)[:20000])


if __name__ == "__main__":
    main()
