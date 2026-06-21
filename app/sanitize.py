from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

MAX_MESSAGE_LENGTH = 2000

PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("pan", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)),
    ("aadhaar", re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"(?:\+91[\s-]?)?\b[6-9]\d{9}\b")),
    ("otp", re.compile(r"\b(?:otp|one[\s-]?time[\s-]?password)\s*[:\s]?\d{4,8}\b", re.IGNORECASE)),
    (
        "account_number",
        re.compile(r"\b(?:account|a/c|acct)[\s#:.-]*\d{6,}\b", re.IGNORECASE),
    ),
)


class SanitizeReason(str, Enum):
    OK = "ok"
    EMPTY = "empty"
    TOO_LONG = "too_long"
    PII = "pii"


@dataclass(frozen=True)
class SanitizeResult:
    text: str
    reason: SanitizeReason
    pii_type: str | None = None

    @property
    def blocked(self) -> bool:
        return self.reason == SanitizeReason.PII


def detect_pii(text: str) -> str | None:
    for label, pattern in PII_PATTERNS:
        if pattern.search(text):
            return label
    return None


def sanitize_message(message: str) -> SanitizeResult:
    text = message.strip()
    if not text:
        return SanitizeResult(text="", reason=SanitizeReason.EMPTY)
    if len(text) > MAX_MESSAGE_LENGTH:
        return SanitizeResult(text=text, reason=SanitizeReason.TOO_LONG)
    pii_type = detect_pii(text)
    if pii_type:
        return SanitizeResult(text=text, reason=SanitizeReason.PII, pii_type=pii_type)
    return SanitizeResult(text=text, reason=SanitizeReason.OK)
