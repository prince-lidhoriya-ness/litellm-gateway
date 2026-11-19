import sys, json, copy, os
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
from context_engineering.engine import ContextEngine
from context_engineering.settings import ContextSettings
import dataclasses

def out_text(i, size):
    # distinct, log-like output of ~size tokens
    lines = []
    n = 0
    j = 0
    while n < size:
        l = f"step{i:02d} line{j:03d} worker=w{(i*7+j)%13} job=j-{i*1000+j} status=ok bytes={(i+1)*(j+3)*17}"
        lines.append(l); n += tk.text_tokens(l) + 1; j += 1
    return "\n".join(lines)

def request_at(n, size):
    msgs = [{"role":"system","content":"You are an operations agent. " + "Policy text. " * 120},
            {"role":"user","content":"Investigate the failing nightly job and report root cause. Never restart production."}]
    for i in range(n):
        msgs.append({"role":"assistant","content":None,"tool_calls":[{"id":f"c{i}","type":"function","function":{"name":"read_logs","arguments":json.dumps({"file":f"log{i}"})}}]})
        msgs.append({"role":"tool","tool_call_id":f"c{i}","content":out_text(i,size)})
    return msgs

def common_prefix_frac(a, b):
    sa = json.dumps(a, sort_keys=True, ensure_ascii=False); sb = json.dumps(b, sort_keys=True, ensure_ascii=False)
    k = 0
    for x, y in zip(sa, sb):
        if x != y: break
        k += 1
    return k / max(1, len(sa))

PRICE = {"anthropic": dict(read=0.10, write=1.25), "openai": dict(read=0.50, write=1.00)}

def simulate(size, rounds=24, mode="gateway"):
    eng = ContextEngine(ContextSettings(min_tokens=0))
    prev = None; tot = {k:0.0 for k in ("tokens","cost_anthropic","cost_openai")}; reused=[]
    for n in range(1, rounds+1):
        raw = request_at(n, size)
        sent = raw if mode=="baseline" else eng.process(raw, "gpt-4o-mini", None, 512).messages
        T = tk.messages_tokens(sent)
        f = 0.0 if prev is None else common_prefix_frac(prev, sent)
        reused.append(round(f,3))
        tot["tokens"] += T
        for prov, p in PRICE.items():
            cached = T * f
            new = T - cached
            tot["cost_"+prov] += cached * p["read"] + new * p["write"]
        prev = sent
    return tot, reused

for size in (250, 600, 1500):
    b, rb = simulate(size, mode="baseline")
    g, rg = simulate(size, mode="gateway")
    print(f"--- tool output ~{size} tokens, 24 rounds")
    print(" tokens  baseline %.0f gateway %.0f  (%.1f%% fewer)" % (b["tokens"], g["tokens"], 100*(1-g["tokens"]/b["tokens"])))
    for prov in ("anthropic","openai"):
        k="cost_"+prov
        print(" cache-adjusted cost (%s-style pricing): baseline %.0f gateway %.0f  (%+.1f%%)" % (prov, b[k], g[k], 100*(g[k]/b[k]-1)))
    print(" prefix reuse by round  baseline:", rb[:12], "... gateway:", rg[:12])
    print(" rounds where gateway prefix reuse < 0.9:", sum(1 for x in rg[1:] if x < 0.9), "of", len(rg)-1)
