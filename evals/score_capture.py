"""Capture-only comparison of benchmark runs (no real-model run needed): sensitivity labels, savings and fidelity.

    .venv-compression/Scripts/python evals/score_capture.py B3 B4
"""

import json
import sys
from collections import Counter
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "reports" / "playground-ab" / "raw"


def summary(run: str) -> dict:
    rows = [json.loads(l) for l in (RAW / f"capture_{run}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    comp = [r for r in rows if r["arm"] == "compressed"]
    non_pii = [r for r in comp if r["family"] != "pii"]
    false_sens = [r for r in non_pii if (r.get("pc") or {}).get("category") == "sensitive"]
    out = {"requests": len(rows),
           "errors": sum(1 for r in rows if str(r.get("http_status")) != "200" or r.get("error")),
           "false_sensitive_rate": round(len(false_sens) / len(non_pii), 3),
           "false_sensitive_by_family": dict(Counter(r["family"] for r in false_sens))}
    for fam in ("qa", "logs", "code", "pii"):
        f = [r for r in comp if r["family"] == fam]
        o, s = sum(r["orig_tokens_cl100k"] for r in f), sum(r["sent_tokens_cl100k"] for r in f)
        out[f"{fam}_reduction_pct"] = round(100 * (o - s) / o, 2)
        out[f"{fam}_changed_pct"] = round(100 * sum(r["changed"] for r in f) / len(f), 1)
    o, s = sum(r["orig_tokens_cl100k"] for r in comp), sum(r["sent_tokens_cl100k"] for r in comp)
    out["all_reduction_pct"] = round(100 * (o - s) / o, 2)
    keys = [v for r in comp for v in (r.get("key_strings_kept") or {}).values()]
    out["key_strings_kept_pct"] = round(100 * sum(keys) / len(keys), 1)
    out["answer_in_prompt_pct"] = round(100 * sum(r["answer_in_prompt"] for r in comp) / len(comp), 1)
    out["pii_kept_verbatim_pct"] = round(100 * sum(1 for r in comp if r["family"] == "pii" and not r["changed"])
                                         / sum(1 for r in comp if r["family"] == "pii"), 1)
    out["pipeline_ms_p95"] = sorted((r.get("pc") or {}).get("elapsed_ms") or 0 for r in comp)[int(0.95 * len(comp))]
    return out


if __name__ == "__main__":
    runs = sys.argv[1:] or ["B3", "B4"]
    res = {r: summary(r) for r in runs}
    for k in res[runs[0]]:
        print(f"{k:28}" + "".join(f"{str(res[r][k]):>34}" for r in runs))
