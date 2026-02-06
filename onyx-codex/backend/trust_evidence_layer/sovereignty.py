from __future__ import annotations

from dataclasses import replace
from typing import Any

from trust_evidence_layer.types import EvidenceSource

JURISDICTIONS = {"EU", "US", "UK", "CA", "UNKNOWN"}
DATA_CLASSIFICATIONS = {"PUBLIC", "INTERNAL", "CONFIDENTIAL", "REGULATED"}


def normalize_jurisdiction(raw: Any) -> str:
    if isinstance(raw, str) and raw.upper() in JURISDICTIONS:
        return raw.upper()
    return "UNKNOWN"


def normalize_data_classification(raw: Any) -> str:
    if isinstance(raw, str) and raw.upper() in DATA_CLASSIFICATIONS:
        return raw.upper()
    return "INTERNAL"


def normalize_allowed_scopes(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return sorted({str(v) for v in raw if v is not None})
    return ["response_generation", "retrieval", "enforcement"]


def enforce_jurisdiction(
    *,
    evidence_sources: list[EvidenceSource],
    allowed_jurisdictions: list[str],
    required_scope: str,
) -> tuple[list[EvidenceSource], list[dict[str, Any]], list[dict[str, Any]], bool]:
    allowed_set = {j.upper() for j in allowed_jurisdictions}
    accepted: list[EvidenceSource] = []
    accepted_meta: list[dict[str, Any]] = []
    rejected_meta: list[dict[str, Any]] = []

    for src in evidence_sources:
        allowed = src.jurisdiction in allowed_set and required_scope in src.allowed_scopes
        meta = {
            "source_id": src.id,
            "jurisdiction": src.jurisdiction,
            "data_classification": src.data_classification,
            "required_scope": required_scope,
        }
        if allowed:
            accepted.append(src)
            accepted_meta.append(meta)
        else:
            reason = "disallowed_jurisdiction" if src.jurisdiction not in allowed_set else "scope_not_allowed"
            meta["reason"] = reason
            rejected_meta.append(meta)

    violation = bool(rejected_meta)
    return accepted, accepted_meta, rejected_meta, violation


def apply_sovereignty_metadata(source: EvidenceSource, *, jurisdiction: str, data_classification: str, allowed_scopes: list[str]) -> EvidenceSource:
    return replace(
        source,
        jurisdiction=normalize_jurisdiction(jurisdiction),
        data_classification=normalize_data_classification(data_classification),
        allowed_scopes=normalize_allowed_scopes(allowed_scopes),
    )
