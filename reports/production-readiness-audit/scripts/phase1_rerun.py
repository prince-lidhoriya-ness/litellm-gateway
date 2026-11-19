"""Phase 1 exit check: rerun the audit's experiments on the remediated code (STRATEGY.md, Phase 1.7 and exit criterion).

Same harness as the audit (h.py: the real context-engineering and compression hooks, the real models, offline, pinned),
same workloads (exp1 cases, exp2, exp7, exp8). The settings are the code defaults the branch ships (enforce mode,
routes narrative+logfold, mask trigger pressure), plus a second pass with the opt-in selection routes switched on.
With --ollama the audit's exp6 is repeated: each case is answered by the local llama3.2:3b, once from the original
messages and once from what the gateway sends, and checked with the audit's own string checks.

Results go to reports/production-readiness-audit/phase1/ and never overwrite the audit's own exp*.json files.

    python reports/production-readiness-audit/scripts/phase1_rerun.py            # token and retention checks
    python reports/production-readiness-audit/scripts/phase1_rerun.py --ollama   # plus answers on llama3.2:3b
"""
import argparse
import copy
import dataclasses
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h  # noqa: E402
from exp1 import cases, rep  # noqa: E402

from prompt_compression.settings import PipelineSettings  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "phase1")
SUBJ = ["billing", "login", "search", "export", "mobile app", "onboarding", "alerts", "reports", "permissions",
        "audit log"]


def exp2_log(rc_pos, id_pos=80, n=160):
    lines = [f"2026-11-17T10:{i // 60:02d}:{i % 60:02d}Z INFO checkout-service req=req-{i:05d} user=u-{i % 37} "
             f"path=/v1/cart latency_ms={80 + i % 50}" for i in range(n)]
    lines[id_pos] = "2026-11-17T10:01:20Z ERROR checkout-service order=ord-7731 returned 503 to client"
    lines[rc_pos] = "2026-11-17T10:01:19Z ERROR db-pool pool exhausted: max=20 active=20 (ROOT-CAUSE-MARKER)"
    return "\n".join(lines)


def exp2():
    rows = []
    for d in (1, 2, 3, 5, 10, 30, -1, -2, -5, -30):
        r = h.run([{"role": "user", "content": "Logs:\n\n" + exp2_log(80 - d) + "\n\nWhy did order ord-7731 fail?"}],
                  ce=False)
        rows.append({"probe": f"distance_{d:+d}", "tok_before": r["tok_before"], "tok_after": r["tok_after"],
                     "root_cause_kept": "ROOT-CAUSE-MARKER" in r["text"], "intent": r["pc"].get("intent")})
    for q in ("Why did order ord-7731 fail?", "Why did the checkout fail?", "What went wrong with the 503 errors?",
              "Why did req-00080 fail? (the order is ord-7731)", "Review these logs and tell me why ord-7731 failed.",
              "What is the status of order ord-7731?"):
        r = h.run([{"role": "user", "content": "Logs:\n\n" + exp2_log(77) + "\n\n" + q}], ce=False)
        rows.append({"probe": "question=" + q, "tok_before": r["tok_before"], "tok_after": r["tok_after"],
                     "root_cause_kept": "ROOT-CAUSE-MARKER" in r["text"], "intent": r["pc"].get("intent")})
    return rows


def notes(repeat):
    paras = []
    for i, s in enumerate(SUBJ):
        paras.append(f"Section {i + 1} ({s}). The {s} module has an owner named team-{s.replace(' ', '-')}. "
                     f"Action item {i + 1}: the owner must deliver the {s} fix by 2026-12-{10 + i:02d}. "
                     + (f"Background: the {s} work was delayed because of dependency churn, staffing gaps and unclear "
                        f"requirements in the previous quarter, and the steering group asked for weekly updates until "
                        f"the milestone is reached. ") * repeat)
    return "\n\n".join(paras)


