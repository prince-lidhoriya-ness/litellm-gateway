"""Builds evals/cases/litellm-gateway.yaml: Gate 4 HTTP cases for the prompt-compression gateway, taken from the
benchmark dataset (reports/compression-fit/data) and the B2 capture run (reports/playground-ab/raw/capture_B2.jsonl).

The `obs-mock` model is a capture mock: it answers with the exact messages the gateway forwarded, so a case can check
what reached the model. For each benchmark item used here, B2 tells which document text the pipeline dropped:
  compressed arm  -> the answer and the question are still in the forwarded prompt, a dropped passage/log line is not
  baseline arm    -> (metadata.prompt_compression=false) the same dropped text is still there, prompt untouched
Only ASCII snippets without quotes or backslashes are used, because the mock returns the prompt JSON-encoded.

    .venv-compression/Scripts/python evals/build_cases.py
"""

import json
import re
import sys
from pathlib import Path

import yaml

GATEWAY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GATEWAY / "reports" / "playground-ab" / "scripts"))
from ab_eval import build_prompt, load_items  # noqa: E402

CAPTURE = GATEWAY / "reports" / "playground-ab" / "raw" / "capture_B2.jsonl"
OUT = GATEWAY / "evals" / "cases" / "litellm-gateway.yaml"
NONCE = "evalcase"
AUTH = {"Authorization": "Bearer {{env:LITELLM_MASTER_KEY}}"}
SAFE = re.compile(r"^[A-Za-z0-9 ,.:;$%=_/+()@-]+$")
# One item per (family, role); chosen from B2 rows where the pipeline acted as designed.
PICK = {"qa": ["qa-000", "qa-001", "qa-010"], "logs": ["logs-000", "logs-005"], "code": ["code-000", "code-004"],
        "pii": ["pii-000", "pii-001"]}


def snippet(text: str, n: int = 48):
    """A JSON-safe snippet of `text`: the longest leading run of safe characters, cut at a word boundary."""
    for line in text.splitlines():
        line = line.strip()
        s = ""
        for ch in line:
            if not SAFE.match(ch):
                break
            s += ch
        s = s[:n].rsplit(" ", 1)[0] if len(s) > n else s
        if len(s) >= 20:
            return s.strip()
    return None


def esc(s: str) -> str:
    return re.escape(s)


def chat(prompt: str, model: str = "obs-mock", opt_out: bool = False, extra=None) -> dict:
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 24}
    if opt_out:
        body["metadata"] = {"prompt_compression": False}
    if extra:
        body.update(extra)
    return {"method": "POST", "path": "/v1/chat/completions", "headers": dict(AUTH), "body": body}


