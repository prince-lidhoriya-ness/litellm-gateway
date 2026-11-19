"""Audit harness: runs the project's REAL hooks (context engineering, then prompt compression) in LiteLLM order,
with the real models (offline, pinned). Nothing in the project is modified."""
import asyncio, copy, json, os, sys, time, logging

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("OMP_NUM_THREADS", "4")
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, ROOT)
logging.disable(logging.CRITICAL)

from context_engineering.callback import ContextEngineeringCallback          # noqa: E402
from context_engineering import tokens as tk                                  # noqa: E402
from prompt_compression.prompt_compression_callback import PromptCompressionCallback  # noqa: E402
from prompt_compression.settings import PipelineSettings                      # noqa: E402
from prompt_compression.texts import all_text_tokens                          # noqa: E402

_ce = _pc = None


def hooks(pc_settings=None):
    global _ce, _pc
    if _ce is None:
        _ce = ContextEngineeringCallback()
    if _pc is None or pc_settings is not None:
        _pc = PromptCompressionCallback(settings=pc_settings) if pc_settings else PromptCompressionCallback()
        _pc._build_pipeline(load=True)
    return _ce, _pc


def flat(messages):
    out = []
    for m in messages:
        out.append(tk.message_text(m))
        out.append(tk.tool_calls_text(m))
    return "\n".join(out)


async def arun(messages, model="gpt-4o-mini", metadata=None, ce=True, pc=True, tools=None, extra=None):
    ce_h, pc_h = hooks()
    data = {"model": model, "messages": copy.deepcopy(messages), "metadata": dict(metadata or {})}
    if tools:
        data["tools"] = tools
    if extra:
        data.update(extra)
    t0 = time.perf_counter()
    if ce:
        data = await ce_h.async_pre_call_hook(None, None, data, "acompletion")
    t1 = time.perf_counter()
    if pc:
        data = await pc_h.async_pre_call_hook(None, None, data, "acompletion")
    t2 = time.perf_counter()
    md = data.get("metadata", {})
    return {
        "data": data,
        "ce": md.get("context_engineering", {}),
        "pc": md.get("prompt_compression", {}),
        "tok_before": tk.messages_tokens(messages),
        "tok_after": tk.messages_tokens(data["messages"]),
        "ce_ms": (t1 - t0) * 1000, "pc_ms": (t2 - t1) * 1000,
        "text": flat(data["messages"]),
    }


def run(*a, **k):
    return asyncio.run(arun(*a, **k))


def survive(text, needles):
    return {n: (n in text) for n in needles}