def exp7_exp8():
    rows = []
    dates = [f"2026-12-{10 + i:02d}" for i in range(10)]
    owners = ["team-" + s.replace(" ", "-") for s in SUBJ]
    probes = [("exp7", 2, q) for q in ("Extract the action items and their owners.", "What are the deadlines?",
                                        "List the owners and dates for billing, login and search.",
                                        "Extract all action items and owners.")]
    probes.append(("exp8", 1, "What are the deadlines?"))
    for name, repeat, q in probes:
        r = h.run([{"role": "user", "content": "Meeting notes:\n\n" + notes(repeat) + "\n\n" + q}], ce=False)
        rows.append({"probe": f"{name}: {q}", "intent": r["pc"].get("intent"), "tok_before": r["tok_before"],
                     "tok_after": r["tok_after"], "dates_exact": sum(d in r["text"] for d in dates),
                     "owners_exact": sum(o in r["text"] for o in owners),
                     "actions": [m.get("action") for m in r["pc"].get("messages", [])]})
    return rows


def case_rows():
    out = []
    for name, case in cases.items():
        row = rep(name, case)
        r = h.run(case["msgs"])
        row["markers"] = r["text"].count("[gateway: ")
        row["fidelity"] = r["pc"].get("fidelity")
        out.append(row)
    return out


# ---- exp6: answers from the local 3B model ------------------------------------------------------------------------

CHECKS = {
    "C_backend_log_identifier": lambda a: any(k in a.lower() for k in ("pool", "exhaust", "connection leak", "leaked")),
    "G_prose_doc": lambda a: "900" in a,
    "E_ticket_lookup": lambda a: "88-4471" in a,
    "H_agent_old_unref": lambda a: "17" in a,
    "I_long_chat": lambda a: "sudo" in a.lower() and "prod-eu-3" in a.lower(),
    "J_ident_in_prose": lambda a: "NIMBUS-5044" in a,
}


def native(msgs):
    out = []
    for m in msgs:
        m = copy.deepcopy(m)
        if m.get("tool_calls"):
            for c in m["tool_calls"]:
                a = c["function"]["arguments"]
                c["function"]["arguments"] = json.loads(a) if isinstance(a, str) else a
                c.pop("id", None)
                c.pop("type", None)
            m["content"] = m.get("content") or ""
        m.pop("tool_call_id", None)
        out.append(m)
    return out


