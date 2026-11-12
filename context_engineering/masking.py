"""Observation masking: fold duplicate tool outputs and replace large, older ones with a compact, verbatim stub.

Rules (docs/context-engineering-blueprint.md 5.7):
  * eligible: a tool/function result with text content that is not pinned (not after the last assistant message) and
    not already a gateway stub
  * duplicates: a later output byte-identical to an earlier one becomes a pointer to the earlier one (no loss: the
    content is still in the context, above). The earlier copy stays, so the prefix does not change.
  * age: of the eligible outputs larger than OBSERVATION_MAX_TOKENS, the newest OBSERVATION_KEEP_RECENT stay in full;
    older ones are masked in batches of OBSERVATION_MASK_BATCH, so the masked set changes only every few tool calls
    and consecutive requests share a byte-identical prefix
  * never masked: error outputs among the newest OBSERVATION_ERROR_GUARD tool results (active debugging), and any
    observation whose ref the latest user or assistant message mentions (that is how a masked output is asked back)
  * the stub keeps the tool_call_id, the name and the role; only the content changes. Key lines are copied verbatim.
  * the original goes to the store under its ref (obs_<sha256[:12]> of the content, so the ref is deterministic)
"""

import re
from typing import Optional

from context_engineering import extract
from context_engineering import tokens as tk
from context_engineering.settings import ContextSettings
from context_engineering.structures import (
    DUPLICATE_MARKER, STUB_MARKER, TOOL_OUTPUT, ContextProfile, MaskRecord,
)

REF_PATTERN = re.compile(r"\b(obs|turn)_[0-9a-f]{12}\b")


def observation_ref(content_sha: str) -> str:
    return "obs_" + content_sha[:12]


def requested_refs(messages: list, profile: ContextProfile) -> set:
    """Refs mentioned by the latest user message or the last assistant message: those originals are wanted back."""
    refs = set()
    for index in (profile.last_user_index, profile.last_assistant_index):
        if index is not None:
            refs.update(match.group(0) for match in REF_PATTERN.finditer(tk.message_text(messages[index])))
            refs.update(match.group(0) for match in REF_PATTERN.finditer(tk.tool_calls_text(messages[index])))
    return refs


def _text_only(message: dict) -> bool:
    content = message.get("content")
    if isinstance(content, str):
        return True
    return isinstance(content, list) and bool(content) and all(
        isinstance(part, dict) and part.get("type") == "text" for part in content
    )


def _set_content(message: dict, text: str) -> None:
    if isinstance(message.get("content"), list):
        message["content"] = [{"type": "text", "text": text}]
    else:
        message["content"] = text


def _follow_up(messages: list, index: int) -> str:
    """The first assistant message after a tool result: fixed once written, so the stub stays stable."""
    for message in messages[index + 1:]:
        if message.get("role") == "assistant":
            return tk.message_text(message)
    return ""


def build_stub(ref: str, tool_name: str, original: str, follow_up: str, settings: ContextSettings,
               stored: bool) -> str:
    lines = original.splitlines()
    header = (f"{STUB_MARKER}{ref} masked by gateway | tool={tool_name or 'unknown'} | "
              f"{tk.text_tokens(original)} tokens, {len(lines)} lines | original {'stored' if stored else 'not stored'}]")
    body = []
    shape = extract.json_shape(original)
    if shape:
        body.append(f"Structure: {shape}")
    kept = extract.key_lines(original, follow_up, settings.observation_stub_max_tokens, settings.observation_head_tail_lines)
    if kept:
        body.append("Key lines (verbatim):")
        body.extend(kept)
    footer = f"[Full output omitted to save context. To restore it, mention {ref} in a message, or call the tool again.]"
    return "\n".join([header, *body, footer])


