"""Conversation-randomised holdout (reports/production-readiness-audit/STRATEGY.md, H2 and Phase 2.1).

A share of conversations (GATEWAY_HOLDOUT_SHARE, e.g. 0.05) is sent entirely unoptimised: both stages run as in shadow
mode for them (they compute and report, the provider gets the original request). Comparing billed cost per conversation
and latency between the arms is the only defensible dollar figure (STRATEGY.md, H2).

Why per conversation, not per request: provider prompt caching works per conversation, so a per-request split would put
both arms inside one cache and bias the comparison.

The arm is decided once per request, by the measurement hook that runs before both stages (observability/measurement.py,
first in litellm_config.yaml callbacks), and written to the request metadata. The stages only read it (is_holdout). With
the measurement hook not registered there is no arm, and nothing changes.

The conversation identity is a salted hash, never text: the client's own session id when it sends one (metadata
session_id / conversation_id, or litellm_session_id), else the system/developer text plus the first user message. Both
stay the same across the turns of a conversation. A system prompt that changes between turns (a date in it) changes the
identity; send a session id to avoid that.
"""

import hashlib
import json
from typing import Optional

METADATA_KEY = "gateway_holdout"
HOLDOUT = "holdout"
TREATMENT = "treatment"
EXCLUDED = "excluded"     # opted out of optimisation by the client: not part of the comparison
INTERNAL = "internal"     # the gateway's own calls (quality re-runs, judge, compaction): never compared, cost kept apart
ARMS = (HOLDOUT, TREATMENT, EXCLUDED, INTERNAL)

_SESSION_KEYS = ("session_id", "conversation_id")


def _metadata_dicts(data: dict) -> list:
    return [data[key] for key in ("metadata", "litellm_metadata") if isinstance(data.get(key), dict)]


def message_text(message: dict) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return "" if content is None else json.dumps(content, sort_keys=True, default=str)


def conversation_key(data: dict, salt: str = "") -> str:
    """16 hex characters identifying the conversation of this request; the same on every turn."""
    session = data.get("litellm_session_id")
    for metadata in _metadata_dicts(data):
        for name in _SESSION_KEYS:
            if session is None and metadata.get(name):
                session = metadata.get(name)
    if session is not None:
        basis = f"session\x1f{session}"
    else:
        messages = data.get("messages") or []
        system = "\n".join(message_text(m) for m in messages if isinstance(m, dict) and m.get("role") in ("system", "developer"))
        first_user = next((message_text(m) for m in messages if isinstance(m, dict) and m.get("role") == "user"), "")
        basis = f"messages\x1f{system}\x1f{first_user}"
    return hashlib.sha256(f"{salt}\x1f{basis}".encode("utf-8", "surrogatepass")).hexdigest()[:16]


def assign(key: str, share: float) -> str:
    """HOLDOUT for a stable `share` of conversation keys, else TREATMENT."""
    if share <= 0:
        return TREATMENT
    return HOLDOUT if int(key[:8], 16) / 0x100000000 < min(share, 1.0) else TREATMENT


def decision(data: dict) -> Optional[dict]:
    """The {"arm": ..., "key": ...} the measurement hook wrote for this request, or None."""
    for metadata in _metadata_dicts(data):
        value = metadata.get(METADATA_KEY)
        if isinstance(value, dict) and value.get("arm") in ARMS:
            return value
    return None


def is_holdout(data: dict) -> bool:
    found = decision(data)
    return bool(found) and found.get("arm") == HOLDOUT


def user_turn(data: dict) -> int:
    """How many user messages the request carries: 1 on the first turn of a conversation."""
    return sum(1 for m in data.get("messages") or [] if isinstance(m, dict) and m.get("role") == "user")


def write(data: dict, arm: str, key: str, turn: int = 0) -> None:
    """Record the decision in the request metadata and in spend_logs_metadata (so it reaches the spend logs, where the
    per-conversation report groups by key). Hash, arm and turn number only, no text. The turn is recorded here, before
    any stage: with turn_off_message_logging the success callbacks only see scrubbed messages."""
    if not isinstance(data.get("metadata"), dict):
        data["metadata"] = {}
    metadata = data["metadata"]
    value = {"arm": arm, "key": key, "turn": turn}
    metadata[METADATA_KEY] = value
    spend = dict(metadata.get("spend_logs_metadata") or {})
    spend[METADATA_KEY] = value
    metadata["spend_logs_metadata"] = spend
