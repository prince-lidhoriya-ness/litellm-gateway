"""Turns the raw benchmark rows into the tables of REPORT.md (raw/results.md) and raw/results.json.

    .venv-compression/Scripts/python reports/context-engineering/scripts/analyze.py

Formulas (as in the brief):
  token reduction %      = (original input tokens - optimised input tokens) / original input tokens x 100
  cost savings %         = (baseline cost - optimised cost) / baseline cost x 100
  latency improvement %  = (baseline latency - optimised latency) / baseline latency x 100
Prices are LiteLLM 1.106.0's bundled model map (litellm.model_cost), read at run time and printed with the tables.
"""

import json
import os
from collections import defaultdict

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

from bench_lib import CONFIGS, MAX_TOKENS, RAW, read_jsonl, summary  # noqa: E402

CONFIG_NAMES = list(CONFIGS)
LABEL = {"baseline": "Baseline", "compression": "Existing (compression only)",
         "context_engineering": "Context engineering only", "combined": "Combined (CE + compression)"}
PRICED_MODELS = ["gpt-4o-mini", "claude-sonnet-4-5"]
CPU_RATE_USD_PER_HOUR = 0.10      # observability's OBS_CPU_HOURLY_RATE_USD default, for the local compute overhead


def pct_change(before, after):
    return round(100.0 * (before - after) / before, 1) if before else 0.0


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join("" if c is None else str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def prices():
    import litellm

    out = {}
    for name in PRICED_MODELS:
        info = litellm.model_cost.get(name) or {}
        out[name] = {"input": info.get("input_cost_per_token"), "output": info.get("output_cost_per_token"),
                     "cache_read": info.get("cache_read_input_token_cost"),
                     "cache_write": info.get("cache_creation_input_token_cost")}
    out["bench-llama (test prices)"] = {"input": 1e-6, "output": 2e-6, "cache_read": None, "cache_write": None}
    return out


def offline_section(md, results):
    rows = read_jsonl(RAW / "offline.jsonl")
    if not rows:
        return
    for profile in ("default", "full"):
        cold = [r for r in rows if r["profile"] == profile and r["pass"] == "cold"]
        families = sorted({r["family"] for r in cold}, key=lambda f: [r["family"] for r in cold].index(f))
        md.append(f"\n### Input tokens by family, profile `{profile}` (in-process, cold)\n")
        header = ["Family", "Items", "Original"] + [f"{LABEL[c]}" for c in CONFIG_NAMES[1:]]
        body = []
        totals = defaultdict(lambda: [0, 0])
        for family in families + ["ALL"]:
            fam_rows = cold if family == "ALL" else [r for r in cold if r["family"] == family]
            original = sum(r["tokens_before"] for r in fam_rows if r["config"] == "baseline")
            cells = [family, len({r["item"] for r in fam_rows}), original]
            for config in CONFIG_NAMES[1:]:
                final = sum(r["tokens_after"] for r in fam_rows if r["config"] == config)
                cells.append(f"{final} ({pct_change(original, final):+.1f}% saved)".replace("+", ""))
                if family == "ALL":
                    totals[config] = [original, final]
            body.append(cells)
        md.append(table(header, body))
        results.setdefault("tokens", {})[profile] = {c: {"original": v[0], "final": v[1],
                                                         "reduction_pct": pct_change(*v)} for c, v in totals.items()}

        combined = [r for r in cold if r["config"] == "combined"]
        attribution = defaultdict(int)
        for r in combined:
            for technique, tokens in (r["ce_saved_by_technique"] or {}).items():
                attribution[technique] += tokens
            attribution["prompt_compression"] += r["pc_removed"]
        original = sum(r["tokens_before"] for r in combined)
        final = sum(r["tokens_after"] for r in combined)
        md.append(f"\n**Attribution, profile `{profile}`, combined configuration** (each stage measured on the previous "
                  f"stage's output, so the parts add up; total {original - final} of {original} tokens):\n")
        md.append(table(["Technique", "Tokens saved", "Share of original input"],
                        [[t, v, f"{100 * v / original:.1f}%"] for t, v in sorted(attribution.items(), key=lambda x: -x[1])]))
        results.setdefault("attribution", {})[profile] = dict(attribution)

    md.append("\n### Optimisation overhead (in-process, ms per request)\n")
    body = []
    for profile in ("default", "full"):
        for pass_name in ("cold", "warm"):
            for config in CONFIG_NAMES[1:]:
                sel = [r for r in rows if r["profile"] == profile and r["pass"] == pass_name and r["config"] == config]
                ce = summary([r["ce_hook_ms"] for r in sel if config in ("context_engineering", "combined")])
                pc = summary([r["pc_hook_ms"] for r in sel if config in ("compression", "combined")])
                total = summary([r["ce_hook_ms"] + r["pc_hook_ms"] for r in sel])
                body.append([profile, pass_name, LABEL[config], _p(ce), _p(pc), _p(total)])
                results.setdefault("overhead", {}).setdefault(profile, {}).setdefault(pass_name, {})[config] = total
    md.append(table(["Profile", "Pass", "Configuration", "CE hook p50 / p90 / p95", "Compression hook p50 / p90 / p95",
                     "Total p50 / p90 / p95"], body))

    full_ce = [r for r in rows if r["profile"] == "full" and r["pass"] == "cold" and r["config"] == "combined"]
    history_ms = [r["ce_stage_ms"].get("history", 0) for r in full_ce if r["history_actions"]]
    mask_ms = [r["ce_stage_ms"].get("mask", 0) for r in full_ce if r["masked"]]
    md.append("\nStage latency inside the CE hook (profile `full`, cold, requests where the stage acted): masking "
              f"{_p(summary(mask_ms))} ms; retrieval + compaction {_p(summary(history_ms))} ms.\n")
    results["stage_ms"] = {"masking": summary(mask_ms), "history": summary(history_ms)}

    md.append("\n### Context checks (in-process, cold; deterministic, no model)\n")
    body = []
    for profile in ("default", "full"):
        for config in CONFIG_NAMES:
            sel = [r for r in rows if r["profile"] == profile and r["pass"] == "cold" and r["config"] == config]
            structured = [r for r in sel if r["family"] in ("code", "log_lookup", "structured_chat", "agent_debug")]
            body.append([profile, LABEL[config],
                         f"{100 * sum(r['key_strings_kept'] for r in structured) / len(structured):.1f}%",
                         f"{100 * sum(r['answer_in_context'] for r in sel) / len(sel):.1f}%",
                         sum(len(r["invariant_violations"]) for r in sel), sum(len(r["stages_failed"]) for r in sel)])
    md.append(table(["Profile", "Configuration", "Key strings kept (code/log/JSON/debug)", "Answer still in context",
                     "Invariant violations", "Stages undone"], body))

    md.append("\n**Answer still in context, by family and variant (profile `full`, cold):**\n")
    body = []
    groups = sorted({(r["family"], r["variant"]) for r in rows})
    for family, variant in groups:
        sel = [r for r in rows if r["profile"] == "full" and r["pass"] == "cold" and r["family"] == family
               and r["variant"] == variant]
        body.append([family, variant or "-"] + [
            f"{sum(r['answer_in_context'] for r in sel if r['config'] == c)}/{sum(1 for r in sel if r['config'] == c)}"
            for c in CONFIG_NAMES])
    md.append(table(["Family", "Variant"] + [LABEL[c] for c in CONFIG_NAMES], body))

    noop = [r for r in rows if r["pass"] == "cold" and not r["ce_expected"] and r["config"] == "context_engineering"]
    changed = [r for r in noop if r["tokens_after"] != r["tokens_before"]]
    md.append(f"\nRequests where context engineering should not act (short chats, single-turn QA/logs/code, the "
              f"structured chat below the size gate): {len(noop)} (both profiles); changed by the CE stage: "
              f"{len(changed)}.\n")
    results["noop"] = {"requests": len(noop), "changed": len(changed)}

    retr = [r for r in rows if r["profile"] == "full" and r["pass"] == "cold" and r["config"] == "combined"
            and r["family"] == "long_chat"]
    old = [r for r in retr if r["variant"] == "old"]
    md.append(f"\n**JIT retrieval (profile `full`, long chats):** turns retrieved {sum(r['retrieved'] for r in retr)} in "
              f"{len(retr)} requests; retrieved turns holding the asked-for fact: "
              f"{sum(r['retrieved_with_needle'] for r in retr)}; old-fact questions whose fact turn was retrieved: "
              f"{sum(1 for r in old if r['retrieved_with_needle'])}/{len(old)}.\n")
    results["retrieval"] = {"requests": len(retr), "retrieved": sum(r["retrieved"] for r in retr),
                            "with_needle": sum(r["retrieved_with_needle"] for r in retr),
                            "old_fact_recall": f"{sum(1 for r in old if r['retrieved_with_needle'])}/{len(old)}"}


def _p(s):
    return f"{s['p50']} / {s['p90']} / {s['p95']}" if s.get("n") else "-"


def cost_section(md, results):
    rows = read_jsonl(RAW / "offline.jsonl")
    quality = read_jsonl(RAW / "quality.jsonl")
    if not rows:
        return
    out_tokens = [((q.get("usage") or {}).get("completion_tokens")) for q in quality]
    out_tokens = [t for t in out_tokens if t]
    mean_out = sum(out_tokens) / len(out_tokens) if out_tokens else MAX_TOKENS
    table_prices = prices()
    results["prices"] = table_prices
    md.append(f"\n### API cost per 1,000 requests of this dataset mix (profile `full`, cold token counts; output "
              f"{mean_out:.1f} tokens per request, the quality run's mean)\n")
    body = []
    for model, p in table_prices.items():
        if not p["input"]:
            continue
        base = None
        for config in CONFIG_NAMES:
            sel = [r for r in rows if r["profile"] == "full" and r["pass"] == "cold" and r["config"] == config]
            per_request = sum(r["tokens_after"] for r in sel) / len(sel) * p["input"] + mean_out * p["output"]
            cost = per_request * 1000
            base = cost if config == "baseline" else base
            body.append([model, LABEL[config], f"${cost:.4f}", f"{pct_change(base, cost):.1f}%"])
            results.setdefault("cost", {}).setdefault(model, {})[config] = round(cost, 6)
    md.append(table(["Price list", "Configuration", "Cost / 1k requests", "Savings vs baseline"], body))
    prep = [r["ce_hook_ms"] + r["pc_hook_ms"] for r in rows
            if r["profile"] == "full" and r["pass"] == "cold" and r["config"] == "combined"]
    overhead_usd = sum(prep) / len(prep) / 1000 / 3600 * CPU_RATE_USD_PER_HOUR * 1000
    md.append(f"\nLocal optimisation compute (combined, cold, mean {sum(prep) / len(prep):.0f} ms of one CPU-bound "
              f"worker per request) at ${CPU_RATE_USD_PER_HOUR}/CPU-hour: ${overhead_usd:.4f} per 1,000 requests.\n")
    results["overhead_usd_per_1k"] = overhead_usd
    md.append("\nPrices per token (LiteLLM 1.106.0 bundled model map): " + "; ".join(
        f"{m}: in {p['input']}, out {p['output']}, cache read {p['cache_read']}, cache write {p['cache_write']}"
        for m, p in table_prices.items()) + ".\n")


def proxy_section(md, results):
    rows = read_jsonl(RAW / "proxy.jsonl") + read_jsonl(RAW / "proxy_reversed.jsonl")
    runs = []
    for name in ("proxy_runs.json", "proxy_reversed_runs.json"):
        if (RAW / name).exists():
            runs += json.loads((RAW / name).read_text(encoding="utf-8"))
    if not rows:
        return
    md.append("\n### End-to-end gateway latency and throughput (proxy + echo provider, profile `full`)\n")
    md.append("`first`: a fresh proxy, configurations in the order baseline, compression, CE, combined, with caches shared "
              "across them, so later configurations profit from earlier ones' cached work. `first_reversed`: another "
              "fresh proxy, order combined, CE, compression, baseline (so combined and CE are cold here). `repeat`: "
              "the same requests again (warm). `c8`: warm, 8 concurrent clients.\n")
    body = []
    for pass_name in ("first", "first_reversed", "repeat", "c8"):
        base_p50 = None
        for config in CONFIG_NAMES:
            sel = [r for r in rows if r["pass"] == pass_name and r["config"] == config]
            lat = summary([r["latency_ms"] for r in sel if not r["error"]])
            run = next((x for x in runs if x["pass"] == pass_name and x["config"] == config), {})
            base_p50 = lat.get("p50") if config == "baseline" else base_p50
            errors = sum(1 for r in sel if r["error"])
            body.append([pass_name, sel[0]["concurrency"] if sel else "", LABEL[config], lat.get("mean"), lat.get("p50"),
                         lat.get("p90"), lat.get("p95"), run.get("rps"), f"{100 * errors / max(1, len(sel)):.1f}%"])
            results.setdefault("proxy", {}).setdefault(pass_name, {})[config] = {**lat, "rps": run.get("rps"),
                                                                                  "errors": errors}
    md.append(table(["Pass", "Concurrency", "Configuration", "Mean ms", "p50 ms", "p90 ms", "p95 ms", "Req/s",
                     "Errors"], body))
    tok = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["pass"] == "repeat" and r.get("tokens_forwarded") is not None:
            tok[r["config"]][0] += r["tokens_original"]
            tok[r["config"]][1] += r["tokens_forwarded"]
    md.append("\nTokens that reached the provider (repeat pass, measured on the echo): " + "; ".join(
        f"{LABEL[c]} {v[1]} of {v[0]} ({pct_change(*v):.1f}% saved)" for c, v in tok.items()) + ".\n")
    results["proxy_tokens"] = {c: {"original": v[0], "forwarded": v[1]} for c, v in tok.items()}


def quality_section(md, results):
    rows = [r for r in read_jsonl(RAW / "quality.jsonl") if not r.get("error")]
    errors = [r for r in read_jsonl(RAW / "quality.jsonl") if r.get("error")]
    if not rows:
        return
    items = sorted({r["item"] for r in rows})
    complete = [i for i in items if all(any(r["item"] == i and r["config"] == c for r in rows) for c in CONFIG_NAMES)]
    rows = [r for r in rows if r["item"] in complete]
    md.append(f"\n### Answer quality, local llama3.2:3b (Ollama, CPU), {len(complete)} items x 4 configurations\n")
    body = []
    base_lat = None
    base_prompt = None
    for config in CONFIG_NAMES:
        sel = [r for r in rows if r["config"] == config]
        instr = [r["instruction"] for r in sel if r["instruction"] is not None]
        lat = summary([r["latency_ms"] / 1000 for r in sel])
        prompt = sum((r.get("usage") or {}).get("prompt_tokens") or 0 for r in sel)
        base_lat = lat["mean"] if config == "baseline" else base_lat
        base_prompt = prompt if config == "baseline" else base_prompt
        body.append([LABEL[config], f"{sum(r['correct'] for r in sel)}/{len(sel)}",
                     f"{100 * sum(r['completeness'] for r in sel) / len(sel):.1f}%",
                     f"{sum(instr)}/{len(instr)}", prompt, f"{pct_change(base_prompt, prompt):.1f}%",
                     lat["mean"], lat["p50"], lat["p95"], f"{pct_change(base_lat, lat['mean']):.1f}%"])
        results.setdefault("quality", {})[config] = {
            "correct": sum(r["correct"] for r in sel), "n": len(sel),
            "completeness": round(sum(r["completeness"] for r in sel) / len(sel), 3),
            "instruction": f"{sum(instr)}/{len(instr)}", "provider_prompt_tokens": prompt, "latency_s": lat}
    md.append(table(["Configuration", "Correct", "Completeness", "Instruction following", "Provider prompt tokens",
                     "Saved", "Mean s", "p50 s", "p95 s", "Latency improvement"], body))
    md.append("\n**Correct answers by family and variant:**\n")
    groups = sorted({(r["family"], r["variant"]) for r in rows})
    md.append(table(["Family", "Variant"] + [LABEL[c] for c in CONFIG_NAMES], [
        [f, v or "-"] + [f"{sum(r['correct'] for r in rows if r['family'] == f and r['variant'] == v and r['config'] == c)}"
                         f"/{sum(1 for r in rows if r['family'] == f and r['variant'] == v and r['config'] == c)}"
                         for c in CONFIG_NAMES] for f, v in groups]))
    flips = []
    for i in complete:
        base = next(r for r in rows if r["item"] == i and r["config"] == "baseline")
        for c in CONFIG_NAMES[1:]:
            other = next(r for r in rows if r["item"] == i and r["config"] == c)
            if other["correct"] != base["correct"]:
                flips.append(f"{i} {c}: baseline {base['correct']} -> {other['correct']}")
    md.append("\nAnswers that differ from the baseline: " + ("; ".join(flips) if flips else "none") +
              f". Request errors: {len(errors)}.\n")
    results["quality_flips"] = flips


def cache_section(md, results):
    rows = read_jsonl(RAW / "cache.jsonl")
    if not rows:
        return
    md.append("\n### Prefix reuse between consecutive turns (turn N, then N+1 of the same conversation)\n")
    body = []
    for config in CONFIG_NAMES:
        sel = [r for r in rows if r["config"] == config]
        n1 = sum(r["tokens_n1"] for r in sel)
        common = sum(r["common_prefix_tokens"] for r in sel)
        cold = [r["ollama_n"]["prompt_eval_s"] for r in sel if "ollama_n" in r]
        warm = [r["ollama_n1"]["prompt_eval_s"] for r in sel if "ollama_n1" in r]
        body.append([LABEL[config], n1, f"{common} ({100 * common / n1:.1f}%)",
                     round(sum(cold), 1) if cold else "-", round(sum(warm), 1) if warm else "-"])
        results.setdefault("cache", {})[config] = {"tokens_n1": n1, "common_prefix": common,
                                                   "ollama_prompt_eval_s_n": sum(cold), "ollama_prompt_eval_s_n1": sum(warm)}
    md.append(table(["Configuration", "Turn N+1 tokens (sum)", "Byte-identical prefix shared with turn N",
                     "Ollama prompt eval, turn N (s, cold)", "Ollama prompt eval, turn N+1 (s)"], body))
    p = prices().get("claude-sonnet-4-5", {})
    if p.get("input") and p.get("cache_read"):
        md.append("\nEstimated input cost of the turn-N+1 requests at claude-sonnet-4-5 prices, if the provider caches "
                  "the shared prefix (written on turn N, read on N+1): ")
        parts = []
        for config in CONFIG_NAMES:
            sel = [r for r in rows if r["config"] == config]
            n1 = sum(r["tokens_n1"] for r in sel)
            common = sum(r["common_prefix_tokens"] for r in sel)
            no_cache = n1 * p["input"]
            cached = common * p["cache_read"] + (n1 - common) * p["input"]
            parts.append(f"{LABEL[config]} ${no_cache:.4f} uncached, ${cached:.4f} with cache")
        md.append("; ".join(parts) + ".\n")


def main():
    md = ["# Benchmark results (generated by scripts/analyze.py)\n"]
    results = {}
    offline_section(md, results)
    cost_section(md, results)
    proxy_section(md, results)
    quality_section(md, results)
    cache_section(md, results)
    (RAW / "results.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (RAW / "results.json").write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