def main() -> None:
    capture = {}
    for line in CAPTURE.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["arm"] == "compressed":
            capture[row["item"]] = row
    items = {i["id"]: i for i in load_items(("qa", "logs", "code", "pii"))}
    content = "choices.0.message.content"
    cases = [
        {"id": "liveness", "name": "Gateway process is up", "critical": True,
         "request": {"method": "GET", "path": "/health/liveliness"}, "expect": {"status": 200}},
        {"id": "readiness", "name": "Gateway is ready (DB and cache connected)", "critical": True,
         "request": {"method": "GET", "path": "/health/readiness"}, "expect": {"status": 200}},
        {"id": "auth-required", "name": "Chat without an API key is rejected", "critical": True,
         "request": {"method": "POST", "path": "/v1/chat/completions",
                     "body": {"model": "obs-mock", "messages": [{"role": "user", "content": "hi"}]}},
         "expect": {"status": 401}},
        {"id": "models", "name": "Model list includes the eval models",
         "request": {"method": "GET", "path": "/v1/models", "headers": dict(AUTH)},
         "expect": {"status": 200, "body_contains": "obs-mock"}},
        {"id": "unknown-model", "name": "Unknown model is a client error, not a 500",
         "request": chat("hello there", model="no-such-model"), "expect": {"status": [400, 404]}},
        {"id": "short-prompt-untouched", "name": "Prompt under PROMPT_COMPRESSION_MIN_TOKENS is forwarded unchanged",
         "critical": True, "request": chat("What is the capital of Portugal? Answer in one word."),
         "expect": {"status": 200, "json": {content: {"contains": "What is the capital of Portugal? Answer in one word."}}}},
    ]

    for fam, ids in PICK.items():
        for iid in ids:
            item, cap = items[iid], capture[iid]
            prompt = build_prompt(item, NONCE)
            answer = item["answers"][0]
            q = snippet(item["question"]) or snippet(INSTR_FALLBACK)
            sent = cap["sent_text"] or prompt  # B2 stores no copy when the prompt went out unchanged
            dropped = None
            for unit in re.split(r"\n\n|\n", item["context"]):
                # JSON records have quotes everywhere: identify a dropped record by its id instead (ORD-4349).
                s = snippet(unit) or next(iter(re.findall(r"\b[A-Z]{2,}-\d{3,}\b", unit)), None)
                if s and s not in sent and answer not in unit:
                    dropped = s
                    break
            kept = snippet(item["context"])
            if fam in ("qa", "logs"):
                assert dropped, f"{iid}: B2 dropped nothing JSON-safe"
                cases.append({
                    "id": f"{iid}-compressed", "critical": True,
                    "name": f"{fam}: answer and question reach the model, unneeded text is dropped",
                    "request": chat(prompt),
                    "expect": {"status": 200, "body_contains": answer, "json": {content: {
                        "regex": f"^(?=[\\s\\S]*{esc(q)})(?![\\s\\S]*{esc(dropped)})"}}},
                })
                cases.append({
                    "id": f"{iid}-opt-out", "critical": True,
                    "name": f"{fam}: metadata.prompt_compression=false forwards the prompt unchanged",
                    "request": chat(prompt, opt_out=True),
                    "expect": {"status": 200, "body_contains": answer, "json": {content: {"contains": dropped}}},
                })
            else:
                # code is kept verbatim by the exact-text guard, pii by the sensitivity check: nothing may be dropped.
                lines = [s for s in dict.fromkeys(snippet(l) for l in re.split(r"\n|(?<=[.!?])\s+", item["context"])) if s]
                spread = [lines[round(i * (len(lines) - 1) / 3)] for i in range(4)] if len(lines) >= 4 else lines
                checks = list(dict.fromkeys(spread + [q]))
                cases.append({
                    "id": f"{iid}-verbatim", "critical": True,
                    "name": f"{fam}: {'code' if fam == 'code' else 'sensitive record'} is forwarded verbatim",
                    "request": chat(prompt),
                    "expect": {"status": 200, "body_contains": answer, "json": {content: {
                        "regex": "^" + "".join(f"(?=[\\s\\S]*{esc(s)})" for s in checks)}}},
                })

    # A sensitive passage inside an otherwise compressible document: selection may drop other passages, never this one.
    base = items["qa-000"]
    health = ("The patient was diagnosed with type 2 diabetes in March and is taking metformin 500 mg twice a day, "
              "according to the clinic notes shared by her physician.")
    paras = base["context"].split("\n\n")
    paras.insert(len(paras) // 2, health)
    doc = {**base, "context": "\n\n".join(paras)}
    cases.append({
        "id": "sensitive-passage-kept", "critical": True,
        "name": "A health passage inside a long document is never dropped or compressed",
        "request": chat(build_prompt(doc, NONCE)),
        "expect": {"status": 200, "json": {content: {"contains": health}}},
    })
    cases.append({
        "id": "system-and-history-kept", "name": "System prompt and earlier turns survive compression of the last turn",
        "request": {"method": "POST", "path": "/v1/chat/completions", "headers": dict(AUTH), "body": {
            "model": "obs-mock", "temperature": 0, "max_tokens": 24, "messages": [
                {"role": "system", "content": "You are a careful assistant for Dorvance analysts."},
                {"role": "user", "content": "Hi, I have a question about a report."},
                {"role": "assistant", "content": "Sure, paste the report and your question."},
                {"role": "user", "content": build_prompt(base, NONCE)}]}},
        "expect": {"status": 200, "body_contains": base["answers"][0], "json": {content: {"regex": (
            "^(?=[\\s\\S]*You are a careful assistant for Dorvance analysts.)"
            "(?=[\\s\\S]*Sure, paste the report and your question.)")}}},
    })
    real = items["qa-000"]
    cases.append({
        "id": "real-model-answer", "critical": True, "timeout": 180,
        "name": "Real model (llama3.2:3b) answers correctly from the compressed prompt",
        "request": chat(build_prompt(real, NONCE), model="obs-priced-llama"),
        "expect": {"status": 200, "json": {content: {"contains": real["answers"][0]}}},
    })

    header = ("# Generated by evals/build_cases.py from reports/compression-fit/data and reports/playground-ab/raw/"
              "capture_B2.jsonl.\n# Do not edit by hand: change the builder and rerun it.\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(header + yaml.safe_dump({"service": "litellm-gateway", "cases": cases}, sort_keys=False,
                                           allow_unicode=False, width=140), encoding="utf-8")
    print(f"wrote {OUT.relative_to(GATEWAY)}: {len(cases)} cases")


INSTR_FALLBACK = "Answer the question using only the document below."

if __name__ == "__main__":
    main()
