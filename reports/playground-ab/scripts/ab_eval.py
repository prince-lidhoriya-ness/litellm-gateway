"""A/B evaluation of the prompt-compression pipeline through the LiteLLM proxy (the endpoint the Admin UI Playground calls).

Arms (same proxy, same model, same request body except one metadata flag):
  baseline    metadata.prompt_compression=false  -> the gate skips the pipeline, the original prompt is sent
  compressed  no flag                            -> gate -> segment/classify -> router -> actions -> reassemble

Modes:
  capture     model obs-mock (capture_mock.py on :4010 echoes what the gateway forwarded): exact post-pipeline text,
              key facts kept, tiktoken counts, pipeline overhead without model noise
  llm         model obs-priced-llama (Ollama llama3.2:3b, temperature 0, seed 7): accuracy, provider tokens, latency
  throughput  concurrency sweep per arm on a fixed subset (obs-mock and/or obs-priced-llama)

    .venv-compression/Scripts/python reports/playground-ab/scripts/ab_eval.py capture --run-id A1
    .venv-compression/Scripts/python reports/playground-ab/scripts/ab_eval.py llm --run-id A1
    .venv-compression/Scripts/python reports/playground-ab/scripts/ab_eval.py throughput --run-id A1 --model obs-mock

Rows go to reports/playground-ab/raw/<mode>_<run-id>[_<suffix>].jsonl (resumable: rows already written are skipped).
The master key is read from .env and never written anywhere.
"""

import argparse
import concurrent.futures
import json
import random
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT_DIR = HERE.parent
GATEWAY_DIR = REPORT_DIR.parents[1]
RAW = REPORT_DIR / "raw"
DATA = GATEWAY_DIR / "reports" / "compression-fit" / "data"
sys.path.insert(0, str(GATEWAY_DIR / "reports" / "pipeline-proof" / "scripts"))
from run_suite import fetch_pipeline_metadata, send  # noqa: E402
from suite_lib import load_env  # noqa: E402

import tiktoken  # noqa: E402

ENC = tiktoken.get_encoding("cl100k_base")
INSTR = ("Answer the question using only the document below. "
         "Reply with only the answer value (a name, number or identifier), nothing else.")
PII_QUESTION = "What is the case reference number?"
FAMILIES = ("qa", "logs", "code", "pii")
SEED = 7


def toks(text: str) -> int:
    return len(ENC.encode(text or ""))


def load_items(families, limit=None) -> list:
    items = []
    for fam in families:
        rows = [json.loads(l) for l in open(DATA / f"{fam}.jsonl", encoding="utf-8") if l.strip()]
        for row in rows[:limit] if limit else rows:
            if fam == "pii":
                ref = next(s for s in row["key_strings"] if s.startswith("CASE-"))
                row = {**row, "question": PII_QUESTION, "answers": [ref]}
            items.append(row)
    return items


def build_prompt(item: dict, nonce: str) -> str:
    # First paragraph = instruction, last = question: the router's edge protection keeps both verbatim.
    return f"[req:{nonce}]\n{INSTR}\n\nDocument:\n{item['context']}\n\nQuestion: {item['question']}\nAnswer:"


def body(item: dict, arm: str, model: str, run_id: str, max_tokens: int) -> tuple:
    nonce = uuid.uuid4().hex[:8]  # same length in both arms; defeats Ollama's prefix cache
    prompt = build_prompt(item, nonce)
    metadata = {"ab_run": run_id, "ab_item": item["id"], "ab_arm": arm}
    if arm == "baseline":
        metadata["prompt_compression"] = False
    return prompt, {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "seed": SEED,
                    "max_tokens": max_tokens, "metadata": metadata}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def correct(item: dict, text: str) -> int:
    r = norm(text)
    return int(any(norm(a) in r for a in item["answers"]))


def done_keys(path: Path) -> set:
    if not path.exists():
        return set()
    return {(r["item"], r["arm"]) for r in map(json.loads, path.read_text(encoding="utf-8").splitlines()) if r}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def join_metadata(path: Path, since: str) -> None:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    ids = {r["call_id"] for r in rows if r.get("call_id") and "pc" not in r}
    if not ids:
        return
    meta = fetch_pipeline_metadata(ids, since)
    for r in rows:
        m = meta.get(r.get("call_id"))
        if m and "pc" not in r:
            r["pc"] = m.get("pc")
            r["spend_prompt_tokens"] = m.get("prompt_tokens")
            r["spend_completion_tokens"] = m.get("completion_tokens")
            r["spend_usd"] = m.get("spend")
            r["request_duration_ms"] = m.get("request_duration_ms")
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"joined spend-log metadata for {sum(1 for r in rows if 'pc' in r)}/{len(rows)} rows", flush=True)


