"""Train the logistic-regression head of embedding_classifier.py and evaluate the full sensitivity decision.

Training data (never used for evaluation):
  eval/sensitivity_train.jsonl   hand-written, broad coverage of sensitive topics and of hard negatives
                                 (general medical / legal / finance facts, company prose, code, chit-chat)
  eval/classifier_dev.jsonl      the original dev split (label "sensitive" vs the other three)
Threshold: 5-fold cross-validation on the training data; the largest threshold whose out-of-fold recall is >= 0.95.

Evaluation (held out):
  eval/classifier_test.jsonl                         original labelled test split (148 prompts)
  reports/playground-ab/data/sensitivity_holdout.jsonl  100 prompts written for this evaluation (40 sensitive)
  reports/compression-fit/data/qa.jsonl prose runs   company/product paragraphs (negatives)
  reports/compression-fit/data/pii.jsonl             50 case notes (positives; rules.py catches them anyway)
  the Playground prompt of 2026-11-06               (negative)

    .venv-compression/Scripts/python -m prompt_compression.eval.train_sensitivity_head
Writes prompt_compression/models/sensitivity_head.json and prompt_compression/eval/results/sensitivity_head.md.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold

GATEWAY = Path(__file__).resolve().parents[2]
if str(GATEWAY) not in sys.path:
    sys.path.insert(0, str(GATEWAY))

from prompt_compression import rules  # noqa: E402
from prompt_compression.embedding_classifier import DEFAULT_ENCODER, HEAD_PATH, EmbeddingEncoder  # noqa: E402
from prompt_compression.segmenter import PROSE, split_segments  # noqa: E402
from prompt_compression.topics import topic_hits  # noqa: E402

EVAL = Path(__file__).resolve().parent
RESULTS = EVAL / "results" / "sensitivity_head.md"
TARGET_RECALL = 0.95
C = 4.0
PLAYGROUND = (
    "Customers frequently cite reliability and after-sales support as the deciding factors when choosing between "
    "suppliers whose prices differ only by a few percentage points, and many buyers say that a responsive service team "
    "matters more to them than a small discount on the list price.\n\nIndustry observers often note that mid-sized "
    "manufacturers adapt faster to new standards than their larger rivals, because they have fewer layers of management "
    "and can make purchasing and design decisions within a few weeks rather than several months."
)


def jsonl(path: Path) -> list:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def qa_prose_runs() -> list:
    runs = []
    for row in jsonl(GATEWAY / "reports" / "compression-fit" / "data" / "qa.jsonl"):
        current = []
        for seg in split_segments(row["context"]):
            if seg.kind == PROSE:
                current.append(seg.text + seg.sep)
            elif current:
                runs.append("".join(current).strip())
                current = []
        if current:
            runs.append("".join(current).strip())
    return [r for r in runs if len(r) >= 40]


def eval_sets() -> dict:
    sets = {
        "test": [(r["text"], r["label"] == "sensitive") for r in jsonl(EVAL / "classifier_test.jsonl")],
        "holdout": [(r["text"], r["label"] == "sensitive")
                    for r in jsonl(GATEWAY / "reports" / "playground-ab" / "data" / "sensitivity_holdout.jsonl")],
        "qa_prose": [(t, False) for t in qa_prose_runs()],
        "pii_notes": [(r["context"], True) for r in jsonl(GATEWAY / "reports" / "compression-fit" / "data" / "pii.jsonl")],
        "playground": [(PLAYGROUND, False)],
    }
    return sets


def scores_for(encoder, w, b, texts, max_chunk_tokens=200):
    out = []
    for text in texts:
        vectors = np.array(encoder.encode(encoder.chunks(text, max_chunk_tokens)))
        out.append(float((1 / (1 + np.exp(-(vectors @ w + b)))).max()))
    return np.array(out)


def rates(flags, gold):
    flags, gold = np.asarray(flags), np.asarray(gold)
    rec = flags[gold].mean() if gold.any() else None
    fpr = flags[~gold].mean() if (~gold).any() else None
    return (None if rec is None else round(float(rec), 3), None if fpr is None else round(float(fpr), 3),
            int(flags[gold].sum()), int(gold.sum()), int(flags[~gold].sum()), int((~gold).sum()))


def main() -> None:
    train = [(r["text"], r["label"] == "sensitive") for r in jsonl(EVAL / "sensitivity_train.jsonl")]
    train += [(r["text"], r["label"] == "sensitive") for r in jsonl(EVAL / "classifier_dev.jsonl")]
    texts = [t for t, _ in train]
    y = np.array([g for _, g in train])

    encoder = EmbeddingEncoder(DEFAULT_ENCODER)
    encoder.load()
    X = np.array(encoder.encode(texts))

    # threshold from out-of-fold probabilities
    oof = np.zeros(len(y))
    for fold_train, fold_val in StratifiedKFold(5, shuffle=True, random_state=7).split(X, y):
        clf = LogisticRegression(C=C, class_weight="balanced", max_iter=2000).fit(X[fold_train], y[fold_train])
        oof[fold_val] = clf.predict_proba(X[fold_val])[:, 1]
    candidates = np.round(np.arange(0.05, 0.951, 0.01), 2)
    ok = [t for t in candidates if (oof[y] >= t).mean() >= TARGET_RECALL]
    threshold = float(max(ok))
    cv_rec, cv_fpr = float((oof[y] >= threshold).mean()), float((oof[~y] >= threshold).mean())

    clf = LogisticRegression(C=C, class_weight="balanced", max_iter=2000).fit(X, y)
    w, b = clf.coef_[0], float(clf.intercept_[0])
    head = {
        "name": "sensitivity-head-v1", "encoder": DEFAULT_ENCODER, "dim": int(X.shape[1]),
        "coef": [round(float(v), 6) for v in w], "intercept": round(b, 6), "threshold": threshold,
        "trained_on": {"files": ["eval/sensitivity_train.jsonl", "eval/classifier_dev.jsonl"],
                       "n": int(len(y)), "positives": int(y.sum())},
        "cv": {"folds": 5, "target_recall": TARGET_RECALL, "recall": round(cv_rec, 3), "fpr": round(cv_fpr, 3)},
        "regularisation_C": C, "created": time.strftime("%Y-%m-%d"),
    }
    HEAD_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEAD_PATH.write_text(json.dumps(head), encoding="utf-8")

    lines = ["# Sensitivity head: evaluation", "",
             f"Encoder `{DEFAULT_ENCODER}` + logistic regression (C={C}, balanced), trained on {len(y)} prompts "
             f"({int(y.sum())} sensitive). Threshold {threshold} = largest with 5-fold out-of-fold recall >= "
             f"{TARGET_RECALL} (CV recall {cv_rec:.3f}, CV FPR {cv_fpr:.3f}).", "",
             "Decision columns: `rules` = rules.py, `topics` = topics.py, `head` = this classifier at the threshold.",
             "", "| set | decision | recall | FPR | flagged sensitive | flagged other |", "|---|---|---|---|---|---|"]
    summary = {}
    t0 = time.perf_counter()
    n_scored = 0
    for name, items in eval_sets().items():
        xs = [t for t, _ in items]
        gold = np.array([g for _, g in items])
        rule = np.array([bool(rules.rule_hits(t)) for t in xs])
        topic = np.array([bool(topic_hits(t)) for t in xs])
        prob = scores_for(encoder, w, b, xs)
        n_scored += len(xs)
        head_flag = prob >= threshold
        for label, flags in (("rules", rule), ("rules or topics", rule | topic), ("rules or head", rule | head_flag),
                             ("rules or topics or head", rule | topic | head_flag)):
            rec, fpr, tp, pos, fp, neg = rates(flags, gold)
            summary.setdefault(name, {})[label] = {"recall": rec, "fpr": fpr}
            lines.append(f"| {name} | {label} | {rec if rec is not None else '-'} | {fpr if fpr is not None else '-'} | "
                         f"{tp}/{pos} | {fp}/{neg} |")
        missed = [t for t, g, f in zip(xs, gold, rule | topic | head_flag) if g and not f]
        alarms = [t for t, g, f in zip(xs, gold, rule | topic | head_flag) if not g and f]
        summary[name]["missed"] = missed
        summary[name]["false_alarms"] = alarms
        if name == "playground":
            summary[name]["score"] = round(float(prob[0]), 4)
    ms = (time.perf_counter() - t0) * 1000 / max(1, n_scored)
    lines += ["", f"Mean scoring time {ms:.1f} ms per text (encoder + head, this CPU, includes chunking).", ""]
    for name in ("test", "holdout"):
        lines.append(f"**{name}: missed by rules or topics or head ({len(summary[name]['missed'])})**")
        lines += [f"- {t[:140]}" for t in summary[name]["missed"]] or ["- none"]
        lines.append(f"\n**{name}: false alarms ({len(summary[name]['false_alarms'])})**")
        lines += [f"- {t[:140]}" for t in summary[name]["false_alarms"]] or ["- none"]
        lines.append("")
    lines.append(f"Playground prompt score: {summary['playground']['score']} (threshold {threshold}).")
    RESULTS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
