import sys, json
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
hooks()

# ---- 2a: root-cause retention vs distance from the identifier line, and vs question phrasing ----
def mklog(rc_pos, id_pos=80, n=160):
    L = [f"2026-11-17T10:{i//60:02d}:{i%60:02d}Z INFO checkout-service req=req-{i:05d} user=u-{i%37} path=/v1/cart latency_ms={80+i%50}" for i in range(n)]
    L[id_pos] = "2026-11-17T10:01:20Z ERROR checkout-service order=ord-7731 returned 503 to client"
    L[rc_pos] = "2026-11-17T10:01:19Z ERROR db-pool pool exhausted: max=20 active=20 (ROOT-CAUSE-MARKER)"
    return "\n".join(L)

res = []
for d in (1, 2, 3, 5, 10, 30, -1, -2, -5, -30):
    rc = 80 - d if d > 0 else 80 + (-d)
    log = mklog(rc)
    r = run([{"role":"user","content":"Logs:\n\n"+log+"\n\nWhy did order ord-7731 fail?"}], ce=False)
    res.append(("distance_%+d" % d, r["tok_before"], r["tok_after"], "ROOT-CAUSE-MARKER" in r["text"]))
for q in ("Why did order ord-7731 fail?", "Why did the checkout fail?", "What went wrong with the 503 errors?", "Why did req-00080 fail? (the order is ord-7731)"):
    log = mklog(77)
    r = run([{"role":"user","content":"Logs:\n\n"+log+"\n\n"+q}], ce=False)
    res.append(("question=" + q, r["tok_before"], r["tok_after"], "ROOT-CAUSE-MARKER" in r["text"]))
for row in res: print(row)

# ---- 2b: does the same log+question get a different treatment when asked as 'review/explain'? ----
for q in ("Review these logs and tell me why ord-7731 failed.", "Why did every order ord-7731 request fail?"):
    log = mklog(77)
    r = run([{"role":"user","content":"Logs:\n\n"+log+"\n\n"+q}], ce=False)
    print("INTENT", q, r["pc"].get("intent"), r["tok_before"], r["tok_after"], "ROOT-CAUSE-MARKER" in r["text"])
