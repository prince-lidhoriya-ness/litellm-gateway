import sys, json, asyncio, time, re, copy
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
from exp1 import cases, prose
from fastapi import HTTPException
from context_engineering.engine import ContextEngine
from context_engineering.settings import ContextSettings
from context_engineering.store import RedisStore
from context_engineering.callback import ContextEngineeringCallback
from prompt_compression.pipeline import PromptPipeline
hooks()

print("== 5a recovery by ref")
base = cases["H_agent_old_unref"]["msgs"]
r1 = run(base, ce=True, pc=False)
stub = next(tk.message_text(m) for m in r1["data"]["messages"] if m["role"]=="tool" and "masked by gateway" in tk.message_text(m))
ref = re.search(r"obs_[0-9a-f]{12}", stub).group(0)
print(" step1 tokens", r1["tok_before"], "->", r1["tok_after"], "| answer-bearing line present:", "db.pool.max_size = 17" in r1["text"])
# user mentions the ref (the documented recovery)
base2 = copy.deepcopy(base); base2[-1]["content"] += f" (use {ref})"
r2 = run(base2, ce=True, pc=False)
print(" step2 (user mentions ref) tokens", r2["tok_before"], "->", r2["tok_after"], "| present:", "db.pool.max_size = 17" in r2["text"], "| restored:", r2["ce"].get("restored"))
# model-side recovery: assistant message mentions the ref, then asks a different question; the model must itself have emitted the ref
base3 = copy.deepcopy(base)[:-1] + [{"role":"assistant","content":f"I need the original output {ref} to answer."},{"role":"user","content":"ok go ahead"}]
r3 = run(base3, ce=True, pc=False)
print(" step3 (assistant mentions ref) present:", "db.pool.max_size = 17" in r3["text"])
# different worker (fresh engine = empty MemoryStore): does ref restore still work?
eng2 = ContextEngine(ContextSettings(min_tokens=0))
res = eng2.process(base2, "gpt-4o-mini", None, 512)
print(" other worker, user mentions ref: present:", "db.pool.max_size = 17" in flat(res.messages), "| store has ref:", eng2.store.get(ref) is not None)
res = ContextEngine(ContextSettings(min_tokens=0)).process(base, "gpt-4o-mini", None, 512)

print("== 5b masking without budget pressure")
ce = r1["ce"]
print(" pressure:", ce.get("pressure"), "utilization:", ce.get("utilization_before"), "window:", ce.get("window"), "masked:", len(ce.get("masked") or []))

print("== 5c unknown-alias window (DB-managed model names)")
r = run(base, model="smart-coder", pc=False)
print(" model alias 'smart-coder' -> window", r["ce"].get("window"), r["ce"].get("window_source"), "caching:", r["ce"].get("caching"))
r = run(base, model="claude-sonnet-4-5", pc=False)
print(" claude-sonnet-4-5 -> window", r["ce"].get("window"), r["ce"].get("window_source"), "caching:", r["ce"].get("caching"), "breakpoints:", r["data"].get("cache_control_injection_points"))

print("== 5d CE failure paths")
async def ce_fail(mode):
    cb = ContextEngineeringCallback(settings=ContextSettings(min_tokens=0, fail_mode=mode))
    class Boom:
        settings = cb.settings; summarizer=None
        def process(self, *a, **k): raise RuntimeError("boom")
    cb._engine = Boom()
    data = {"model":"gpt-4o-mini","messages":copy.deepcopy(base)}
    try:
        out = await cb.async_pre_call_hook(None, None, data, "acompletion")
        return "open: forwarded original=%s" % (out["messages"]==base)
    except HTTPException as e:
        return "closed: HTTP %s" % e.status_code
print(" fail_mode open  ->", asyncio.run(ce_fail("open")))
print(" fail_mode closed ->", asyncio.run(ce_fail("closed")))

print("== 5e Redis store outage inside CE (CONTEXT_STORE=redis)")
class DeadRedis:
    def set(self, *a, **k): time.sleep(0.5); raise ConnectionError("down")
    def get(self, *a, **k): time.sleep(0.5); raise ConnectionError("down")
st = RedisStore(DeadRedis(), 3600)
cb = ContextEngineeringCallback(engine=ContextEngine(ContextSettings(min_tokens=0), store=st))
async def go():
    data = {"model":"gpt-4o-mini","messages":copy.deepcopy(base)}
    t = time.perf_counter()
    out = await cb.async_pre_call_hook(None, None, data, "acompletion")
    return time.perf_counter()-t, out["metadata"]["context_engineering"]
dt, md = asyncio.run(go())
print(" with dead redis: hook took %.2fs, status=%s, error=%s, tokens_after=%s" % (dt, md.get("status"), md.get("error"), md.get("tokens_after")))

print("== 5f compression failure paths")
class RaisingCompressor:
    model_name="x"; 
    def load(self): pass
    def compress(self, *a, **k): raise RuntimeError("model crashed")
from prompt_compression.prompt_compression_callback import PromptCompressionCallback
from prompt_compression.settings import PipelineSettings
import dataclasses
async def pc_fail(mode):
    s = dataclasses.replace(PipelineSettings.from_env(), fail_mode=mode, eager_load=False)
    pipe = PromptPipeline(settings=s, compressor=RaisingCompressor())
    cb = PromptCompressionCallback(pipeline=pipe, settings=s)
    data = {"model":"gpt-4o-mini","messages":copy.deepcopy(cases["E_ticket_lookup"]["msgs"])}
    try:
        out = await cb.async_pre_call_hook(None, None, data, "acompletion")
        return "status=%s forwarded_original=%s" % (out["metadata"]["prompt_compression"]["status"], out["messages"]==cases["E_ticket_lookup"]["msgs"])
    except HTTPException as e:
        return "HTTP %s" % e.status_code
print(" open  ->", asyncio.run(pc_fail("open")))
print(" closed ->", asyncio.run(pc_fail("closed")))
