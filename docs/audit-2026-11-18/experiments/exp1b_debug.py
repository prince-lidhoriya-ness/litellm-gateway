"""Debug follow-up: cold vs warm compression cache, where the reduction comes from, and what happened to the needles."""
import asyncio
import json
import os
import sys

SP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SP)
import exp1_workloads as e  # noqa: E402  (same workloads, same seed)

from prompt_compression.prompt_compression_callback import PromptCompressionCallback  # noqa: E402


def action_counts(meta):
    counts = {}
    for entry in meta.get("messages", []):
        key = entry.get("action", "?")
        counts[key] = counts.get(key, 0) + 1
    return counts


def segment_totals(meta):
    totals = {}
    for entry in meta.get("messages", []):
        for k, v in (entry.get("segments") or {}).items():
            if isinstance(v, (int, float)):
                totals[k] = totals.get(k, 0) + v
    return {k: v for k, v in totals.items() if v}


async def main():
    W = e.workloads()
    for name in ["W2_long_doc_lookup", "W3_long_doc_summarize", "W5_debug_session", "W7_long_chat", "W8_large_40k_prose"]:
        spec = W[name]
        pc = PromptCompressionCallback()  # fresh instance => cold compression cache
        for phase in ("cold", "warm"):
            data, wall = await e.run(None, pc, spec["messages"], spec.get("tools"), ce=False, pc=True)
            meta = data["metadata"].get("prompt_compression", {})
            before = e.total_tokens(spec["messages"])
            after = e.total_tokens(data["messages"])
            print(json.dumps({
                "workload": name, "phase": phase, "wall_ms": wall, "elapsed_ms_reported": meta.get("elapsed_ms"),
                "status": meta.get("status"), "intent": meta.get("intent"), "routes": meta.get("routes"),
                "category": meta.get("category"), "reduction_pct": round(100 * (before - after) / before, 1),
                "compress_calls": meta.get("compress_calls"), "compress_stopped": meta.get("compress_stopped"),
                "actions": action_counts(meta), "segments": segment_totals(meta), "kept": meta.get("kept"),
            }, default=str), flush=True)
            if name in ("W2_long_doc_lookup", "W3_long_doc_summarize", "W5_debug_session") and phase == "cold":
                # which needle sentences survived, and what the compressed text looks like around them
                out_text = "\n".join(t for m in data["messages"] for _, t in e.text_parts(m))
                for needle in spec["needles"] + ["Tanaka"]:
                    idx = out_text.find(needle)
                    print("  needle", repr(needle), "present" if idx >= 0 else "MISSING",
                          ("| ..." + out_text[max(0, idx - 120): idx + 60].replace("\n", " ") + "...") if idx >= 0 else "")
                # the original needle sentences, to compare
                for line in e.NEEDLE_SENTENCES:
                    if any(tok in line for tok in spec["needles"]):
                        print("  original:", line)
                        # find its closest surviving fragment
                        key = line.split(",")[0][-30:]
                        print("  compressed fragment near 'ESC'/'MAX'/'E_CONN'/'184':",
                              [out_text[max(0, out_text.find(t) - 60): out_text.find(t) + 40].replace("\n", " ")
                               for t in ("ESC", "184", "MAX_", "E_CONN") if out_text.find(t) >= 0][:2])
    return


if __name__ == "__main__":
    asyncio.run(main())
