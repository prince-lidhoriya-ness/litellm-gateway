import json, sys, random
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *

random.seed(7)
SENT = [
    "The team reviewed the rollout plan and agreed that the migration should happen in stages across the regions.",
    "Customers have reported intermittent slowness when the dashboard loads large result sets during peak hours.",
    "An earlier incident showed that retry storms can amplify load when the downstream service starts to degrade.",
    "Several engineers pointed out that the documentation for the internal tooling is outdated and often misleading.",
    "The vendor confirmed that the fix will ship in the next maintenance window, although no exact date was given.",
    "It was noted that the staging environment differs from production in how it handles connection pooling.",
    "Finance asked for a breakdown of the monthly spend so that the budget review can be completed on time.",
    "Support leadership wants a clearer escalation path when a ticket remains unresolved for more than two days.",
]


def prose(n_sent, seed):
    r = random.Random(seed)
    return " ".join(r.choice(SENT) for _ in range(n_sent))


def para_list(n, seed0=0, k=5):
    return "\n\n".join(prose(k, seed0 + i) for i in range(n))


cases = {}

# A short prompt
cases["A_short"] = dict(domain="any", msgs=[{"role": "user", "content": "Explain what a mutex is in two sentences."}], needles=[])

# B frontend: code-heavy
code = '''import React, { useEffect, useMemo, useState } from "react";
import { fetchCart, applyCoupon } from "../api/cartClient";

export function CartSummary({ userId, currency = "EUR" }) {
  const [cart, setCart] = useState(null);
  const [coupon, setCoupon] = useState("");
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchCart(userId).then((c) => { if (!cancelled) setCart(c); }).catch(setError);
    return () => { cancelled = true; };
  }, [userId, cart]);   // BUG: cart in deps re-triggers fetch

  const total = useMemo(() => cart?.items.reduce((s, i) => s + i.qty * i.unitPrice, 0) ?? 0, [cart]);

  async function onApply() {
    try {
      const updated = await applyCoupon(userId, coupon);
      setCart(updated);
    } catch (e) { setError(e); }
  }
  return (<div className="cart"><h2>Cart ({cart?.items.length ?? 0})</h2>
    <p>Total: {total.toFixed(2)} {currency}</p>
    <input value={coupon} onChange={(e) => setCoupon(e.target.value)} />
    <button onClick={onApply}>Apply</button>{error && <p role="alert">{String(error)}</p>}</div>);
}
''' * 2
cases["B_frontend_code"] = dict(domain="frontend", msgs=[
    {"role": "system", "content": "You are a senior frontend engineer."},
    {"role": "user", "content": "Here is my component. It keeps refetching the cart in a loop in the network tab.\n\n```jsx\n" + code + "\n```\n\nWhy does this happen and how do I fix it?"}],
    needles=["[userId, cart]", "fetchCart(userId)"])

# C backend: log with root cause line far from the identifier
logs = []
for i in range(160):
    logs.append(f"2026-11-17T10:{i//60:02d}:{i%60:02d}Z INFO checkout-service req=req-{i:05d} user=u-{i%37} path=/v1/cart latency_ms={80+i%50}")
logs[70] = "2026-11-17T10:01:10Z INFO checkout-service req=req-07731 order=ord-7731 path=/v1/checkout started"
logs[71] = "2026-11-17T10:01:11Z INFO checkout-service req=req-07732 user=u-12 path=/v1/cart latency_ms=91"
logs[72] = "2026-11-17T10:01:11Z INFO checkout-service req=req-07733 user=u-13 path=/v1/cart latency_ms=95"
logs[73] = "2026-11-17T10:01:12Z ERROR db-pool pool exhausted: max=20 active=20 waiting=41 (leaked connections in InventoryRepo.reserve)"
logs[74] = "2026-11-17T10:01:12Z INFO checkout-service req=req-07734 user=u-14 path=/v1/cart latency_ms=99"
logs[75] = "2026-11-17T10:01:13Z INFO checkout-service req=req-07735 user=u-15 path=/v1/cart latency_ms=97"
logs[90] = "2026-11-17T10:01:30Z WARN checkout-service order=ord-7731 payment authorization timed out after 30000ms"
logs[91] = "2026-11-17T10:01:31Z ERROR checkout-service order=ord-7731 returned 503 to client"
cases["C_backend_log_identifier"] = dict(domain="backend", msgs=[
    {"role": "user", "content": "Service logs from the checkout-service:\n\n" + "\n".join(logs) + "\n\nWhy did order ord-7731 fail?"}],
    needles=["pool exhausted", "max=20 active=20", "leaked connections", "InventoryRepo.reserve", "timed out after 30000ms"])

# D devops CI log, no identifier in question
ci = []
for i in range(220):
    ci.append(f"[{i:03d}] step=build-{i%12} cache=hit duration={i%9}.{i%7}s status=ok")
ci[140] = "[140] step=deploy-canary status=FAILED: kubectl rollout status timed out; pod web-7f9c still CrashLoopBackOff (OOMKilled, limit 256Mi)"
cases["D_devops_ci_noid"] = dict(domain="devops", msgs=[
    {"role": "user", "content": "CI pipeline output:\n\n" + "\n".join(ci) + "\n\nWhich step failed and why?"}],
    needles=["OOMKilled", "limit 256Mi", "CrashLoopBackOff"])

# E/F ticket thread
thread = []
for i in range(10):
    body = prose(6, 100 + i)
    if i == 3:
        body += " The customer wrote: my order number is 88-4471-XQ and the refund of 129.90 USD must reach card ending 4242 before 2026-12-01."
    thread.append(f"From: agent{i%3}@example.com\nTo: customer@example.org\nSubject: Re: Ticket TCK-20931\n\n{body}")
