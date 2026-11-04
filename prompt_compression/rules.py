"""Deterministic sensitive-data rules. A hit forces the `sensitive` label.

Each rule is a regex plus an optional validator (Luhn for cards, mod-97 for
IBANs). Rules run before the model, so a secret is never routed to lossy
compression even if the model misses it. `redact()` replaces matched spans with
placeholders such as [EMAIL] when REDACT_SENSITIVE=true.
"""

import re
from dataclasses import dataclass
from typing import Callable, Optional


def luhn_valid(number: str) -> bool:
    digits = [int(ch) for ch in number if ch.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def iban_valid(value: str) -> bool:
    compact = re.sub(r"\s", "", value).upper()
    if not 15 <= len(compact) <= 34:
        return False
    rearranged = compact[4:] + compact[:4]
    numeric = "".join(str(int(ch, 36)) for ch in rearranged)
    return int(numeric) % 97 == 1


def ssn_valid(value: str) -> bool:
    area, group, serial = value.split("-")
    return area not in ("000", "666") and not area.startswith("9") and group != "00" and serial != "0000"


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern
    placeholder: str
    validator: Optional[Callable[[str], bool]] = None
    # Regex group to redact; 0 = whole match. Lets "password: X" keep the keyword.
    group: int = 0


_I = re.IGNORECASE

RULES = (
    Rule(
        "private_key",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY(?: BLOCK)?-----"
                   r"[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY(?: BLOCK)?-----|$)"),
        "[PRIVATE_KEY]",
    ),
    Rule("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    Rule(
        "credit_card",
        re.compile(r"(?<![\d-])(?:\d[ -]?){12,18}\d(?![\d-])"),
        "[CREDIT_CARD]",
        validator=luhn_valid,
    ),
    Rule(
        "iban",
        re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?\b"),
        "[IBAN]",
        validator=iban_valid,
    ),
    Rule("us_ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[NATIONAL_ID]", validator=ssn_valid),
    Rule(
        # Keyword-anchored IDs: passport, national ID, driver's license, tax ID, MRN, etc.
        "national_id",
        re.compile(
            r"\b(?:passport(?: number| no\.?)?|national id(?: number)?|driver'?s licen[cs]e|"
            r"licen[cs]e number|tax id|aadhaar(?: number)?|pan number|mrn|medical record number|"
            r"social security(?: number)?|ssn)\b[\s:#]*(?:is\s+)?((?=[A-Z0-9-]*\d)[A-Z0-9][A-Z0-9-]{5,})",
            _I,
        ),
        "[NATIONAL_ID]",
        group=1,
    ),
    Rule(
        "bank_account",
        re.compile(r"\b(?:routing|account|acct|sort code|iban|swift|bic)(?: number| no\.?)?\b[\s:#]*(?:is\s+)?(\d[\d -]{5,}\d)", _I),
        "[BANK_ACCOUNT]",
        group=1,
    ),
    Rule(
        "phone",
        re.compile(r"(?<![\w-])(?:\+\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?![\w-])"),
        "[PHONE]",
    ),
    Rule("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "[API_KEY]"),
    Rule("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"), "[API_KEY]"),
    Rule("openai_style_key", re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}\b"), "[API_KEY]"),
    Rule("stripe_key", re.compile(r"\b[rs]k_(?:live|test)_[A-Za-z0-9]{16,}\b"), "[API_KEY]"),
    Rule("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "[API_KEY]"),
    Rule("slack_token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b"), "[API_KEY]"),
    Rule("slack_webhook", re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9/]+"), "[API_KEY]"),
    Rule("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), "[TOKEN]"),
    Rule("bearer_token", re.compile(r"\bBearer\s+([A-Za-z0-9._~+/-]{20,}=*)", _I), "[TOKEN]", group=1),
    Rule(
        # key=value / key: value secrets, e.g. API_KEY=..., client_secret: ...
        "secret_assignment",
        re.compile(
            r"\b[\w-]*(?:api[_-]?key|secret|token|access[_-]?key|private[_-]?key|client[_-]?secret)[\w-]*"
            r"\s*[:=]\s*[\"']?([^\s\"',]{8,})",
            _I,
        ),
        "[SECRET]",
        group=1,
    ),
    Rule(
        "credentials_in_url",
        re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@]+:([^\s@/]+)@", _I),
        "[PASSWORD]",
        group=1,
    ),
    Rule(
        "password",
        re.compile(
            r"\b(?:password|passwd|pwd|passcode|passphrase)\b(?:\s+(?:for|of)\s+[\w\s'-]{1,30}?)?"
            r"\s*,?\s*(?:is|it'?s|:|=|-)\s*[\"']?([^\s\"',]{4,})",
            _I,
        ),
        "[PASSWORD]",
        group=1,
    ),
    Rule(
        "pin",
        re.compile(r"\bpin\b(?:\s+(?:for|of)\s+[\w\s'-]{1,30}?)?\s*(?:is|:|=)\s*(\d{4,8})\b", _I),
        "[PIN]",
        group=1,
    ),
    Rule(
        # "login is admin / P@ssw0rd" or "with password X" style
        "login_pair",
        re.compile(r"\b(?:login|credentials|creds|username)\b[^\n]{0,40}?\s/\s*(\S{4,})", _I),
        "[PASSWORD]",
        group=1,
    ),
    Rule("with_password", re.compile(r"\bwith password\s+(\S{4,})", _I), "[PASSWORD]", group=1),
)


@dataclass(frozen=True)
class RuleMatch:
    rule: str
    start: int
    end: int
    placeholder: str


def find_matches(text: str) -> list[RuleMatch]:
    matches = []
    for rule in RULES:
        for match in rule.pattern.finditer(text):
            if rule.validator is not None and not rule.validator(match.group(0)):
                continue
            start, end = match.span(rule.group)
            if start < 0 or end <= start:
                continue
            matches.append(RuleMatch(rule.name, start, end, rule.placeholder))
    return matches


def rule_hits(text: str) -> list[str]:
    """Names of the rules that matched, sorted and de-duplicated."""
    return sorted({match.rule for match in find_matches(text)})


def redact(text: str) -> tuple[str, list[str]]:
    """Replace every matched span with its placeholder; returns (text, rule names)."""
    redacted, names, _ = redact_with_count(text)
    return redacted, names


def redact_with_count(text: str) -> tuple[str, list[str], int]:
    """Like redact(), plus the number of spans replaced (for observability)."""
    matches = sorted(find_matches(text), key=lambda m: (m.start, -(m.end - m.start)))
    kept, last_end = [], -1
    for match in matches:
        if match.start >= last_end:
            kept.append(match)
            last_end = match.end
    redacted = text
    for match in reversed(kept):
        redacted = redacted[: match.start] + match.placeholder + redacted[match.end :]
    return redacted, sorted({match.rule for match in kept}), len(kept)