def run_pairs(mode: str, run_id: str, model: str, families, limit, max_tokens: int, arms) -> Path:
    key = load_env()["LITELLM_MASTER_KEY"]
    path = RAW / f"{mode}_{run_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    done = done_keys(path)
    items = load_items(families, limit)
    # interleave families round-robin to spread drift; per-item arm order is shuffled (seeded)
    by_fam = {f: [i for i in items if i["family"] == f] for f in families}
    order = [i for group in zip(*[by_fam[f] + [None] * (max(map(len, by_fam.values())) - len(by_fam[f]))
                                  for f in families]) for i in group if i]
    rng = random.Random(SEED)
    since = now_utc()
    started = time.time()
    with open(path, "a", encoding="utf-8") as out:
        for n, item in enumerate(order, 1):
            pair = list(arms)
            rng.shuffle(pair)
            for arm in pair:
                if (item["id"], arm) in done:
                    continue
                prompt, req = body(item, arm, model, run_id, max_tokens)
                res = send(req, key, stream=False)
                row = {"run": run_id, "mode": mode, "model": model, "item": item["id"], "family": item["family"],
                       "arm": arm, "ts": now_utc(), "http_status": res["http_status"], "error": res["error"],
                       "call_id": res.get("call_id"), "latency_s": res["latency_s"], "usage": res["usage"],
                       "orig_chars": len(prompt), "orig_tokens_cl100k": toks(prompt)}
                content = res["content"] or ""
                if mode == "capture":
                    try:
                        sent = json.loads(content)["received_messages"][0]["content"]
                    except Exception:
                        sent = None
                    row.update(sent_text=sent, sent_tokens_cl100k=toks(sent) if sent else None,
                               changed=(sent is not None and sent.split("\n", 1)[1:] != prompt.split("\n", 1)[1:]),
                               key_strings_kept={k: (k in sent) if sent else None for k in item["key_strings"]},
                               answer_in_prompt=int(any(a in (sent or "") for a in item["answers"])))
                    if item["family"] == "pii":
                        row["sent_text"] = None  # PII prompts: keep only the checks, not the text
                else:
                    row.update(response=content, correct=correct(item, content), finish_reason=res["finish_reason"])
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
            if n % 10 == 0 or n == len(order):
                print(f"{mode} {run_id}: {n}/{len(order)} items, {(time.time() - started) / 60:.1f} min", flush=True)
    join_metadata(path, since)
    return path


def throughput(run_id: str, model: str, levels, per_level: int, max_tokens: int) -> None:
    key = load_env()["LITELLM_MASTER_KEY"]
    path = RAW / f"throughput_{run_id}_{model}.jsonl"
    items = load_items(("qa", "logs", "code"), None)
    rng = random.Random(SEED)
    rng.shuffle(items)
    subset = items[:per_level]
    with open(path, "a", encoding="utf-8") as out:
        for level in levels:
            for arm in ("baseline", "compressed", "compressed", "baseline")[: 2 if level > 1 else 2]:
                for _ in range(2):  # warm-up
                    send(body(subset[0], arm, model, run_id, max_tokens)[1], key, stream=False)
                t0 = time.perf_counter()
                with concurrent.futures.ThreadPoolExecutor(max_workers=level) as pool:
                    results = list(pool.map(lambda it: send(body(it, arm, model, run_id, max_tokens)[1], key,
                                                            stream=False), subset))
                wall = time.perf_counter() - t0
                lat = sorted(r["latency_s"] for r in results)
                row = {"run": run_id, "model": model, "arm": arm, "concurrency": level, "requests": len(results),
                       "ok": sum(1 for r in results if r["http_status"] == 200), "wall_s": round(wall, 3),
                       "rps": round(len(results) / wall, 4), "lat_p50": lat[len(lat) // 2],
                       "lat_p95": lat[min(len(lat) - 1, int(0.95 * len(lat)))],
                       "prompt_tokens": sum(((r["usage"] or {}).get("prompt_tokens") or 0) for r in results)}
                out.write(json.dumps(row) + "\n")
                out.flush()
                print(json.dumps(row), flush=True)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["capture", "llm", "throughput", "probe"])
    p.add_argument("--run-id", required=True)
    p.add_argument("--model")
    p.add_argument("--families", nargs="+", default=list(FAMILIES))
    p.add_argument("--limit", type=int)
    p.add_argument("--max-tokens", type=int, default=24)
    p.add_argument("--levels", nargs="+", type=int, default=[1, 4])
    p.add_argument("--per-level", type=int, default=24)
    a = p.parse_args()
    if a.mode == "probe":
        path = run_pairs("probe", a.run_id, a.model or "obs-mock", ["qa"], 1, a.max_tokens, ("compressed",))
        print(path.read_text(encoding="utf-8")[:3000])
    elif a.mode == "capture":
        run_pairs("capture", a.run_id, a.model or "obs-mock", a.families, a.limit, a.max_tokens,
                  ("baseline", "compressed"))
    elif a.mode == "llm":
        run_pairs("llm", a.run_id, a.model or "obs-priced-llama", a.families, a.limit, a.max_tokens,
                  ("baseline", "compressed"))
    else:
        throughput(a.run_id, a.model or "obs-mock", a.levels, a.per_level, a.max_tokens)


if __name__ == "__main__":
    main()
