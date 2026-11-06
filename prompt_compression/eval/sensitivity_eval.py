"""sensitivity_eval.py -- how good is the pipeline's sensitivity decision?

The decision is: sensitive if a rule in rules.py hits, or if the zero-shot model's probability for "sensitive" reaches
SENSITIVITY_THRESHOLD. Every prompt of eval/classifier_<split>.jsonl is scored once; the report gives, for a sweep of
thresholds and for the configured one:

  recall   share of the gold "sensitive" prompts that are flagged (a miss means a sensitive text may be compressed)
  FPR      share of the other prompts that are flagged too (a false alarm only costs compression: the text is kept)

Choose the threshold on dev, then report test, never the other way round.

  python -m prompt_compression.eval.sensitivity_eval [--splits dev test]

Writes eval/results/sensitivity_<split>.md. CPU only; the first run downloads the model.
"""

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
GATEWAY = Path(__file__).resolve().parents[2]
if str(GATEWAY) not in sys.path:
    sys.path.insert(0, str(GATEWAY))

from prompt_compression.sensitivity import SensitivityDetector  # noqa: E402
from prompt_compression.settings import SensitivitySettings  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
THRESHOLDS = (0.99, 0.6, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2)


def load_split(split: str) -> list[dict]:
    path = EVAL_DIR / f"classifier_{split}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def counts(results: list[dict], threshold: float) -> tuple[int, int, int, int]:
    tp = fn = fp = tn = 0
    for r in results:
        flagged = r["rules"] or r["score"] >= threshold
        if r["gold"] == "sensitive":
            tp, fn = (tp + 1, fn) if flagged else (tp, fn + 1)
        else:
            fp, tn = (fp + 1, tn) if flagged else (fp, tn + 1)
    return tp, fn, fp, tn


def evaluate(detector: SensitivityDetector, split: str) -> str:
    rows = load_split(split)
    results, latencies = [], []
    for row in rows:
        result = detector.check(row["text"])
        results.append({"gold": row["label"], "hard": bool(row.get("hard_negative")), "rules": result.source == "rules",
                        "score": 0.0 if result.source == "rules" else result.score})
        if not result.cache_hit:
            latencies.append(result.elapsed_ms)
    positives = sum(r["gold"] == "sensitive" for r in results)
    rules_caught = sum(r["rules"] and r["gold"] == "sensitive" for r in results)
    configured = detector.settings.threshold
    lines = [
        f"# Sensitivity decision, split={split}",
        "",
        f"{len(results)} prompts, {positives} gold-sensitive; model {detector.model_name}; "
        f"the rules alone flag {rules_caught} of the {positives} sensitive prompts "
        f"({rules_caught / positives:.3f}). Latency per prompt p50 {statistics.median(latencies):.0f} ms, "
        f"p95 {sorted(latencies)[int(0.95 * (len(latencies) - 1))]:.0f} ms.",
        "",
        "| threshold | sensitive recall | false-positive rate | hard negatives flagged | tp | fn | fp | tn |",
        "|---|---|---|---|---|---|---|---|",
    ]
    hard = [r for r in results if r["hard"] and r["gold"] != "sensitive"]
    for threshold in sorted(set(THRESHOLDS) | {configured}, reverse=True):
        tp, fn, fp, tn = counts(results, threshold)
        hard_flagged = sum(1 for r in hard if r["rules"] or r["score"] >= threshold)
        mark = " (configured)" if threshold == configured else ""
        lines.append(f"| {threshold}{mark} | {tp / (tp + fn):.3f} | {fp / (fp + tn):.3f} | {hard_flagged}/{len(hard)} | {tp} | {fn} | {fp} | {tn} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--splits", nargs="*", choices=["dev", "test"], default=["dev", "test"])
    args = parser.parse_args()
    detector = SensitivityDetector(SensitivitySettings.from_env())
    detector.load()
    (EVAL_DIR / "results").mkdir(exist_ok=True)
    for split in args.splits:
        report = evaluate(detector, split)
        (EVAL_DIR / "results" / f"sensitivity_{split}.md").write_text(report, encoding="utf-8")
        print(report)


if __name__ == "__main__":
    main()
