"""In-process benchmark: the gateway's two real hooks, chained exactly as LiteLLM chains them, with the real models
(MiniLM sensitivity head, LLMLingua-2), over every benchmark item, for the four configurations and both settings
profiles, cold (first pass, empty caches) and warm (second pass). No LLM is called.

    .venv-compression/Scripts/python reports/context-engineering/scripts/offline_bench.py
writes raw/offline.jsonl (one row per item x config x profile x pass) and raw/offline_env.json.

Token counts are context_engineering.tokens.messages_tokens (cl100k_base text + tool-call arguments + 4 per message),
applied to the original request and to what would reach the provider.
"""

import asyncio
import copy
import dataclasses
import json
import os
import platform
import sys
import time

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from bench_lib import CONFIGS, MAX_TOKENS, PROFILES, RAW, context_text, answer_in_context, key_strings_kept, \
    load_items, write_jsonl  # noqa: E402

from context_engineering.callback import ContextEngineeringCallback  # noqa: E402
from context_engineering.engine import ContextEngine  # noqa: E402
from context_engineering.settings import ContextSettings  # noqa: E402
from context_engineering.store import MemoryStore  # noqa: E402
from context_engineering.tokens import messages_tokens  # noqa: E402
from prompt_compression.prompt_compression_callback import PromptCompressionCallback  # noqa: E402

MODEL = "ollama_chat/llama3.2:3b"


async def run_one(ce, pc, item, metadata):
    data = {"model": MODEL, "messages": copy.deepcopy(item["messages"]), "max_tokens": MAX_TOKENS,
            "metadata": copy.deepcopy(metadata)}
    started = time.perf_counter()
    data = await ce.async_pre_call_hook(user_api_key_dict=None, cache=None, data=data, call_type="acompletion")
    middle = time.perf_counter()
    data = await pc.async_pre_call_hook(user_api_key_dict=None, cache=None, data=data, call_type="acompletion")
    ended = time.perf_counter()
    return data, (middle - started) * 1000, (ended - middle) * 1000


def row_for(item, config, profile, pass_name, data, ce_ms, pc_ms):
    meta = data.get("metadata") or {}
    ce = meta.get("context_engineering") or {}
    pc = meta.get("prompt_compression") or {}
    final = data["messages"]
    before = messages_tokens(item["messages"])
    after = messages_tokens(final)
    retrieved = [h for h in ce.get("history") or [] if h.get("action") == "retrieved"]
    needle = item.get("needle") or ""
    original_by_index = {i: context_text([m]) for i, m in enumerate(item["messages"])}
    retrieved_with_needle = sum(1 for h in retrieved if any(needle in original_by_index.get(i, "")
                                                            for i in h.get("original_indexes", [])))
    pc_removed = 0
    if pc.get("status") == "ok":
        pc_removed = max(0, int(pc.get("tokens_before") or 0) - int(pc.get("tokens_after") or 0))
    return {
        "item": item["id"], "family": item["family"], "variant": item.get("variant", ""), "config": config,
        "profile": profile, "pass": pass_name, "ce_expected": item.get("ce_expected"),
        "tokens_before": before, "tokens_after": after,
        "ce_status": ce.get("status"), "ce_reason": ce.get("reason"), "ce_tokens_saved": ce.get("tokens_saved", 0),
        "ce_saved_by_technique": ce.get("saved_by_technique") or {}, "ce_elapsed_ms": ce.get("elapsed_ms"),
        "ce_stage_ms": ce.get("stage_ms") or {}, "ce_hook_ms": round(ce_ms, 2),
        "pc_status": pc.get("status"), "pc_reason": pc.get("reason"), "pc_removed": pc_removed,
        "pc_elapsed_ms": pc.get("elapsed_ms"), "pc_hook_ms": round(pc_ms, 2), "pc_compress_calls": pc.get("compress_calls"),
        "pc_ratio_cap_hits": (pc.get("segments") or {}).get("ratio_cap_hits", 0), "pc_stopped": pc.get("compress_stopped"),
        "masked": len(ce.get("masked") or []), "history_actions": [h.get("action") for h in ce.get("history") or []],
        "summary_source": ce.get("summary_source"), "retrieved": len(retrieved),
        "retrieved_with_needle": retrieved_with_needle,
        "invariant_violations": ce.get("invariant_violations") or [], "stages_failed": ce.get("stages_failed") or [],
        "key_strings_kept": key_strings_kept(item, final), "answer_in_context": answer_in_context(item, final),
        "utilization_before": ce.get("utilization_before"), "utilization_after": ce.get("utilization_after"),
        "pressure": ce.get("pressure"), "caching": ce.get("caching"),
    }


def clear_caches(pc) -> None:
    for component in (pc._pipeline.compressor, pc._pipeline.detector):
        cache = getattr(component, "_cache", None)
        lock = getattr(component, "_cache_lock", None)
        if cache is not None and hasattr(cache, "clear"):
            if lock is not None:
                with lock:
                    cache.clear()
            else:
                cache.clear()


async def main():
    items = load_items()
    pc = PromptCompressionCallback()          # real models, loaded at construction (eager load)
    rows = []
    for profile, overrides in PROFILES.items():
        settings = dataclasses.replace(ContextSettings.from_env(), **overrides)
        ce = ContextEngineeringCallback(engine=ContextEngine(settings, store=MemoryStore()), settings=settings)
        # cold: compression's caches (compressed outputs, sensitivity verdicts) are emptied before every request, so no
        # configuration profits from another's work. warm: the same request again, straight after (a repeated turn).
        for item in items:
            for config, metadata in CONFIGS.items():
                clear_caches(pc)
                data, ce_ms, pc_ms = await run_one(ce, pc, item, metadata)
                rows.append(row_for(item, config, profile, "cold", data, ce_ms, pc_ms))
                data, ce_ms, pc_ms = await run_one(ce, pc, item, metadata)
                rows.append(row_for(item, config, profile, "warm", data, ce_ms, pc_ms))
        print(f"profile={profile}: {len(rows)} rows", flush=True)
    write_jsonl(RAW / "offline.jsonl", rows)
    env = {"python": sys.version.split()[0], "platform": platform.platform(), "processor": platform.processor(),
           "cpus": os.cpu_count(), "model_for_budget": MODEL, "profiles": PROFILES,
           "compression": {k: (sorted(v) if isinstance(v, frozenset) else v)
                           for k, v in dataclasses.asdict(pc.settings).items()},
           "classifier": pc._pipeline.detector.model_name, "compressor": pc._pipeline.compressor.model_name}
    (RAW / "offline_env.json").write_text(json.dumps(env, indent=1, default=str), encoding="utf-8")
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
