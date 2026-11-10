"""History management under budget pressure: recent turns stay verbatim, older turns are retrieved or compacted.

    head     system/developer messages and the whole first turn (pinned: its constraints are often irreplaceable)
    recent   the last CONTEXT_RECENT_TURNS turns (never touched here)
    older    everything in between; only the oldest multiple of CONTEXT_COMPACTION_BATCH_TURNS of them is processed,
             so the compacted span grows in steps and the prefix stays identical between steps

A turn is a user message and every assistant/tool message up to the next user message, so a tool call is never
separated from its result. Of the older turns in the span:
    protected  kept verbatim: a deterministic sensitivity hit (rules, topics), or its turn_ ref was mentioned
    retrieved  kept verbatim: JIT retrieval scored it relevant to the current question (only when allowed: by default
               not on providers that cache prompts, because query-dependent selection breaks the cached prefix)
    compacted  replaced, all together, by one summary message (compaction.py) inserted where the first of them was;
               the originals go to the store under their turn_ ref
With compaction off and JIT on, the dropped turns still leave an index-level summary (constraints, open tasks,
decisions, turn refs), so nothing is removed without a trace.
"""

from context_engineering import compaction, retrieval
from context_engineering import tokens as tk
from context_engineering.masking import requested_refs
from context_engineering.settings import ContextSettings
from context_engineering.structures import CachePlan, ContextProfile, HistoryRecord, SUMMARY_MARKER

SYSTEM_ROLES = frozenset({"system", "developer"})


def segment(messages: list) -> tuple[int, list]:
    """(end of the leading system block, [list of message indexes per turn])."""
    head = 0
    while head < len(messages) and messages[head].get("role") in SYSTEM_ROLES:
        head += 1
    turns: list = []
    for index in range(head, len(messages)):
        if messages[index].get("role") == "user" or not turns:
            turns.append([])
        turns[-1].append(index)
    return head, turns


def _sensitive(texts: list) -> bool:
    try:
        from prompt_compression.sensitivity import deterministic_hits

        return any(deterministic_hits(text) for text in texts if text)
    except Exception:
        return True


class HistoryOutcome:
    def __init__(self, messages):
        self.messages = messages
        self.records: list = []
        self.decisions: list = []
        self.summary_index = None
        self.summary_source = ""
        self.pending: list = []        # (span sha, source text) for the background summarizer


def apply(messages: list, profile: ContextProfile, cache_plan: CachePlan, settings: ContextSettings, store,
          summarizer=None) -> HistoryOutcome:
    outcome = HistoryOutcome(list(messages))
    jit_active = settings.jit_enabled and cache_plan.jit_allowed
    if settings.jit_enabled and not cache_plan.jit_allowed:
        outcome.decisions.append(f"jit retrieval skipped: provider caching is {cache_plan.caching}")
    if not settings.compaction_enabled and not jit_active:
        return outcome
    _, turns = segment(messages)
    older = turns[1:max(1, len(turns) - settings.recent_turns)]
    span_size = (len(older) // settings.compaction_batch_turns) * settings.compaction_batch_turns
    if not span_size:
        outcome.decisions.append(
            f"history: {len(older)} older turn(s), below a batch of {settings.compaction_batch_turns}")
        return outcome
    span = older[:span_size]
    wanted = requested_refs(messages, profile)
    entries = []
    for indexes in span:
        turn_messages = [messages[i] for i in indexes]
        ref = compaction.turn_ref(turn_messages)
        texts = [tk.message_text(m) for m in turn_messages] + [tk.tool_calls_text(m) for m in turn_messages]
        protected = ref in wanted or _sensitive(texts) or any(t.startswith(SUMMARY_MARKER) for t in texts)
        entries.append({"ref": ref, "indexes": tuple(indexes), "messages": turn_messages, "protected": protected,
                        "text": "\n".join(t for t in texts if t), "tokens": tk.messages_tokens(turn_messages)})

    retrieved: dict = {}
    if jit_active:
        candidates = [e for e in entries if not e["protected"]]
        query = tk.message_text(messages[profile.last_user_index]) if profile.last_user_index is not None else ""
        try:
            scores, backend = retrieval.score_turns(query, [e["text"] for e in candidates], settings.jit_backend)
            chosen = retrieval.select(scores, settings.jit_max_turns, settings.jit_min_score)
        except Exception as exc:
            # Retrieval failed: keep the whole history rather than drop turns blind.
            outcome.decisions.append(f"jit retrieval failed ({type(exc).__name__}): history left unchanged")
            return outcome
        retrieved = {candidates[i]["ref"]: scores[i] for i in chosen}
        outcome.decisions.append(f"jit retrieval ({backend}): {len(retrieved)} of {len(candidates)} older turn(s) kept")

    compacted = [e for e in entries if not e["protected"] and e["ref"] not in retrieved]
    for entry in entries:
        if entry["protected"]:
            outcome.records.append(HistoryRecord("protected", entry["ref"], entry["indexes"], entry["tokens"]))
        elif entry["ref"] in retrieved:
            outcome.records.append(HistoryRecord("retrieved", entry["ref"], entry["indexes"], entry["tokens"],
                                                 round(retrieved[entry["ref"]], 4)))
    if not compacted:
        outcome.decisions.append("history: nothing to compact (all older turns protected or retrieved)")
        return outcome

    turns_payload = [(e["ref"], e["indexes"], e["messages"]) for e in compacted]
    level = "full" if settings.compaction_enabled else "index"
    sections = compaction.extract_sections(turns_payload, settings)
    summary = compaction.build_summary(turns_payload, settings, level, len(retrieved), sections=sections)
    source = "extractive" if level == "full" else "index"
    sha = compaction.span_sha(turns_payload)
    if settings.compaction_enabled and settings.compaction_mode == "llm" and summarizer is not None:
        model_text = summarizer.lookup(sha)
        if model_text:
            head = compaction.header(turns_payload, sum(e["tokens"] for e in compacted), len(retrieved))
            summary, source = compaction.model_summary_message(head, model_text, sections), "model"
        elif summarizer.wants(sha):
            outcome.pending.append((sha, compaction.source_text(turns_payload)))

    span_tokens = sum(e["tokens"] for e in compacted)
    summary_tokens = tk.text_tokens(summary) + tk.MESSAGE_OVERHEAD
    if summary_tokens > settings.compaction_max_summary_ratio * span_tokens:
        outcome.decisions.append(
            f"compaction skipped: summary {summary_tokens} tokens vs span {span_tokens} (ratio cap "
            f"{settings.compaction_max_summary_ratio})")
        outcome.records = [r for r in outcome.records if r.action != "retrieved"]
        return outcome

    for entry in compacted:
        stored = store.put(entry["ref"], {"kind": "turn", "ref": entry["ref"], "indexes": list(entry["indexes"]),
                                          "messages": entry["messages"]}, sensitive=False)
        outcome.records.append(HistoryRecord("compacted", entry["ref"], entry["indexes"], entry["tokens"]))
        if not stored:
            outcome.decisions.append(f"history: {entry['ref']} not stored (store {getattr(store, 'backend', '?')})")
    drop = {i for e in compacted for i in e["indexes"]}
    first = min(drop)
    result = []
    for index, message in enumerate(messages):
        if index == first:
            outcome.summary_index = len(result)
            result.append({"role": "user", "content": summary})
        if index not in drop:
            result.append(message)
    outcome.messages = result
    outcome.summary_source = source
    outcome.decisions.append(f"history: {len(compacted)} turn(s), {span_tokens} tokens -> summary {summary_tokens} "
                             f"tokens ({source})")
    return outcome
