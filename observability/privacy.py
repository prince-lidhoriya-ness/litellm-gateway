"""Hashing and scrubbing applied to everything this package exports.

Prompt text never leaves through here: messages are reduced to a salted hash,
a character count and a token count. Free-text values that could contain user
data (error messages, reasons) go through the classifier's own rule layer.
"""

import hashlib
import hmac
from typing import Optional

from prompt_compression import rules

MAX_TEXT_CHARS = 500


def _keyed(value: str, salt: str) -> str:
    # HMAC-SHA256 rather than sha256(salt + value): a keyed hash cannot be recomputed without the key, and the key
    # cannot be confused with a prefix of the value (PROJECT_AUDIT_REPORT.md, F-18S).
    return hmac.new(salt.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()[:16]


def hash_id(value: Optional[object], salt: str) -> Optional[str]:
    """Keyed hash (HMAC-SHA256), 16 hex chars. Used for user, team and end-user ids."""
    if value is None or value == "":
        return None
    return _keyed(str(value), salt)


def fingerprint(text: str, salt: str) -> str:
    """Keyed hash of a message, so identical prompts can be correlated without storing them."""
    return _keyed(text, salt)


def derive_salt(secret: str) -> str:
    """A hashing key derived from another secret (LITELLM_SALT_KEY), for when OBS_HASH_SALT is not set."""
    return hmac.new(secret.encode("utf-8"), b"litellm-gateway/observability/hash-salt", hashlib.sha256).hexdigest()


def scrub(value: object) -> object:
    """Rule-layer redaction for strings; other values pass through unchanged."""
    if not isinstance(value, str):
        return value
    redacted, _ = rules.redact(value)
    return redacted if len(redacted) <= MAX_TEXT_CHARS else redacted[:MAX_TEXT_CHARS] + "..."
