"""Shared helpers for the pipeline-proof suite: paths, template expansion, key-fact extraction, stats.

Key-shaped test secrets are stored in the suite as templates ({{FAKE_OPENAI_KEY}} ...) and
expanded here, deterministically, at request time. The values match the gateway's rule patterns
but are obviously fake; they never sit literally in a file (a scanner already replaced the
literal fakes in prompt_compression/eval/ and tests/ with placeholders).
"""

import hashlib
import json
import math
import random
import re
from pathlib import Path

# parents[3] is the gateway folder; a shallow copy (overhead.py runs from /tmp/pp in the container) falls back.
_here = Path(__file__).resolve()
GATEWAY_DIR = _here.parents[3] if len(_here.parents) > 3 else _here.parent
SUITE_DIR = GATEWAY_DIR / "tests" / "pipeline_suite"
REPORT_DIR = GATEWAY_DIR / "reports" / "pipeline-proof"
RAW_DIR = REPORT_DIR / "raw"

SEED = 42
SYSTEM_PROMPT = "You are a helpful assistant. Answer briefly, in at most 3 sentences."

_TEMPLATES = {
    "{{FAKE_OPENAI_KEY}}": lambda: "sk-" + "proj-" + "Fake0Test1Key2" * 2 + "xYz",
    "{{FAKE_GITHUB_TOKEN}}": lambda: "gh" + "p_" + "FAKEtest" * 5,
    "{{FAKE_AWS_KEY}}": lambda: "AK" + "IA" + "FAKETESTKEY00042",
    "{{FAKE_STRIPE_KEY}}": lambda: "sk_" + "live_" + "FakeTestKey" * 2,
    "{{FAKE_PASSWORD}}": lambda: "Tr0ub4dor" + "&" + "Fake3",
}


def expand(value):
    """Expand templates in strings, recursively through lists/dicts."""
    if isinstance(value, str):
        for token, make in _TEMPLATES.items():
            if token in value:
                value = value.replace(token, make())
        return value
    if isinstance(value, list):
        return [expand(v) for v in value]
    if isinstance(value, dict):
        return {k: expand(v) for k, v in value.items()}
    return value


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


_FACT_PATTERNS = [
    r"[\w.+-]+@[\w-]+\.[\w.]+",                                   # emails
    r"\b[A-Z]{2,}[-_]?\d[\w-]*\b",                                # IDs like ORD-2024-88731, CVE-2024-3094, JIRA-4521
    r"\b\d{4}-\d{2}-\d{2}(?:T[\d:+.-]+)?\b",                      # ISO dates / timestamps
    r"\b\d{1,2}:\d{2}\b",                                         # times
    r"[$€£]?\d[\d,]*(?:\.\d+)*(?:\s?(?:%|mm|mg/kg|kg|mg|ms|GB|°C|°F))?",  # numbers (incl. versions) with units
    r"\b[a-z]+_[a-z_]+\b|\b[a-z]+[A-Z]\w+\b",                     # snake_case / camelCase identifiers
    r"`[^`]+`",                                                   # inline code
]


def extract_key_facts(text: str, limit: int = 8) -> list:
    """Deterministic key facts: emails, IDs, dates, times, numbers(+units), code identifiers.

    Single digits and bare 1-2 digit numbers are skipped (too ambiguous to require verbatim)."""
    facts = []
    for pattern in _FACT_PATTERNS:
        for match in re.findall(pattern, text):
            fact = match.strip().strip(",.;:")
            if not fact or (fact.isdigit() and len(fact) < 3) or fact in facts:
                continue
            facts.append(fact)
    # Drop facts contained in a longer fact (e.g. "2024" inside "2024-01-01").
    facts = [f for f in facts if not any(f != g and f in g for g in facts)]
    return facts[:limit]


def wilson(successes: int, n: int, z: float = 1.96) -> tuple:
    """Wilson score interval for a proportion; returns (p, low, high)."""
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def percentile(values, pct):
    ordered = sorted(values)
    if not ordered:
        return float("nan")
    k = (len(ordered) - 1) * pct / 100
    lo, hi = math.floor(k), math.ceil(k)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def bootstrap_ci(values, stat, iterations: int = 2000, seed: int = SEED) -> tuple:
    """Percentile bootstrap 95% CI of `stat(values)`."""
    if not values:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    samples = sorted(stat([rng.choice(values) for _ in values]) for _ in range(iterations))
    return (samples[int(0.025 * iterations)], samples[int(0.975 * iterations) - 1])


def read_jsonl(path: Path) -> list:
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_env() -> dict:
    env = {}
    for line in (GATEWAY_DIR / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"')
    return env
