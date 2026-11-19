import sys, json, copy, time, urllib.request
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
from exp1 import cases
hooks()

def native(msgs):
    out = []
    for m in msgs:
        m = copy.deepcopy(m)
        if m.get("tool_calls"):
            for c in m["tool_calls"]:
                a = c["function"]["arguments"]
                c["function"]["arguments"] = json.loads(a) if isinstance(a, str) else a
                c.pop("id", None); c.pop("type", None)
            m["content"] = m.get("content") or ""
        m.pop("tool_call_id", None)
        out.append(m)
    return out

def ask(msgs):
    body = {"model": "llama3.2:3b", "messages": native(msgs), "stream": False,
            "options": {"temperature": 0, "num_ctx": 16384, "num_predict": 160, "seed": 1}}
    req = urllib.request.Request("http://127.0.0.1:11434/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t = time.perf_counter()
    r = json.loads(urllib.request.urlopen(req, timeout=600).read())
    return r["message"]["content"], r.get("prompt_eval_count"), r.get("eval_count"), time.perf_counter() - t

checks = {
 "C_backend_log_identifier": lambda a: any(k in a.lower() for k in ("pool", "exhaust", "connection leak", "leaked")),
 "G_prose_doc": lambda a: "900" in a,
 "E_ticket_lookup": lambda a: "88-4471" in a,
 "H_agent_old_unref": lambda a: "17" in a,
 "I_long_chat": lambda a: "sudo" in a.lower() and "prod-eu-3" in a.lower(),
 "J_ident_in_prose": lambda a: "NIMBUS-5044" in a.replace(" ", "") or "NIMBUS - 5044" in a,
}
rows = []
for name, chk in checks.items():
    c = cases[name]
    g = run(c["msgs"])
    for label, msgs in (("baseline", c["msgs"]), ("gateway", g["data"]["messages"])):
        ans, pt, et, dt = ask(msgs)
        row = dict(case=name, cfg=label, provider_prompt_tokens=pt, out_tokens=et, secs=round(dt,1), correct=bool(chk(ans)), answer=ans[:230].replace("\n"," "))
        rows.append(row); print(json.dumps(row), flush=True)
json.dump(rows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exp6.json"),"w"), indent=1)
