"""Experiment 5: (a) cost of the prompt-compression size gate just above and just below 32,000 tokens; (b) what the model
sees for a masked tool output (context-engineering stub), built by the production masking code."""
import asyncio
import json
import os
import sys
import time

SP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SP)
import exp1_workloads as e  # noqa: E402

from prompt_compression.prompt_compression_callback import PromptCompressionCallback  # noqa: E402
from context_engineering import masking  # noqa: E402
from context_engineering.settings import ContextSettings  # noqa: E402


async def gate_timing():
    pc = PromptCompressionCallback()
    rows = []
    for paragraphs in (240, 300, 360):
        text = e.doc(paragraphs, needles=False)
        msgs = [e.msg("user", text + "\n\nWhat was the escalation reference?")]
        tokens = e.total_tokens(msgs)
        data = {"model": "gpt-4o", "messages": msgs, "metadata": {}}
        t = time.perf_counter()
        out = await pc.async_pre_call_hook(None, None, data, "acompletion")
        wall = round((time.perf_counter() - t) * 1000, 1)
        m = out["metadata"].get("prompt_compression", {})
        rows.append({"input_tokens": tokens, "status": m.get("status"), "reason": m.get("reason") or m.get("error"),
                     "stop": m.get("compress_stopped"), "wall_ms": wall})
        print("GATE", rows[-1], flush=True)
    return rows


def stub_sample():
    # one large grep-style tool output (about 600 tokens), preceded by an assistant tool call, then a later assistant
    # message that follows it, so the stub's follow-up line is realistic.
    output = e.tool_output(45)
    msgs = [
        e.msg("system", e.SYSTEM),
        e.msg("user", "Find the cause of the export failure."),
        {"role": "assistant", "content": None, "tool_calls": [{"id": "c0", "type": "function", "function": {
            "name": "read_file", "arguments": json.dumps({"path": "exporter/client.py"})}}]},
        e.msg("tool", output, tool_call_id="c0"),
        e.msg("assistant", "The send path retries on 429 only. I will check the backoff next."),
        e.msg("user", "Continue."),
    ]
    settings = ContextSettings(observation_max_tokens=400, observation_keep_recent=0, observation_batch=1)
    profile = __import__("context_engineering.analyzer", fromlist=["analyze"]).analyze(msgs, None, "", 3)
    store = __import__("context_engineering.store", fromlist=["MemoryStore"]).MemoryStore()
    out, records, decisions = masking.mask(msgs, profile, settings, frozenset({"mask"}), store)
    stub_text = out[3]["content"]
    return {"original_tokens": e.count_tokens(output), "stub_tokens": e.count_tokens(stub_text),
            "original_head": output[:300], "stub": stub_text, "decisions": decisions, "records": [r.__dict__ for r in records]}


def main():
    rows = asyncio.run(gate_timing())
    stub = stub_sample()
    out = {"gate": rows, "stub": stub}
    with open(os.path.join(SP, "exp5_results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    print("STUB original_tokens", stub["original_tokens"], "stub_tokens", stub["stub_tokens"], flush=True)
    print(stub["stub"], flush=True)


if __name__ == "__main__":
    main()
