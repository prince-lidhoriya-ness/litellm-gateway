import sys, json, asyncio, time, collections, statistics
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
from exp1 import prose, para_list
hooks()

def req(seed):
    body = "\n\n".join(prose(6, seed*100 + i) for i in range(8))
    return [{"role":"user","content":f"Memo {seed}:\n\n{body}\n\nWhat did the vendor confirm?"}]

async def burst(n, base):
    t0 = time.perf_counter()
    async def one(i):
        s = time.perf_counter()
        r = await arun(req(base+i), ce=False)
        return r, time.perf_counter() - s
    out = await asyncio.gather(*[one(i) for i in range(n)])
    wall = time.perf_counter() - t0
    st = collections.Counter()
    saved = 0; before = 0; lat = []
    for r, dt in out:
        pc = r["pc"]; lat.append(dt)
        label = pc.get("status") + (":" + pc["reason"] if pc.get("reason") else "") + (":stopped=" + str(pc["compress_stopped"]) if pc.get("compress_stopped") else "") + (":" + pc.get("error","") if pc.get("status")=="error" else "")
        st[label] += 1
        before += r["tok_before"]; saved += r["tok_before"] - r["tok_after"]
    lat.sort()
    return dict(n=n, wall_s=round(wall,1), statuses=dict(st), saved_pct=round(100*saved/before,1),
                p50_s=round(statistics.median(lat),1), max_s=round(lat[-1],1))

base = 1000
for n in (1, 4, 8, 16, 32):
    print(json.dumps(asyncio.run(burst(n, base))), flush=True)
    base += 1000
