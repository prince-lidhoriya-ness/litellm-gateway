"""guard_eval.py -- does the pipeline keep the quality that reports/compression-fit/REPORT.md says whole-message
compression loses?

Runs the real PromptPipeline (real LLMLingua-2 on CPU) on the benchmark items of reports/compression-fit/data, sends
each changed prompt to the same local model the report used, and scores "the reference string appears in the answer".

  python -m prompt_compression.eval.guard_eval [--detector real|rules] [--limit N] [--families qa,logs,code]
                                               [--conditions ...]

--detector real   the production sensitivity check: rules plus the NLI model at SENSITIVITY_THRESHOLD (default)
--detector rules  rules only, no NLI model: isolates the router from the sensitivity check

Needs Ollama with llama3.2:3b running (OLLAMA_URL, TARGET_MODEL override) and the research data and results:
  reports/compression-fit/data/*.jsonl                       items, reference answers
  reports/compression-fit/raw/llm_runs.jsonl                 the report's uncompressed answers, reused as the baseline
The prompt template is the report's own, so the baseline is the report's baseline. When the router leaves a prompt
byte for byte unchanged, the baseline answer is reused instead of asking the model again (and counted as such).

Conditions (all with LLMLingua-2 capped at settings.max_ratio):
  default      route "narrative" at the default rate (0.4)
  aggressive   route "narrative" at rate 0.28
  passages     default + route "passages" (drop whole passages the question does not need; size guard lowered to 100 tokens)
  records      default + route "records"   (drop log/JSON lines the question does not name; size guard lowered to 10 lines)

Raw rows go to reports/compression-fit/raw/gateway_eval/runs_<detector>.jsonl, the summary to
eval/results/guard_eval_<detector>.md.
"""

import argparse
import dataclasses
import json
import math
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

GATEWAY = Path(__file__).resolve().parents[2]
if str(GATEWAY) not in sys.path:
    sys.path.insert(0, str(GATEWAY))

from prompt_compression.compressor_adapter import LLMLinguaCompressor  # noqa: E402
from prompt_compression.pipeline import PromptPipeline  # noqa: E402
from prompt_compression.sensitivity import Sensitivity, SensitivityDetector  # noqa: E402
from prompt_compression.settings import PipelineSettings, SensitivitySettings  # noqa: E402
from prompt_compression import rules  # noqa: E402

RESEARCH = GATEWAY / "reports" / "compression-fit"
RAW_DIR = RESEARCH / "raw" / "gateway_eval"
RESULTS_DIR = Path(__file__).resolve().parent / "results"

URL = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/chat"
MODEL = os.environ.get("TARGET_MODEL", "llama3.2:3b")
INSTR = "Answer the question using only the document below. Reply with only the answer value (a name, number or identifier), nothing else."
OPTIONS = dict(temperature=0, seed=7, num_predict=24, num_ctx=4096)

# name -> (routes, settings overrides). The benchmark items are small (about 360 tokens, 20 lines), so the selection
# routes run with lower size guards than the production defaults of 300 passage tokens and 20 lines.
CONDITIONS = {
    "default": (frozenset({"narrative"}), {}),
    "aggressive": (frozenset({"narrative"}), {"rate": 0.28}),
    "passages": (frozenset({"narrative", "passages"}), {"min_passage_tokens": 100}),
    "records": (frozenset({"narrative", "records"}), {"record_min_lines": 10}),
}
DEFAULT_PLAN = {"qa": ["default", "aggressive", "passages"], "logs": ["default", "aggressive", "records"], "code": ["default", "aggressive"]}