def mask(messages: list, profile: ContextProfile, settings: ContextSettings, techniques: frozenset, store
         ) -> tuple[list, list, list]:
    """Returns (messages, MaskRecords, decisions). `messages` is a new list; changed messages are copies."""
    out = list(messages)
    records: list = []
    decisions: list = []
    requested = requested_refs(messages, profile)
    eligible = [
        item for item in profile.items
        if item.category == TOOL_OUTPUT and not item.pinned and not item.gateway_made and _text_only(messages[item.index])
    ]
    if not eligible:
        return out, records, decisions

    def apply(item, reason: str, stub: str, stored: bool) -> None:
        message = dict(messages[item.index])
        _set_content(message, stub)
        after = tk.message_tokens(message)
        if after >= item.tokens:
            decisions.append(f"mask skipped #{item.index}: stub not shorter")
            return
        out[item.index] = message
        records.append(MaskRecord(item.index, observation_ref(item.content_sha), reason, item.tool_name or "",
                                  item.tool_call_id or "", item.tokens, after, stored))

    duplicates = set()
    eligible_indexes = {item.index for item in eligible}
    if "dedupe" in techniques:
        first_seen: dict = {}
        for item in profile.items:
            if item.category != TOOL_OUTPUT or item.gateway_made:
                continue
            if (item.content_sha in first_seen and item.index in eligible_indexes
                    and item.tokens >= settings.dedup_min_tokens):
                ref = observation_ref(item.content_sha)
                if ref in requested:
                    continue
                stub = (f"{DUPLICATE_MARKER}{ref} (message #{first_seen[item.content_sha]}) | "
                        f"tool={item.tool_name or 'unknown'}: identical content omitted]")
                apply(item, "duplicate", stub, stored=False)
                duplicates.add(item.index)
            else:
                first_seen.setdefault(item.content_sha, item.index)

    if "mask" in techniques:
        guarded = {
            item.index for item in profile.items
            if item.is_error and item.tool_rank is not None and item.tool_rank < settings.observation_error_guard
        }
        candidates = [
            item for item in eligible
            if item.index not in duplicates and item.index not in guarded and item.tokens > settings.observation_max_tokens
            and observation_ref(item.content_sha) not in requested
        ]
        if guarded:
            decisions.append(f"mask: {len(guarded)} recent error output(s) kept (active debugging)")
        restored = [item.index for item in eligible if observation_ref(item.content_sha) in requested]
        if restored:
            decisions.append(f"mask: {len(restored)} observation(s) kept because their ref was mentioned")
        surplus = max(0, len(candidates) - settings.observation_keep_recent)
        count = (surplus // settings.observation_batch) * settings.observation_batch
        if surplus and not count:
            decisions.append(f"mask: {surplus} candidate(s) wait for a full batch of {settings.observation_batch}")
        for item in candidates[:count]:
            original = tk.message_text(messages[item.index])
            ref = observation_ref(item.content_sha)
            # Only a store that leaves the process cares (RedisStore refuses sensitive content); the regex scan
            # costs tens of milliseconds on a large output, so it is skipped for the in-memory store.
            sensitive = _sensitive(original) if getattr(store, "backend", "") == "redis" else False
            stored = store.put(ref, {
                "kind": "observation", "ref": ref, "tool": item.tool_name, "tool_call_id": item.tool_call_id,
                "content": messages[item.index].get("content"),
            }, sensitive=sensitive)
            stub = build_stub(ref, item.tool_name or "", original, _follow_up(messages, item.index), settings, stored)
            apply(item, "age", stub, stored)
    return out, records, decisions


def _sensitive(text: str) -> bool:
    try:
        from prompt_compression.sensitivity import deterministic_hits

        return bool(deterministic_hits(text))
    except Exception:
        return True        # unknown: treat as sensitive so nothing leaves the process


def recover_observation(store, ref: str) -> Optional[dict]:
    return store.get(ref)


def restored_count(messages: list, profile: ContextProfile) -> int:
    """Tool outputs left in full on this request because the latest user or assistant message mentioned their ref."""
    wanted = requested_refs(messages, profile)
    if not wanted:
        return 0
    return sum(1 for item in profile.items
               if item.category == TOOL_OUTPUT and not item.gateway_made and observation_ref(item.content_sha) in wanted)
