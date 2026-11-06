"""Compare decision rules for the zero-shot sensitivity check on the same model (typeform/distilbert-base-uncased-mnli).

Sets: eval/classifier_dev.jsonl, eval/classifier_test.jsonl (gold labels), plus two negative sets that the current
rule flags by mistake: the prose paragraphs of reports/compression-fit/data/qa.jsonl (company/product facts, no
personal data) and the Playground prompt of 2026-11-06.

Every set is scored the way the pipeline does it: a rules.py hit is sensitive; otherwise the model score is compared
with a threshold. A variant = hypothesis wording x scoring mode:
  softmax   one softmax over the four candidate labels, P("sensitive")   (current)
  contrast  P(sensitive) / (P(sensitive) + P(non_sensitive)) from the same softmax
  multi     multi_label=True: independent entailment probability of the "sensitive" hypothesis

    .venv-compression/Scripts/python reports/playground-ab/scripts/sensitivity_variants.py
Writes reports/playground-ab/raw/sensitivity_variants.json and prints a table.
"""

import json
import sys
from pathlib import Path

GATEWAY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(GATEWAY))
from prompt_compression import rules  # noqa: E402
from prompt_compression.labels import DESCRIPTIONS, DESCRIPTIVE_TEMPLATE  # noqa: E402
from prompt_compression.segmenter import PROSE, split_segments  # noqa: E402
from prompt_compression.sensitivity import load_zero_shot_pipeline  # noqa: E402

EVAL = GATEWAY / "prompt_compression" / "eval"
OUT = GATEWAY / "reports" / "playground-ab" / "raw" / "sensitivity_variants.json"
MODEL = "typeform/distilbert-base-uncased-mnli"

PLAYGROUND = (
    "Customers frequently cite reliability and after-sales support as the deciding factors when choosing between "
    "suppliers whose prices differ only by a few percentage points, and many buyers say that a responsive service team "
    "matters more to them than a small discount on the list price.\n\nIndustry observers often note that mid-sized "
    "manufacturers adapt faster to new standards than their larger rivals, because they have fewer layers of management "
    "and can make purchasing and design decisions within a few weeks rather than several months."
)

WORDINGS = {
    "current": DESCRIPTIONS["sensitive"],
    "personal": "private information about a specific person, such as their identity, contact details, credentials, "
                "health, money or legal matters",
}


def label_sets(wording: str) -> dict:
    labels = dict(DESCRIPTIONS)
    labels["sensitive"] = WORDINGS[wording]
    return labels


def qa_prose_runs() -> list:
    """Consecutive prose blocks of each QA context, as the pipeline sends them to the model."""
    runs = []
    for line in (GATEWAY / "reports" / "compression-fit" / "data" / "qa.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        current = []
        for seg in split_segments(json.loads(line)["context"]):
            if seg.kind == PROSE:
                current.append(seg.text + seg.sep)
            elif current:
                runs.append("".join(current).strip())
                current = []
        if current:
            runs.append("".join(current).strip())
    return [r for r in runs if len(r) >= 40]


def main() -> None:
    zs = load_zero_shot_pipeline(MODEL)
    sets = {}
    for split in ("dev", "test"):
        rows = [json.loads(l) for l in (EVAL / f"classifier_{split}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        sets[split] = [(r["text"], r["label"] == "sensitive", r.get("hard_negative", False)) for r in rows]
    sets["qa_prose"] = [(t, False, True) for t in qa_prose_runs()]
    sets["playground"] = [(PLAYGROUND, False, True)]

    scores = {}  # (wording, mode) -> set -> list of (score_or_None_if_rule, gold)
    for wording in WORDINGS:
        labels = label_sets(wording)
        texts = list(labels.values())
        sens_text, ns_text = labels["sensitive"], labels["non_sensitive"]
        for name, items in sets.items():
            for text, gold, _ in items:
                rule = bool(rules.rule_hits(text))
                soft = zs(text, candidate_labels=texts, hypothesis_template=DESCRIPTIVE_TEMPLATE)
                s = dict(zip(soft["labels"], soft["scores"]))
                multi = zs(text, candidate_labels=[sens_text], hypothesis_template=DESCRIPTIVE_TEMPLATE, multi_label=True)
                values = {"softmax": s[sens_text], "contrast": s[sens_text] / (s[sens_text] + s[ns_text]),
                          "multi": multi["scores"][0]}
                for mode, v in values.items():
                    scores.setdefault(f"{wording}/{mode}", {}).setdefault(name, []).append(
                        {"score": None if rule else round(v, 4), "gold": gold})
        print(f"scored wording={wording}", flush=True)

    def rates(rows, thr):
        pos = [r for r in rows if r["gold"]]
        neg = [r for r in rows if not r["gold"]]
        flag = lambda r: r["score"] is None or r["score"] >= thr  # noqa: E731
        rec = sum(map(flag, pos)) / len(pos) if pos else None
        fpr = sum(map(flag, neg)) / len(neg) if neg else None
        return rec, fpr

    table = []
    for variant, per_set in scores.items():
        for thr in (0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9):
            row = {"variant": variant, "threshold": thr}
            for name, rows in per_set.items():
                rec, fpr = rates(rows, thr)
                row[f"{name}_recall"] = None if rec is None else round(rec, 3)
                row[f"{name}_fpr"] = None if fpr is None else round(fpr, 3)
            table.append(row)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"scores": scores, "table": table}, indent=1), encoding="utf-8")
    print(f"{'variant':20} thr  dev_rec dev_fpr test_rec test_fpr qa_fpr playground")
    for r in table:
        print(f"{r['variant']:20} {r['threshold']:.2f} {r['dev_recall']:7} {r['dev_fpr']:7} {r['test_recall']:8} "
              f"{r['test_fpr']:8} {r['qa_prose_fpr']:6} {r['playground_fpr']}")


if __name__ == "__main__":
    main()
