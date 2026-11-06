"""Where do the tokens go? Runs the real pipeline in-process (same code and models as the gateway, no LLM call) over the
benchmark prompts and attributes every prompt token (cl100k) to the router's decision for its block.

    .venv-compression/Scripts/python reports/playground-ab/scripts/token_budget.py [--tag before]
Writes raw/token_budget_<tag>.json and prints a per-family table.
"""

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATEWAY = HERE.parents[2]
sys.path.insert(0, str(GATEWAY))
sys.path.insert(0, str(HERE))
from ab_eval import build_prompt, load_items  # noqa: E402
from prompt_compression import router  # noqa: E402
from prompt_compression.pipeline import PromptPipeline, _tail_paragraph  # noqa: E402
from prompt_compression.settings import PipelineSettings  # noqa: E402
from prompt_compression.texts import count_tokens, text_parts  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tag", default="before")
    p.add_argument("--families", nargs="+", default=["qa", "logs", "code", "pii"])
    a = p.parse_args()
    settings = PipelineSettings.from_env()
    pipe = PromptPipeline(settings=settings)
    pipe.load()
    out = {"settings": {"routes": sorted(settings.routes), "rate": settings.rate, "max_ratio": settings.max_ratio,
                        "min_chars": settings.min_chars, "exact_density": settings.exact_density,
                        "threshold": pipe.detector.threshold, "classifier": pipe.detector.model_name}, "families": {}}
    examples = defaultdict(list)
    for fam in a.families:
        items = load_items([fam])
        by_reason = Counter()
        kinds = Counter()
        before = after = 0
        ms = []
        cats = Counter()
        for item in items:
            prompt = build_prompt(item, "0" * 8)
            messages = [{"role": "user", "content": prompt}]
            # attribution: segment + classify + route exactly as process() does
            units = pipe._segment(0, text_parts(messages[0]))
            pipe._classify(units, use_model=True)
            query = _tail_paragraph(prompt)
            plan = router.route(units, settings, query, 0, count_tokens)
            for u in units:
                t = count_tokens(u.full)
                key = u.reason if u.action == "keep" else f"{u.action}:{u.reason}"
                if u.sensitive:
                    key = f"keep:sensitive({u.sensitive_source})"
                by_reason[key] += t
                kinds[u.kind] += t
            if len(examples[fam]) < 3:
                examples[fam].append([{"kind": u.kind, "reason": u.reason, "action": u.action, "sensitive": u.sensitive,
                                       "src": u.sensitive_source, "text": u.text[:90]} for u in units])
            # real outcome
            started = time.perf_counter()
            new, report = pipe.process(messages)
            ms.append((time.perf_counter() - started) * 1000)
            before += report.tokens_before
            after += report.tokens_after
            cats[report.request_category] += 1
        total = sum(by_reason.values())
        out["families"][fam] = {
            "n": len(items), "tokens_before": before, "tokens_after": after,
            "ratio": round(before / after, 3) if after else None, "saved_pct": round(100 * (before - after) / before, 1),
            "share_by_decision_pct": {k: round(100 * v / total, 1) for k, v in by_reason.most_common()},
            "share_by_kind_pct": {k: round(100 * v / total, 1) for k, v in kinds.most_common()},
            "request_category": dict(cats), "pipeline_ms_mean": round(sum(ms) / len(ms), 1),
        }
        f = out["families"][fam]
        print(f"\n== {fam}: {before} -> {after} tokens, ratio {f['ratio']}, saved {f['saved_pct']}%, "
              f"{f['pipeline_ms_mean']} ms/prompt, category {dict(cats)}")
        print("   token share by decision:", f["share_by_decision_pct"])
        print("   token share by kind    :", f["share_by_kind_pct"])
    out["examples"] = examples
    (GATEWAY / "reports" / "playground-ab" / "raw" / f"token_budget_{a.tag}.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