class RulesOnlyDetector:
    """Sensitivity without the NLI model: only the deterministic rules."""

    model_name = "rules-only"

    def load(self):
        pass

    def rules_only(self, text):
        hits = tuple(rules.rule_hits(text)) if text and text.strip() else ()
        return Sensitivity(bool(hits), 1.0 if hits else 0.0, "rules" if hits else "none", self.model_name, rule_hits=hits)

    def check(self, text):
        result = self.rules_only(text)
        return result if result.sensitive else Sensitivity(False, 0.0, "model", self.model_name, chunks=1)


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def norm(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def correct(item, response):
    return int(any(norm(answer) in norm(response) for answer in item["answers"]))


def build(ctx, question, nonce):
    return f"[req:{nonce}]\n{INSTR}\n\nDocument:\n{ctx}\n\nQuestion: {question}\nAnswer:"


def ask(prompt):
    body = json.dumps(dict(model=MODEL, messages=[dict(role="user", content=prompt)], stream=False, options=OPTIONS, keep_alive="120m")).encode()
    request = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=900) as response:
        reply = json.loads(response.read())
    return reply["message"]["content"], time.perf_counter() - started


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def mcnemar(a, b):
    from scipy import stats

    only_a = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    only_b = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    n = only_a + only_b
    return (1.0 if n == 0 else float(stats.binomtest(min(only_a, only_b), n, 0.5).pvalue)), only_a, only_b


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--families", default="qa,logs,code")
    parser.add_argument("--conditions", default=None, help="comma list; default is the per-family plan")
    parser.add_argument("--detector", choices=["real", "rules"], default="real")
    args = parser.parse_args()
    families = args.families.split(",")
    out_raw = RAW_DIR / f"runs_{args.detector}.jsonl"
    out_md = RESULTS_DIR / f"guard_eval_{args.detector}.md"

    base_runs = {r["item_id"]: r for r in load_jsonl(RESEARCH / "raw" / "llm_runs.jsonl") if r["arm"] == "base"}
    settings0 = dataclasses.replace(PipelineSettings.from_env(), mode="enforce", eager_load=False, min_chars=200, protect_edges=True)
    compressor = LLMLinguaCompressor(settings0.compression_model)
    started_loading = time.perf_counter()
    compressor.load()
    print(f"LLMLingua-2 loaded in {time.perf_counter() - started_loading:.1f}s", flush=True)

    detector = RulesOnlyDetector() if args.detector == "rules" else SensitivityDetector(SensitivitySettings.from_env())
    detector.load()
    pipelines = {}
    for name, (routes, overrides) in CONDITIONS.items():
        pipelines[name] = PromptPipeline(
            settings=dataclasses.replace(settings0, routes=routes, **overrides), detector=detector, compressor=compressor
        )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    done = {}
    if out_raw.exists():
        for row in load_jsonl(out_raw):
            done[(row["item_id"], row["condition"])] = row
    out = out_raw.open("a", encoding="utf-8")

    rows = []
    for family in families:
        items = load_jsonl(RESEARCH / "data" / f"{family}.jsonl")[: args.limit]
        plan = args.conditions.split(",") if args.conditions else DEFAULT_PLAN[family]
        for item in items:
            base_response = base_runs[item["id"]]["response"]
            base_ok = correct(item, base_response)
            rows.append(dict(item_id=item["id"], family=family, condition="base", ok=base_ok, changed=False, tokens_before=None,
                             tokens_after=None, process_ms=0.0, actions="", response=base_response, asked=False))
            for condition in plan:
                key = (item["id"], condition)
                if key in done:
                    rows.append(done[key])
                    continue
                original = build(item["context"], item["question"], "0" * 8)
                messages = [{"role": "user", "content": original}]
                new_messages, report = pipelines[condition].process(messages)
                changed = new_messages[0]["content"] != original
                if changed:
                    response, seconds = ask(new_messages[0]["content"])
                else:
                    response, seconds = base_response, 0.0
                row = dict(item_id=item["id"], family=family, condition=condition, ok=correct(item, response), changed=changed,
                           tokens_before=report.tokens_before, tokens_after=report.tokens_after, process_ms=report.elapsed_ms,
                           actions=report.messages[0].get("action", ""), segments=report.segments, response=response,
                           asked=changed, llm_seconds=round(seconds, 2))
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
                rows.append(row)
        print(f"done {family}", flush=True)
    out.close()
    write_summary(rows, families, args.detector, out_md)


def write_summary(rows, families, detector, out_md):
    lines = [
        f"# Pipeline evaluation (local), sensitivity check: {detector}",
        "",
        f"Real pipeline, real LLMLingua-2 on CPU, target {MODEL} through Ollama, the report's prompts and baseline "
        "(reports/compression-fit/raw/llm_runs.jsonl). Accuracy = the "
        "reference string appears in the answer; Wilson 95% interval; exact McNemar against the baseline on the same items. "
        "A prompt the router leaves byte for byte unchanged reuses the baseline answer (column 'prompt changed').",
        "",
        "| family | condition | items | accuracy [95% Wilson] | diff vs baseline | McNemar p | prompt changed | token ratio | router ms, mean |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for family in families:
        base = {r["item_id"]: r for r in rows if r["family"] == family and r["condition"] == "base"}
        if not base:
            continue
        conditions = []
        for r in rows:
            if r["family"] == family and r["condition"] != "base" and r["condition"] not in conditions:
                conditions.append(r["condition"])
        k = sum(r["ok"] for r in base.values())
        lo, hi = wilson(k, len(base))
        lines.append(f"| {family} | baseline (uncompressed) | {len(base)} | {k / len(base):.3f} [{lo:.3f}, {hi:.3f}] | - | - | - | 1.00x | - |")
        for condition in conditions:
            sel = {r["item_id"]: r for r in rows if r["family"] == family and r["condition"] == condition}
            ids = [i for i in base if i in sel]
            ok = [sel[i]["ok"] for i in ids]
            b = [base[i]["ok"] for i in ids]
            k = sum(ok)
            lo, hi = wilson(k, len(ids))
            p, only_base, only_cond = mcnemar(b, ok)
            changed = sum(1 for i in ids if sel[i]["changed"])
            before = sum(sel[i]["tokens_before"] for i in ids)
            after = sum(sel[i]["tokens_after"] for i in ids)
            ms = sum(sel[i]["process_ms"] for i in ids) / len(ids)
            lines.append(
                f"| {family} | {condition} | {len(ids)} | {k / len(ids):.3f} [{lo:.3f}, {hi:.3f}] | {(k - sum(b)) / len(ids):+.3f} "
                f"| {p:.3f} | {changed}/{len(ids)} | {before / after:.2f}x | {ms:.0f} |"
            )
    pii_path = RESEARCH / "data" / "pii.jsonl"
    if pii_path.exists():
        records = load_jsonl(pii_path)
        flagged = sum(1 for r in records if rules.rule_hits(r["context"]))
        lines += ["", f"Sensitive records: the deterministic rules alone flag {flagged} of {len(records)} synthetic case notes, "
                      "which the pipeline then never compresses (the NLI classifier adds to this)."]
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
