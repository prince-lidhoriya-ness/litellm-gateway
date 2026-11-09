"""Scores a benchmark run (default B2) against evals/thresholds.yaml section `compression` and writes
<RESULTS_DIR>/<phase>/compression.json in the quality-gates schema (metrics, checks, findings).

Inputs (all written by reports/playground-ab/scripts): raw/results_<run>.json, raw/capture_<run>.jsonl,
raw/llm_<run>.jsonl, raw/throughput_<run>_*.jsonl.

    .venv-compression/Scripts/python evals/score_results.py --phase litellm-b2 [--run B2]
Env: QG_DIR (quality-gates folder), RESULTS_DIR (default evals/results), THRESHOLDS_FILE (default evals/thresholds.yaml).
"""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATEWAY = HERE.parent
RAW = GATEWAY / "reports" / "playground-ab" / "raw"
os.environ.setdefault("THRESHOLDS_FILE", str(HERE / "thresholds.yaml"))
os.environ.setdefault("RESULTS_DIR", str(HERE / "results"))
sys.path.insert(0, str(Path(os.environ.get("QG_DIR", "C:/AI-office/jenkins-setup/quality-gates/quality-gates")) / "gates"))
from common import finish  # noqa: E402


def rows(path: Path) -> list:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(p * len(values)))] if values else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True)
    ap.add_argument("--run", default="B2")
    a = ap.parse_args()
    res = json.loads((RAW / f"results_{a.run}.json").read_text(encoding="utf-8"))
    llm = rows(RAW / f"llm_{a.run}.jsonl")
    cap = rows(RAW / f"capture_{a.run}.jsonl")
    fam = res["llm"]["families"]
    capfam = res["capture"]["families"]
    thr = {}
    for f in RAW.glob(f"throughput_{a.run}_*.jsonl"):
        for r in rows(f):
            thr[(r["model"], r["arm"], r["concurrency"])] = r["rps"]

    comp_cap = [r for r in cap if r["arm"] == "compressed"]
    all_pc = [r["pc"] for r in llm + cap if r["arm"] == "compressed" and isinstance(r.get("pc"), dict)]
    bad_status = Counter(pc.get("status") for pc in all_pc if pc.get("status") not in ("ok", "skipped"))
    http_errors = sum(1 for r in llm + cap if str(r.get("http_status")) != "200" or r.get("error"))
    elapsed = [pc.get("elapsed_ms") or 0 for pc in all_pc]

    qa_logs_b = fam["qa"]["prompt_tokens_baseline"] + fam["logs"]["prompt_tokens_baseline"]
    qa_logs_c = fam["qa"]["prompt_tokens_compressed"] + fam["logs"]["prompt_tokens_compressed"]
    non_pii = [r for r in comp_cap if r["family"] != "pii"]
    false_sensitive = [r for r in non_pii if r["pc"].get("category") == "sensitive"]
    blocked = [r for r in comp_cap if r["family"] in ("qa", "logs") and not r["changed"]
               and r["pc"].get("category") == "sensitive"]
    gains = [100 * (thr[("obs-priced-llama", "compressed", c)] / thr[("obs-priced-llama", "baseline", c)] - 1)
             for c in (1, 4) if ("obs-priced-llama", "baseline", c) in thr]

    metrics = {
        "errors_or_timeouts": http_errors + sum(bad_status.values()),
        "pipeline_ms_max": round(max(elapsed), 1),
        "prompt_token_reduction_pct": round(fam["all"]["prompt_token_reduction_pct"], 2),
        "total_token_reduction_pct": round(fam["all"]["total_token_reduction_pct"], 2),
        "compressible_reduction_pct": round(100 * (qa_logs_b - qa_logs_c) / qa_logs_b, 2),
        "qa_reduction_pct": round(fam["qa"]["prompt_token_reduction_pct"], 2),
        "logs_reduction_pct": round(fam["logs"]["prompt_token_reduction_pct"], 2),
        "code_reduction_pct": round(fam["code"]["prompt_token_reduction_pct"], 2),
        "pii_reduction_pct": round(fam["pii"]["prompt_token_reduction_pct"], 2),
        "qa_prompts_changed_pct": round(100 * capfam["qa"]["changed"] / capfam["qa"]["n"], 1),
        "answers_lost_on_changed": len(res["llm"]["changed_subset"]["lost"]),
        "changed_prompts": res["llm"]["changed_subset"]["n"],
        "accuracy_baseline_pct": round(100 * fam["all"]["accuracy_baseline"], 1),
        "accuracy_compressed_pct": round(100 * fam["all"]["accuracy_compressed"], 1),
        "accuracy_drop_pts": round(100 * (fam["all"]["accuracy_baseline"] - fam["all"]["accuracy_compressed"]), 2),
        "key_strings_kept_pct": capfam["all"]["key_strings_kept_pct"],
        "answer_in_prompt_pct": capfam["all"]["answer_in_prompt_pct"],
        "latency_mean_diff_s": fam["all"]["latency_mean_diff"],
        "latency_p50_baseline_s": fam["all"]["latency_p50_baseline"],
        "latency_p50_compressed_s": fam["all"]["latency_p50_compressed"],
        "real_throughput_gain_pct": round(min(gains), 1) if gains else None,
        "overhead_p50_ms": round(1000 * capfam["all"]["overhead_p50_s"], 1),
        "overhead_p95_ms": round(1000 * capfam["all"]["overhead_p95_s"], 1),
        "mock_capacity_ratio": round(thr[("obs-mock", "compressed", 8)] / thr[("obs-mock", "baseline", 8)], 3),
        "mock_compressed_rps_c8": round(thr[("obs-mock", "compressed", 8)], 2),
        "mock_baseline_rps_c8": round(thr[("obs-mock", "baseline", 8)], 2),
        "false_sensitive_rate": round(len(false_sensitive) / len(non_pii), 3),
        "savings_blocked_rate": round(len(blocked) / sum(1 for r in comp_cap if r["family"] in ("qa", "logs")), 4),
        "pii_kept_verbatim_pct": round(100 * sum(1 for r in comp_cap if r["family"] == "pii" and not r["changed"])
                                       / capfam["pii"]["n"], 1),
    }

    findings = []
    for r in blocked:
        m = r["pc"]["messages"][0]
        findings.append({"tool": "score", "severity": "medium", "file": r["item"], "rule": "savings-blocked",
                         "msg": f"whole document kept verbatim: model score {m.get('score')} just over the threshold "
                                f"marked all {m['segments']['sensitive']} blocks sensitive ({r['orig_tokens_cl100k']} tokens unsaved)"})
    by_fam = Counter(r["family"] for r in false_sensitive)
    if false_sensitive:
        findings.append({"tool": "score", "severity": "low", "file": ", ".join(f"{k}: {v}" for k, v in by_fam.items()),
                         "rule": "false-sensitive-label",
                         "msg": f"{len(false_sensitive)} non-sensitive requests labelled sensitive (model, rules hits: "
                                f"{sum(1 for r in false_sensitive if r['pc'].get('messages', [{}])[0].get('rule_hits'))}); "
                                "request category and dashboards are wrong, savings mostly unaffected"})
    for r in comp_cap:
        if (r["pc"].get("elapsed_ms") or 0) > 1000:
            m = r["pc"]["messages"][0]
            findings.append({"tool": "score", "severity": "low", "file": r["item"], "rule": "slow-pipeline",
                             "msg": f"pipeline {r['pc']['elapsed_ms']:.0f} ms (classify {m.get('classify_ms')} ms, "
                                    f"LLMLingua-2 {m.get('compress_ms')} ms, {m['segments']['compress_calls']} call(s))"})
    if metrics["mock_capacity_ratio"] < 0.5:
        findings.append({"tool": "score", "severity": "high", "file": "prompt_compression/compressor_adapter.py, embedding_classifier.py",
                         "rule": "capacity",
                         "msg": f"with an instant model the gateway serves {metrics['mock_capacity_ratio']:.0%} of its "
                                "uncompressed throughput: model calls run one at a time behind locks in one proxy process"})
    noise = [(f, fam[f]["lost_by_compression"], fam[f]["gained_by_compression"]) for f in ("code", "pii")]
    notes = [f"answer flips on prompts compression did not change (model noise floor): "
             + ", ".join(f"{f} lost {l} / gained {g}" for f, l, g in noise),
             f"non-ok pipeline statuses: {dict(bad_status) or 'none'}; spend-log metadata missing for "
             f"{sum(1 for r in llm if r['arm'] == 'compressed' and not isinstance(r.get('pc'), dict))} llm rows"]
    finish("compression", f"Prompt compression results ({a.run})", a.phase, metrics, findings, notes)


if __name__ == "__main__":
    main()
