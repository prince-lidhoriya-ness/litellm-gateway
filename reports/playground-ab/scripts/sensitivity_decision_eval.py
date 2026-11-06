"""Decision rules built from rules.py, topics.py and the model score (current wording, 4-way softmax), using the
scores saved by sensitivity_variants.py. Designed on dev; test, QA prose and the Playground prompt are held out.

    .venv-compression/Scripts/python reports/playground-ab/scripts/sensitivity_decision_eval.py
"""

import json
import sys
from pathlib import Path

GATEWAY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(GATEWAY))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompt_compression import rules  # noqa: E402
from prompt_compression.topics import topic_hits  # noqa: E402
from sensitivity_variants import PLAYGROUND, qa_prose_runs  # noqa: E402

RAW = GATEWAY / "reports" / "playground-ab" / "raw"
EVAL = GATEWAY / "prompt_compression" / "eval"

saved = json.loads((RAW / "sensitivity_variants.json").read_text(encoding="utf-8"))["scores"]["current/softmax"]
texts = {}
for split in ("dev", "test"):
    rows = [json.loads(l) for l in (EVAL / f"classifier_{split}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    texts[split] = [(r["text"], r["label"]) for r in rows]
texts["qa_prose"] = [(t, "non_sensitive") for t in qa_prose_runs()]
texts["playground"] = [(PLAYGROUND, "non_sensitive")]

# Held-out sets scored here with the production wording (4-way softmax): a fresh holdout written after the lexicon,
# and the 50 case notes of reports/compression-fit/data/pii.jsonl (all sensitive).
from prompt_compression.labels import DESCRIPTIONS, DESCRIPTIVE_TEMPLATE  # noqa: E402
from prompt_compression.sensitivity import load_zero_shot_pipeline  # noqa: E402

_zs = load_zero_shot_pipeline("typeform/distilbert-base-uncased-mnli")


def model_score(text):
    if rules.rule_hits(text):
        return {"score": None}
    out = _zs(text, candidate_labels=list(DESCRIPTIONS.values()), hypothesis_template=DESCRIPTIVE_TEMPLATE)
    return {"score": round(dict(zip(out["labels"], out["scores"]))[DESCRIPTIONS["sensitive"]], 4)}


holdout = [json.loads(l) for l in (RAW.parent / "data" / "sensitivity_holdout.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
texts["holdout"] = [(r["text"], r["label"]) for r in holdout]
pii = [json.loads(l) for l in (GATEWAY / "reports" / "compression-fit" / "data" / "pii.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
texts["pii_notes"] = [(r["context"], "sensitive") for r in pii]
for name in ("holdout", "pii_notes"):
    saved[name] = [model_score(t) for t, _ in texts[name]]

DECISIONS = {
    "current: rules or model>=0.35": lambda t, s: bool(rules.rule_hits(t)) or (s is not None and s >= 0.35),
    "rules only": lambda t, s: bool(rules.rule_hits(t)),
    "rules or topics": lambda t, s: bool(rules.rule_hits(t)) or bool(topic_hits(t)),
    "rules or topics or model>=0.6": lambda t, s: bool(rules.rule_hits(t)) or bool(topic_hits(t)) or (s is not None and s >= 0.6),
    "rules or topics or model>=0.7": lambda t, s: bool(rules.rule_hits(t)) or bool(topic_hits(t)) or (s is not None and s >= 0.7),
}

result = {}
print(f"{'decision':34} {'dev rec':>8} {'dev FPR':>8} {'test rec':>9} {'test FPR':>9} {'QA prose FPR':>13} {'Playground':>11}"
      f" {'hold rec':>9} {'hold FPR':>9} {'PII rec':>8}")
for name, decide in DECISIONS.items():
    row = {}
    for split, items in texts.items():
        flags = [(decide(t, s["score"]), label == "sensitive") for (t, label), s in zip(items, saved[split])]
        pos = [f for f, g in flags if g]
        neg = [f for f, g in flags if not g]
        row[split] = {"recall": round(sum(pos) / len(pos), 3) if pos else None,
                      "fpr": round(sum(neg) / len(neg), 3) if neg else None, "tp": sum(pos), "pos": len(pos), "fp": sum(neg), "neg": len(neg),
                      "missed": [t[:100] for (t, label), s in zip(items, saved[split])
                                 if label == "sensitive" and not decide(t, s["score"])],
                      "false_alarms": [(label, t[:100]) for (t, label), s in zip(items, saved[split])
                                       if label != "sensitive" and decide(t, s["score"])]}
    result[name] = row
    print(f"{name:34} {row['dev']['recall']:8} {row['dev']['fpr']:8} {row['test']['recall']:9} {row['test']['fpr']:9} "
          f"{row['qa_prose']['fpr']:13} {'flagged' if row['playground']['fpr'] else 'not flagged':>11}"
          f" {row['holdout']['recall']:9} {row['holdout']['fpr']:9} {row['pii_notes']['recall']:8}")
(RAW / "sensitivity_decisions.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
for name in ("rules or topics", "rules or topics or model>=0.6"):
    print(f"\n== {name}: HOLDOUT misses"); [print("  ", m) for m in result[name]["holdout"]["missed"]]
    print(f"== {name}: HOLDOUT false alarms"); [print("  ", f[1]) for f in result[name]["holdout"]["false_alarms"]]
    print(f"\n== {name}: test misses"); [print("  ", m) for m in result[name]["test"]["missed"]]
    print(f"== {name}: test false alarms"); [print("  ", f) for f in result[name]["test"]["false_alarms"]]
    print(f"== {name}: QA prose false alarms"); [print("  ", f[1]) for f in result[name]["qa_prose"]["false_alarms"]]
