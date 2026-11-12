"""Shared helpers for the context-engineering benchmark: configurations, scoring, token accounting, statistics."""

import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GATEWAY = HERE.parents[2]
RAW = ROOT / "raw"
DATA = ROOT / "data" / "bench.jsonl"
if str(GATEWAY) not in sys.path:
    sys.path.insert(0, str(GATEWAY))

# The four configurations, selected per request with the two stages' opt-out flags, so one gateway process serves all
# four with identical settings, models and load.
CONFIGS = {
    "baseline": {"context_engineering": False, "prompt_compression": False},
    "compression": {"context_engineering": False},
    "context_engineering": {"prompt_compression": False},
    "combined": {},
}

# Settings profiles of the context-engineering stage.
#   default  the shipped defaults: budget, duplicate folding, masking, cache-aware construction; JIT and compaction off;
#            window from LiteLLM's model map (131,072 tokens for llama3.2:3b)
#   full     every technique on, with a constrained 6,000-token effective window so the history techniques have
#            something to do at these conversation sizes; JIT allowed although the target caches prefixes locally
PROFILES = {
    "default": {},
    "full": {"compaction_enabled": True, "jit_enabled": True, "jit_on_caching_providers": True, "window_tokens": 6000},
}
PROFILE_ENV = {
    "default": {},
    "full": {"CONTEXT_COMPACTION_ENABLED": "true", "JIT_RETRIEVAL_ENABLED": "true",
             "JIT_RETRIEVAL_ON_CACHING_PROVIDERS": "true", "CONTEXT_WINDOW_TOKENS": "6000"},
}
MAX_TOKENS = 48


def load_items(families=None, ids=None) -> list:
    rows = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line.strip()]
    if families:
        rows = [r for r in rows if r["family"] in families]
    if ids:
        rows = [r for r in rows if r["id"] in ids]
    return rows


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def context_text(messages: list) -> str:
    parts = []
    for m in messages:
        content = m.get("content")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            parts += [p.get("text", "") for p in content if isinstance(p, dict)]
        for call in m.get("tool_calls") or []:
            parts.append(json.dumps(call))
    return "\n".join(parts)


def correct(item: dict, answer: str) -> int:
    return int(any(norm(a) in norm(answer) for a in item["answers"]))


def completeness(item: dict, answer: str) -> float:
    wanted = item.get("complete") or item["answers"]
    return sum(1 for w in wanted if norm(w) in norm(answer)) / len(wanted)


def follows_instruction(item: dict, answer: str):
    """Multi-turn items ask for every answer to start with 'Answer:'; None where the item gives no such instruction."""
    first_user = next((m for m in item["messages"] if m["role"] == "user"), {})
    if "Start every answer with 'Answer:'" not in str(first_user.get("content")):
        return None
    return int((answer or "").strip().lower().startswith("answer:"))


def key_strings_kept(item: dict, messages: list) -> float:
    text = context_text(messages)
    keys = item.get("key_strings") or []
    return sum(1 for k in keys if k in text) / len(keys) if keys else 1.0


def answer_in_context(item: dict, messages: list) -> int:
    text = norm(context_text(messages))
    return int(any(norm(a) in text for a in item["answers"]))


def common_prefix_tokens(a: list, b: list, count) -> int:
    """Tokens of the longest run of leading messages that are byte-identical in two requests (the part a provider's
    prefix cache can reuse, at message granularity)."""
    total = 0
    for x, y in zip(a, b):
        if json.dumps(x, sort_keys=True) != json.dumps(y, sort_keys=True):
            break
        total += count(x)
    return total


def pct(values: list, q: float):
    if not values:
        return None
    values = sorted(values)
    k = (len(values) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def summary(values: list) -> dict:
    values = [v for v in values if v is not None]
    if not values:
        return {"n": 0}
    return {"n": len(values), "mean": round(statistics.fmean(values), 2), "p50": round(pct(values, 0.5), 2),
            "p90": round(pct(values, 0.9), 2), "p95": round(pct(values, 0.95), 2), "max": round(max(values), 2)}


def write_jsonl(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def read_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