def ask(msgs, num_predict=160):
    body = {"model": "llama3.2:3b", "messages": native(msgs), "stream": False,
            "options": {"temperature": 0, "num_ctx": 16384, "num_predict": num_predict, "seed": 1}}
    req = urllib.request.Request("http://127.0.0.1:11434/api/chat", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    started = time.perf_counter()
    r = json.loads(urllib.request.urlopen(req, timeout=900).read())
    return r["message"]["content"], r.get("prompt_eval_count"), time.perf_counter() - started


OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"     # litellm_config.yaml, judge-nemotron


def _openrouter_key() -> str:
    """OPENROUTER_API_KEY from the environment or the repository's .env (never printed)."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    path = os.path.join(h.ROOT, ".env")
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            name, _, value = line.strip().partition("=")
            if name == "OPENROUTER_API_KEY" and value:
                return value.strip().strip("\"'")
    raise SystemExit("OPENROUTER_API_KEY is not set")


def ask_openrouter(msgs, max_tokens=1024):
    """The same messages in OpenAI format (tool calls and results included) to the production-tier model."""
    body = {"model": OPENROUTER_MODEL, "messages": msgs, "temperature": 0, "max_tokens": max_tokens}
    for attempt in range(6):
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", json.dumps(body).encode(),
                                     {"Content-Type": "application/json",
                                      "Authorization": f"Bearer {_openrouter_key()}"})
        started = time.perf_counter()
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=600).read())
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 502, 503) and attempt < 5:
                time.sleep(20 * (attempt + 1))
                continue
            raise
        if "choices" not in r:
            raise RuntimeError(f"OpenRouter returned no choices: {str(r)[:200]}")
        content = r["choices"][0]["message"].get("content") or ""
        return content, (r.get("usage") or {}).get("prompt_tokens"), time.perf_counter() - started
    raise RuntimeError("OpenRouter kept rate-limiting")


def exp6_openrouter(names):
    rows = []
    for name in names:
        case, check = cases[name], CHECKS[name]
        g = h.run(case["msgs"])
        status = g["pc"].get("status") or g["pc"].get("reason")
        for label, msgs in (("baseline", case["msgs"]), ("gateway", g["data"]["messages"])):
            answer, prompt_tokens, seconds = ask_openrouter(msgs)
            rows.append({"case": name, "cfg": label, "model": OPENROUTER_MODEL, "provider_prompt_tokens": prompt_tokens,
                         "pc_status": status if label == "gateway" else None, "correct": bool(check(answer)),
                         "secs": round(seconds, 1), "answer": answer[:600].replace("\n", " ")})
            print(json.dumps(rows[-1]), flush=True)
    return rows


def exp6(names=None, num_predict=160):
    """The gateway's output is computed while nothing else uses the CPU, and its hook status is recorded: under CPU
    contention the compression hook can time out and fail open (audit H5), which sends the original."""
    rows = []
    for name, check in CHECKS.items():
        if names and name not in names:
            continue
        case = cases[name]
        g = h.run(case["msgs"])
        status = g["pc"].get("status") or g["pc"].get("reason")
        for label, msgs in (("baseline", case["msgs"]), ("gateway", g["data"]["messages"])):
            answer, prompt_tokens, seconds = ask(msgs, num_predict)
            rows.append({"case": name, "cfg": label, "provider_prompt_tokens": prompt_tokens,
                         "pc_status": status if label == "gateway" else None, "num_predict": num_predict,
                         "correct": bool(check(answer)), "secs": round(seconds, 1),
                         "answer": answer[:400].replace("\n", " ")})
            print(json.dumps(rows[-1]), flush=True)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ollama", action="store_true")
    parser.add_argument("--exp6-only", nargs="*", help="only answer these exp6 cases (no token runs)")
    parser.add_argument("--num-predict", type=int, default=160, help="answer length in tokens (the audit used 160)")
    parser.add_argument("--openrouter", nargs="+", help="answer these exp6 cases on the OpenRouter judge model")
    parser.add_argument("--out", default="rerun.json")
    args = parser.parse_args()
    os.makedirs(OUT, exist_ok=True)
    h.hooks()
    if args.openrouter:
        rows = exp6_openrouter(args.openrouter)
        with open(os.path.join(OUT, args.out), "w", encoding="utf-8") as handle:
            json.dump(rows, handle, indent=1)
        return
    if args.exp6_only is not None:
        rows = exp6(set(args.exp6_only) or None, args.num_predict)
        with open(os.path.join(OUT, args.out), "w", encoding="utf-8") as handle:
            json.dump(rows, handle, indent=1)
        return
    result = {"settings": "code defaults (enforce, routes narrative+logfold, mask trigger pressure)",
              "cases": case_rows(), "exp2": exp2(), "exp7_exp8": exp7_exp8()}
    # Second pass: the opt-in selection routes on (what a team gets if it enables them).
    h.hooks(pc_settings=dataclasses.replace(PipelineSettings.from_env(),
                                            routes=frozenset({"narrative", "logfold", "passages", "records"})))
    result["selection_on"] = {"cases": case_rows(), "exp2": exp2(), "exp7_exp8": exp7_exp8()}
    h.hooks(pc_settings=PipelineSettings.from_env())
    if args.ollama:
        result["exp6"] = exp6()
    with open(os.path.join(OUT, args.out), "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=1)
    print(json.dumps({k: v for k, v in result.items() if k != "exp6"}, indent=1))


if __name__ == "__main__":
    main()