thread_text = "\n\n".join(thread)
cases["E_ticket_lookup"] = dict(domain="ticket", msgs=[
    {"role": "user", "content": "Here is the ticket history:\n\n" + thread_text + "\n\nWhat order number did the customer give?"}],
    needles=["88-4471-XQ", "129.90 USD", "ending 4242", "2026-12-01"])
cases["F_ticket_summarize"] = dict(domain="ticket", msgs=[
    {"role": "user", "content": "Here is the ticket history:\n\n" + thread_text + "\n\nSummarize the whole thread and propose a resolution."}],
    needles=["88-4471-XQ", "129.90 USD", "ending 4242", "2026-12-01"])

# G long prose doc + paraphrase-type question
doc = para_list(12, 300, 6)
doc_marked = doc.replace("\n\n", "\n\n", 1)
paras = doc.split("\n\n")
paras[6] += " The decisive configuration value is IDLE_TIMEOUT_SECONDS=1800 and it must never be lowered below 900."
cases["G_prose_doc"] = dict(domain="any", msgs=[
    {"role": "user", "content": "Read this design memo:\n\n" + "\n\n".join(paras) + "\n\nWhat is the minimum allowed idle timeout?"}],
    needles=["IDLE_TIMEOUT_SECONDS=1800", "900"])

# J identifiers inside long prose (assistant history)
ident_par = (prose(4, 900) + " The tracking code for the incident is NIMBUS-5044 and it was opened against RFC-9110 section 5.2 on port 8443 "
             "running version 3.11.4 of the proxy. " + prose(4, 901))
cases["J_ident_in_prose"] = dict(domain="ticket", msgs=[
    {"role": "user", "content": "Please remember the incident details below.\n\n" + ident_par + "\n\n" + prose(5, 902)},
    {"role": "assistant", "content": ident_par + "\n\n" + prose(6, 903)},
    {"role": "user", "content": "What was the tracking code and which port was in use?"}],
    needles=["NIMBUS-5044", "RFC-9110", "section 5.2", "8443", "3.11.4"])

# H agent debug loop with old unreferenced detail, and ref'd detail
def tool_round(i, name, args, out, reply):
    cid = f"call_{i}"
    return [{"role": "assistant", "content": None, "tool_calls": [{"id": cid, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]},
            {"role": "tool", "tool_call_id": cid, "content": out},
            {"role": "assistant", "content": reply}]

def conf_dump():
    lines = [f"setting_{i:03d} = value_{i * 7 % 101}" for i in range(220)]
    lines[140] = "db.pool.max_size = 17   # raised from 10 after the March incident"
    return "\n".join(lines)

def grep_out(tag):
    return "\n".join(f"src/{tag}/mod_{i}.py:{10 + i}: logger.info('processed batch %s', batch_id)" for i in range(60))

msgs = [{"role": "system", "content": "You are a debugging agent. Never edit files under /etc."},
        {"role": "user", "content": "Find why the nightly import job hangs. Do not restart production services."}]
msgs += tool_round(0, "read_file", {"path": "config/app.conf"}, conf_dump(), "I read the config; nothing obviously wrong yet.")
for i in range(1, 8):
    msgs += tool_round(i, "grep", {"pattern": "batch", "dir": f"src/{i}"}, grep_out(i), f"Searched src/{i}; the logging looks normal.")
msgs += [{"role": "user", "content": "Earlier you read the config. What was db.pool.max_size set to, and was there a comment?"}]
cases["H_agent_old_unref"] = dict(domain="backend-debug", msgs=msgs, needles=["db.pool.max_size = 17", "raised from 10"])

# I long chat with early constraint
chat = [{"role": "system", "content": "You are an infrastructure assistant."},
        {"role": "user", "content": "We run on EKS. Constraint: you must never suggest using sudo or disabling TLS verification. Also the cluster name is prod-eu-3."}]
chat.append({"role": "assistant", "content": prose(14, 400)})
for t in range(1, 7):
    chat.append({"role": "user", "content": f"Question {t}: " + prose(2, 500 + t)})
    chat.append({"role": "assistant", "content": prose(16, 600 + t)})
chat.append({"role": "user", "content": "Remind me, what constraints did I give at the start and what is the cluster name?"})
cases["I_long_chat"] = dict(domain="devops", msgs=chat, needles=["never suggest using sudo", "disabling TLS verification", "prod-eu-3"])

def rep(name, c, **kw):
    r = run(c["msgs"], **kw)
    keep = survive(r["text"], c["needles"])
    pc = r["pc"]
    return {
        "case": name, "domain": c["domain"], "tok_before": r["tok_before"], "tok_after": r["tok_after"],
        "saved_pct": round(100 * (1 - r["tok_after"] / r["tok_before"]), 1),
        "ce_status": r["ce"].get("status") or r["ce"].get("reason"), "ce_saved": r["ce"].get("saved_by_technique"),
        "pc_status": pc.get("status") or pc.get("reason"), "pc_intent": pc.get("intent"),
        "pc_actions": [m.get("action") for m in pc.get("messages", [])] if pc else None,
        "ce_ms": round(r["ce_ms"]), "pc_ms": round(r["pc_ms"]),
        "needles_kept": sum(keep.values()), "needles_total": len(keep),
        "lost": [k for k, v in keep.items() if not v],
        "omission_marker_present": any(w in r["text"].lower() for w in ("omitted", "dropped", "removed", "masked by gateway", "[...")),
    }

if __name__ == "__main__":
    hooks()
    out = []
    for name, c in cases.items():
        out.append(rep(name, c))
        print(json.dumps(out[-1]), flush=True)
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exp1.json"), "w"), indent=1)
