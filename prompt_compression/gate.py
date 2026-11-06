"""Gate: the first stage. Cheap checks that decide whether the pipeline runs at all.

    disabled / not a chat call   -> pass the request through, silently
    per-request opt-out          -> skip, reported as "skipped"
    too few tokens               -> skip, reported as "skipped" (classifying a tiny prompt costs more than it can save)

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


def check(data: dict, call_type, settings: PipelineSettings) -> GateDecision:
    if call_type not in CHAT_CALL_TYPES or not isinstance(data.get("messages"), list):
        return GateDecision(False, "not_chat", silent=True)
    if not settings.enabled:
        return GateDecision(False, "disabled", silent=True)
    if opted_out(data):
        return GateDecision(False, "request_opt_out")
    if all_text_tokens(data["messages"]) < settings.min_tokens:
        return GateDecision(False, "below_min_size")
    return GateDecision(True)
