"""Gate: the first stage. Cheap checks that decide whether the pipeline runs at all.

    disabled / not a chat call   -> pass the request through, silently
    per-request opt-out          -> skip, reported as "skipped"
    too few tokens               -> skip, reported as "skipped" (classifying a tiny prompt costs more than it can save)
    too many tokens              -> skip, reported as "skipped" (the work would not finish inside the timeout)

The token checks need a full tiktoken pass over the prompt (about 200 ms for 2 MB of text), so the hook runs them in its
worker thread through size_check(), not on the event loop (PROJECT_AUDIT_REPORT.md, F-04); check() only runs them when
asked to (count_tokens=True, the default, for direct callers).

The timeout and the fail-open / fail-closed behaviour belong to the hook (prompt_compression_callback.py), which wraps
the whole pipeline: on a timeout or an error the original prompt is sent ("Fail open") or the request is rejected.
"""

from dataclasses import dataclass

from prompt_compression.settings import PipelineSettings
from prompt_compression.texts import all_text_tokens

CHAT_CALL_TYPES = frozenset({"completion", "acompletion"})
METADATA_KEY = "prompt_compression"


@dataclass(frozen=True)
class GateDecision:
    allow: bool
    reason: str = ""
    # True: not worth a metadata entry (the request is not a chat call, or compression is switched off).
    silent: bool = False


def metadata_dicts(data: dict) -> list[dict]:
    return [data[key] for key in ("metadata", "litellm_metadata") if isinstance(data.get(key), dict)]


def opted_out(data: dict) -> bool:
    """Per-request opt-out: metadata {"prompt_compression": false} or {"disable_prompt_compression": true}."""
    for metadata in metadata_dicts(data):
        if metadata.get(METADATA_KEY) is False or str(metadata.get(METADATA_KEY)).lower() == "false":
            return True
        if metadata.get("disable_prompt_compression") in (True, "true", "True"):
            return True
    return False


def is_chat(data: dict, call_type) -> bool:
    return call_type in CHAT_CALL_TYPES and isinstance(data.get("messages"), list)


def size_check(messages: list, settings: PipelineSettings) -> GateDecision:
    """The token-count part of the gate: below min_tokens or above max_input_tokens skips the pipeline."""
    tokens = all_text_tokens(messages)
    if tokens < settings.min_tokens:
        return GateDecision(False, "below_min_size")
    if settings.max_input_tokens > 0 and tokens > settings.max_input_tokens:
        return GateDecision(False, "too_large")
    return GateDecision(True)


def check(data: dict, call_type, settings: PipelineSettings, count_tokens: bool = True) -> GateDecision:
    if not is_chat(data, call_type):
        return GateDecision(False, "not_chat", silent=True)
    if not settings.enabled:
        return GateDecision(False, "disabled", silent=True)
    if opted_out(data):
        return GateDecision(False, "request_opt_out")
    if count_tokens:
        return size_check(data["messages"], settings)
    return GateDecision(True)
