from __future__ import annotations

import hashlib
from typing import Any

from trust_evidence_layer.sovereignty import normalize_allowed_scopes
from trust_evidence_layer.sovereignty import normalize_data_classification
from trust_evidence_layer.sovereignty import normalize_jurisdiction
from trust_evidence_layer.types import EvidenceSource

TRUST_LEVELS = {"PRIMARY", "SECONDARY", "UNVERIFIED"}
ORIGINS = {"INTERNAL", "CUSTOMER", "THIRD_PARTY", "TOOL"}


def source_hash(*, source_id: str, snippet: str, title: str | None) -> str:
    payload = f"{source_id}|{title or ''}|{snippet}".encode("utf-8", errors="ignore")
    return hashlib.sha256(payload).hexdigest()


def _normalize_trust_level(raw: Any, *, origin: str, trusted_tool: bool) -> str:
    if isinstance(raw, str) and raw.upper() in TRUST_LEVELS:
        return raw.upper()
    if origin == "TOOL":
        return "SECONDARY" if trusted_tool else "UNVERIFIED"
    return "SECONDARY"


def _normalize_origin(raw: Any) -> str:
    if isinstance(raw, str):
        candidate = raw.upper()
        if candidate in ORIGINS:
            return candidate
    return "THIRD_PARTY"


def _normalize_confidence_weight(raw: Any, trust_level: str) -> float:
    if isinstance(raw, (int, float)):
        val = float(raw)
    else:
        val = {"PRIMARY": 0.9, "SECONDARY": 0.6, "UNVERIFIED": 0.2}[trust_level]
    return max(0.0, min(1.0, val))


def normalize_raw_evidence(
    raw_items: list[dict[str, Any]],
    *,
    trusted_tools: set[str] | None = None,
) -> list[EvidenceSource]:
    normalized: list[EvidenceSource] = []
    seen: set[str] = set()
    trusted_tools = {t.lower() for t in (trusted_tools or set())}

    for idx, item in enumerate(raw_items):
        source_id = str(
            item.get("id")
            or item.get("document_id")
            or item.get("uri")
            or f"source_{idx}"
        )
        snippet = str(item.get("snippet") or item.get("blurb") or "").strip()
        if not snippet:
            continue

        title = item.get("title") or item.get("semantic_identifier")
        uri_or_path = item.get("uri") or item.get("link")
        offsets = item.get("offsets") if isinstance(item.get("offsets"), dict) else None

        origin = _normalize_origin(item.get("origin"))
        tool_name = str(item.get("tool_name") or "").lower()
        trusted_tool = bool(tool_name and tool_name in trusted_tools)
        trust_level = _normalize_trust_level(
            item.get("trust_level"), origin=origin, trusted_tool=trusted_tool
        )
        confidence_weight = _normalize_confidence_weight(
            item.get("confidence_weight"), trust_level
        )
        jurisdiction = normalize_jurisdiction(item.get("jurisdiction"))
        data_classification = normalize_data_classification(item.get("data_classification"))
        allowed_scopes = normalize_allowed_scopes(item.get("allowed_scopes"))

        ev_hash = source_hash(source_id=source_id, snippet=snippet, title=title)

        dedup_key = f"{source_id}:{ev_hash}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        normalized.append(
            EvidenceSource(
                id=source_id,
                title=title,
                uri_or_path=uri_or_path,
                snippet=snippet,
                offsets=offsets,
                hash=ev_hash,
                trust_level=trust_level,
                origin=origin,
                confidence_weight=confidence_weight,
                jurisdiction=jurisdiction,
                data_classification=data_classification,
                allowed_scopes=allowed_scopes,
            )
        )

    return normalized
