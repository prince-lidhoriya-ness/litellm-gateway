"""Runs suite cases through the LiteLLM gateway and records one raw row per request.

Arms:
  pipeline  normal request: rules -> classifier -> router -> compressor -> LiteLLM -> model
  baseline  same gateway, per-request opt-out (metadata.prompt_compression=false): uncompressed
Model:
  obs-priced-llama  Ollama llama3.2:3b (temperature 0, seed 42), test prices from litellm_config.yaml
  obs-mock          capture mock (capture_mock.py): response = the exact messages/tools the gateway sent

    python reports/pipeline-proof/scripts/run_suite.py --run-id R1 --arm pipeline --model obs-priced-llama \
        --files normal edge_minimal ... [--repeat-from-case] [--stream] [--max-tokens 96]

Writes raw/run_<run-id>_<arm>_<model>.jsonl. Pipeline metadata (label, scores, source, tokens
before/after, stage timings) is joined from the Postgres spend logs by litellm_call_id.
Secrets: the master key is read from .env and never written; key-shaped test values are
expanded from templates at send time and only their hashes are stored.
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from suite_lib import RAW_DIR, SEED, SUITE_DIR, expand, load_env, read_jsonl, sha, write_jsonl  # noqa: E402

GATEWAY = "http://127.0.0.1:4000/v1/chat/completions"
TEXT_ROLES = ("user", "assistant")


def message_text(message: dict) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
    return ""


def send(body: dict, key: str, stream: bool, timeout: float = 600) -> dict:
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {**body, "stream": stream}
    if stream:
        body["stream_options"] = {"include_usage": True}
    started = time.perf_counter()
    result = {"http_status": None, "error": None, "content": None, "finish_reason": None, "usage": None,
              "ttft_s": None, "tool_calls": None}
    try:
        req = urllib.request.Request(GATEWAY, data=json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result["http_status"] = resp.status
            result["call_id"] = resp.headers.get("x-litellm-call-id")
            result["cost_header_usd"] = _float(resp.headers.get("x-litellm-response-cost"))
            if not stream:
                data = json.loads(resp.read())
                choice = data["choices"][0]
                result.update(content=choice["message"].get("content"), finish_reason=choice.get("finish_reason"),
                              usage=data.get("usage"), tool_calls=choice["message"].get("tool_calls"))
            else:
                parts, usage, finish = [], None, None
                for raw in resp:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line.startswith("data:") or line == "data: [DONE]":
                        continue
                    chunk = json.loads(line[5:])
                    usage = chunk.get("usage") or usage
                    for choice in chunk.get("choices") or []:
                        delta = choice.get("delta") or {}
                        if delta.get("content"):
                            if result["ttft_s"] is None:
                                result["ttft_s"] = round(time.perf_counter() - started, 4)
                            parts.append(delta["content"])
                        finish = choice.get("finish_reason") or finish
                result.update(content="".join(parts), usage=usage, finish_reason=finish)
    except urllib.error.HTTPError as exc:
        result["http_status"] = exc.code
        result["call_id"] = exc.headers.get("x-litellm-call-id")
        detail = exc.read()[:400].decode("utf-8", "replace")
        result["error"] = f"HTTP {exc.code}: {detail}"
    except Exception as exc:  # network / timeout
        result["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
    result["latency_s"] = round(time.perf_counter() - started, 4)
    return result


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def capture_checks(case: dict, sent_messages: list, sent_tools) -> dict:
    """Deterministic comparison of what the gateway sent vs the original request."""
    original = expand(case["messages"])
    out = {"roles_order_ok": [m.get("role") for m in sent_messages] == [m.get("role") for m in original]}
    if not out["roles_order_ok"]:
        return out
    changed, preserved_ok = [], True
    for index, (orig, sent) in enumerate(zip(original, sent_messages)):
        if orig.get("role") in ("system", "developer", "tool") or orig.get("tool_calls"):
            same = message_text(orig) == message_text(sent) and orig.get("tool_calls") == sent.get("tool_calls") \
                and orig.get("tool_call_id") == sent.get("tool_call_id")
            preserved_ok &= same
        elif message_text(orig) != message_text(sent):
            changed.append(index)
    out["preserved_roles_unchanged"] = preserved_ok
    out["tools_unchanged"] = (expand(case.get("tools")) or None) == (sent_tools or None)
    out["changed_message_indexes"] = changed
    sent_text = "\n".join(message_text(m) for m in sent_messages if m.get("role") in TEXT_ROLES)
    out["key_facts_present"] = {fact: expand(fact) in sent_text for fact in case["key_facts"]}
    out["sent_text_sha"] = sha(sent_text)
    out["original_text_sha"] = sha("\n".join(message_text(m) for m in original if m.get("role") in TEXT_ROLES))
    out["sent_text_chars"] = len(sent_text)
    # Text is stored only for categories that may be compressed; sensitive cases keep hashes only.
    if case["expected_label"] in ("non_sensitive", "less_important", "critical", "none"):
        out["sent_text"] = sent_text
    return out


def fetch_pipeline_metadata(call_ids: set, since_iso: str, wait_s: float = 150) -> dict:
    """Spend-log rows (batched writes, so poll) -> {call_id: {...}}."""
    sql = ("COPY (SELECT json_build_object('call_id', litellm_call_id, 'request_id', request_id, 'status', status, "
           "'prompt_tokens', prompt_tokens, 'completion_tokens', completion_tokens, 'spend', spend, "
           "'request_duration_ms', request_duration_ms, 'pc', metadata->'spend_logs_metadata'->'prompt_compression') "
           f"FROM \"LiteLLM_SpendLogs\" WHERE \"startTime\" >= '{since_iso}') TO STDOUT")
    deadline = time.time() + wait_s
    found = {}
    while True:
        proc = subprocess.run(["docker", "exec", "litellm-gateway-db-1", "psql", "-U", "litellm", "-d", "litellm", "-t", "-A", "-c", sql],
                              capture_output=True, text=True, encoding="utf-8")
        for line in proc.stdout.splitlines():
            if line.strip():
                row = json.loads(line.replace("\\\\", "\\"))
                found[row["call_id"] or row["request_id"]] = row
        if call_ids <= set(found) or time.time() > deadline:
            return found
        time.sleep(10)


def load_cases(files: list, ids: list | None) -> list:
    cases = []
    for name in files:
        cases += read_jsonl(SUITE_DIR / f"{name}.jsonl")
    if ids:
        cases = [c for c in cases if c["id"] in ids]
    return cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--arm", choices=["pipeline", "baseline"], required=True)
    parser.add_argument("--model", default="obs-priced-llama")
    parser.add_argument("--files", nargs="+", required=True)
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--max-tokens", type=int, default=96)
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--tag", default="")
    args = parser.parse_args()

    key = load_env()["LITELLM_MASTER_KEY"]
    cases = load_cases(args.files, args.ids)
    since = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    capture = args.model == "obs-mock"
    rows = []
    total = sum(c.get("repeat", 1) for c in cases)
    done = 0
    for case in cases:
        for repetition in range(case.get("repeat", 1)):
            metadata = {"suite_case": case["id"], "suite_arm": args.arm, "suite_run": args.run_id}
            if args.arm == "baseline":
                metadata["prompt_compression"] = False
            body = {"model": args.model, "messages": expand(case["messages"]), "temperature": 0, "seed": SEED,
                    "max_tokens": args.max_tokens, "metadata": metadata}
            if case.get("tools"):
                body["tools"] = expand(case["tools"])
            result = send(body, key, args.stream)
            row = {"run_id": args.run_id, "arm": args.arm, "model": args.model, "case_id": case["id"],
                   "category": case["category"], "edge_type": case.get("edge_type"), "expected_label": case["expected_label"],
                   "repetition": repetition, "inject": case.get("inject"), "tag": args.tag, **result}
            if capture and result.get("content"):
                try:
                    echoed = json.loads(result["content"])
                    row["capture"] = capture_checks(case, echoed["received_messages"], echoed.get("received_tools"))
                except (json.JSONDecodeError, KeyError) as exc:
                    row["capture_error"] = type(exc).__name__
                row["content"] = None  # the echo is the prompt itself; its checks are kept instead
            elif result.get("content") is not None and case["expected_label"] == "sensitive":
                row["content_sha"] = sha(result["content"])  # answers may quote PII; keep text for judging only
            rows.append(row)
            done += 1
            print(f"[{done}/{total}] {case['id']} rep={repetition} http={result['http_status']} "
                  f"{result['latency_s']:.2f}s{' ERR ' + result['error'][:80] if result['error'] else ''}", flush=True)

    meta = fetch_pipeline_metadata({r["call_id"] for r in rows if r.get("call_id")}, since)
    for row in rows:
        m = meta.get(row.get("call_id")) or {}
        row["spend_log"] = {k: m.get(k) for k in ("status", "prompt_tokens", "completion_tokens", "spend", "request_duration_ms")} if m else None
        row["pipeline"] = m.get("pc")
    suffix = f"_{args.tag}" if args.tag else ""
    out = RAW_DIR / f"run_{args.run_id}_{args.arm}_{args.model}{suffix}.jsonl"
    write_jsonl(out, rows)
    print(f"wrote {out} ({len(rows)} rows, {sum(1 for r in rows if r['pipeline'])} with pipeline metadata)")


if __name__ == "__main__":
    main()
