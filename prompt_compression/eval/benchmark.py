"""Benchmarks zero-shot NLI checkpoints on the classifier dataset (CPU only).

Scores the raw transformers zero-shot pipeline as a four-way classifier, which is
what the comparison between NLI checkpoints uses. The pipeline itself only uses
the probability of the "sensitive" label; how well that works as a decision
(rules + model + threshold + chunking) is measured by eval/sensitivity_eval.py.

Examples:
  python -m prompt_compression.eval.benchmark --split dev --formats plain descriptive \
      --models typeform/distilbert-base-uncased-mnli
  python -m prompt_compression.eval.benchmark --split test --formats descriptive \
      --models typeform/distilbert-base-uncased-mnli MoritzLaurer/deberta-v3-base-zeroshot-v2.0

Each run writes eval/results/<split>__<format>__<model>.json and appends a row
to eval/results/summary_<split>.md.
"""

import argparse
import json
import os
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
import transformers
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

from prompt_compression.sensitivity import load_zero_shot_pipeline
from prompt_compression.labels import CRITICAL, LABEL_FORMATS, LABELS, SENSITIVE

EVAL_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EVAL_DIR / "results"
WARMUP_CALLS = 3


def load_split(split: str) -> list[dict]:
    path = EVAL_DIR / f"classifier_{split}.jsonl"
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(pct / 100 * (len(ordered) - 1))))
    return ordered[index]


def _param_count(model) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


def score(rows: list[dict], predictions: list[str], latencies_ms: list[float]) -> dict:
    gold = [row["label"] for row in rows]
    precision, recall, f1, support = precision_recall_fscore_support(
        gold, predictions, labels=list(LABELS), zero_division=0
    )
    per_class = {
        label: {
            "precision": round(float(precision[i]), 4),
            "recall": round(float(recall[i]), 4),
            "f1": round(float(f1[i]), 4),
            "support": int(support[i]),
        }
        for i, label in enumerate(LABELS)
    }
    hard = [i for i, row in enumerate(rows) if row.get("hard_negative")]
    # Routing view: sensitive/critical are never compressed, the other two are.
    protected = {SENSITIVE, CRITICAL}
    gold_protected = [p for g, p in zip(gold, predictions) if g in protected]
    gold_sensitive = [p for g, p in zip(gold, predictions) if g == SENSITIVE]
    gold_compressible = [p for g, p in zip(gold, predictions) if g not in protected]
    return {
        "routing": {
            "sensitive_kept_uncompressed": f"{sum(p in protected for p in gold_sensitive)}/{len(gold_sensitive)}",
            "protected_kept_uncompressed": f"{sum(p in protected for p in gold_protected)}/{len(gold_protected)}",
            "compressible_compressed": f"{sum(p not in protected for p in gold_compressible)}/{len(gold_compressible)}",
        },
        "per_class": per_class,
        "macro_f1": round(float(f1.mean()), 4),
        "accuracy": round(sum(g == p for g, p in zip(gold, predictions)) / len(gold), 4),
        "hard_negative_accuracy": (
            round(sum(gold[i] == predictions[i] for i in hard) / len(hard), 4) if hard else None
        ),
        "confusion_matrix": {
            "labels": list(LABELS),
            "rows_gold_cols_pred": confusion_matrix(gold, predictions, labels=list(LABELS)).tolist(),
        },
        "latency_ms": {
            "p50": round(_percentile(latencies_ms, 50), 1),
            "p95": round(_percentile(latencies_ms, 95), 1),
            "mean": round(statistics.fmean(latencies_ms), 1),
        },
    }


def run_model_only(model_name: str, label_format: str, rows: list[dict], quantize: str = "none") -> dict:
    label_texts, template = LABEL_FORMATS[label_format]
    text_to_label = {text: label for label, text in label_texts.items()}
    candidate_labels = list(label_texts.values())

    load_started = time.perf_counter()
    classifier = load_zero_shot_pipeline(model_name, quantize)
    load_seconds = time.perf_counter() - load_started
    call_kwargs = {
        "candidate_labels": candidate_labels,
        "hypothesis_template": template,
        "batch_size": len(candidate_labels),
    }

    for row in rows[:WARMUP_CALLS]:
        classifier(row["text"], **call_kwargs)

    predictions, top_scores, latencies_ms = [], [], []
    for row in rows:
        started = time.perf_counter()
        result = classifier(row["text"], **call_kwargs)
        latencies_ms.append((time.perf_counter() - started) * 1000)
        predictions.append(text_to_label[result["labels"][0]])
        top_scores.append(round(float(result["scores"][0]), 4))

    report = score(rows, predictions, latencies_ms)
    report.update(
        {
            "params": _param_count(classifier.model),
            "max_length": classifier.tokenizer.model_max_length,
            "load_seconds": round(load_seconds, 1),
            "predictions": [
                {"id": row["id"], "gold": row["label"], "pred": pred, "score": top}
                for row, pred, top in zip(rows, predictions, top_scores)
            ],
        }
    )
    return report


def _summary_row(model: str, label_format: str, report: dict) -> str:
    sensitive = report["per_class"][SENSITIVE]
    params = report.get("params")
    return (
        f"| {model} | {label_format} | {sensitive['recall']:.3f} | {sensitive['precision']:.3f} | "
        f"{report['macro_f1']:.3f} | {report['accuracy']:.3f} | {report['hard_negative_accuracy']} | "
        f"{report['latency_ms']['p50']} | {report['latency_ms']['p95']} | "
        f"{f'{params / 1e6:.0f}M' if params else '-'} |"
    )


def _append_summary(split: str, row: str) -> None:
    path = RESULTS_DIR / f"summary_{split}.md"
    if not path.exists():
        path.write_text(
            f"# Classifier benchmark, split={split}\n\n"
            "| model | format | sensitive recall | sensitive precision | macro-F1 | accuracy | "
            "hard-neg acc | p50 ms | p95 ms | params |\n"
            "|---|---|---|---|---|---|---|---|---|---|\n",
            encoding="utf-8",
        )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(row + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--models", nargs="*", default=[])
    parser.add_argument("--formats", nargs="*", choices=list(LABEL_FORMATS), default=["descriptive"])
    parser.add_argument("--quantize", choices=["none", "int8"], default="none", help="model-only runs: int8 dynamic quantization")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_split(args.split)
    environment = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "split": args.split,
        "n_examples": len(rows),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "cpu": platform.processor(),
        "torch_threads": torch.get_num_threads(),
        "device": "cpu",
    }

    def runs():
        for model_name in args.models:
            for label_format in args.formats:
                name = model_name + (f"@{args.quantize}" if args.quantize != "none" else "")
                print(f"-> {name} [{label_format}] on {args.split} ({len(rows)} examples)", flush=True)
                yield name, label_format, run_model_only(model_name, label_format, rows, args.quantize)

    for model_name, label_format, report in runs():
        report["environment"] = environment
        report["model"] = model_name
        report["label_format"] = label_format
        out_path = RESULTS_DIR / f"{args.split}__{label_format}__{model_name.replace('/', '--')}.json"
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        row = _summary_row(model_name, label_format, report)
        _append_summary(args.split, row)
        print(row, flush=True)
        print(f"   confusion (rows=gold, cols=pred, order={list(LABELS)}): "
              f"{report['confusion_matrix']['rows_gold_cols_pred']}", flush=True)


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    main()
