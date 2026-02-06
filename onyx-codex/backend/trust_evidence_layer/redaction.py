from __future__ import annotations

import re
from typing import Any

EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?\d{1,2}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})\b")
NATIONAL_ID_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
MEDICAL_RECORD_RE = re.compile(r"\bMRN[-:\s]?\d{6,10}\b", re.IGNORECASE)

_PATTERNS = [
    ("EMAIL", EMAIL_RE),
    ("PHONE", PHONE_RE),
    ("NATIONAL_ID", NATIONAL_ID_RE),
    ("MEDICAL_RECORD", MEDICAL_RECORD_RE),
]


def redact_text(text: str) -> tuple[str, list[dict[str, Any]]]:
    redacted = text
    events: list[dict[str, Any]] = []
    for label, pattern in _PATTERNS:
        matches = pattern.findall(redacted)
        if not matches:
            continue
        redacted = pattern.sub(f"[REDACTED_{label}]", redacted)
        events.append(
            {
                "policy_id": "pii_redaction",
                "detector": label,
                "count": len(matches),
            }
        )
    return redacted, events
