"""Hashing and scrubbing applied to everything this package exports.

Prompt text never leaves through here: messages are reduced to a salted hash,
a character count and a token count. Free-text values that could contain user
data (error messages, reasons) go through the classifier's own rule layer.
"""

import hashlib
from typing import Optional

from prompt_compression import rules

MAX_TEXT_CHARS = 500


def hash_id(value: Optional[object], salt: str) -> Optional[str]:
    """Salted sha256, 16 hex chars. Used for user, team and end-user ids."""
    if value is None or value == "":
        return None
    return hashlib.sha256(f"{salt}{value}".encode("utf-8")).hexdigest()[:16]


def fingerprint(text: str, salt: str) -> str:
    """Salted sha256 of a message, so identical prompts can be correlated without storing them."""
    return hashlib.sha256(f"{salt}{text}".encode("utf-8")).hexdigest()[:16]


def scrub(value: object) -> object:
    """Rule-layer redaction for strings; other values pass through unchanged."""
    if not isinstance(value, str):
        return value
    redacted, _ = rules.redact(value)
    return redacted if len(redacted) <= MAX_TEXT_CHARS else redacted[:MAX_TEXT_CHARS] + "..."
