from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class SystemBehaviorClaim:
    system_claim_id: str
    description: str
    scope: str
    enforced_by: list[str]
    evidence: list[str]
    valid_from: str
    valid_to: str | None
    version: str


_SYSTEM_BEHAVIOR_CLAIMS: list[SystemBehaviorClaim] = [
    SystemBehaviorClaim(
        system_claim_id="SYS-RESP-001",
        description="System enforces strict four-key response contract at boundary",
        scope="enforcement",
        enforced_by=["trust_evidence_layer/gate.py", "trust_evidence_layer/boundary.py"],
        evidence=["test_schema_contract.py", "test_no_raw_output_any_endpoint.py"],
        valid_from="2026-01-01",
        valid_to=None,
        version="1.0.0",
    ),
    SystemBehaviorClaim(
        system_claim_id="SYS-EVID-001",
        description="Unsupported claims are transformed to UNKNOWN fail-closed",
        scope="response_generation",
        enforced_by=["trust_evidence_layer/claims.py", "trust_evidence_layer/gate.py"],
        evidence=["test_fail_closed.py", "test_hallucination_events_and_metrics.py"],
        valid_from="2026-01-01",
        valid_to=None,
        version="1.0.0",
    ),
    SystemBehaviorClaim(
        system_claim_id="SYS-AUD-001",
        description="Audit pack integrity validates trace and payload hashes",
        scope="audit",
        enforced_by=["trust_evidence_layer/audit_pack.py"],
        evidence=["test_audit_pack_hash_mismatch.py", "test_audit_pack_trace_mismatch.py"],
        valid_from="2026-01-01",
        valid_to=None,
        version="1.0.0",
    ),
]


def get_active_system_claims(at_date: date | None = None) -> list[SystemBehaviorClaim]:
    now = at_date or date.today()
    active: list[SystemBehaviorClaim] = []
    for claim in _SYSTEM_BEHAVIOR_CLAIMS:
        start = date.fromisoformat(claim.valid_from)
        end = date.fromisoformat(claim.valid_to) if claim.valid_to else None
        if now >= start and (end is None or now <= end):
            active.append(claim)
    return active


def as_dicts(claims: list[SystemBehaviorClaim]) -> list[dict[str, Any]]:
    return [
        {
            "system_claim_id": c.system_claim_id,
            "description": c.description,
            "scope": c.scope,
            "enforced_by": c.enforced_by,
            "evidence": c.evidence,
            "valid_from": c.valid_from,
            "valid_to": c.valid_to,
            "version": c.version,
        }
        for c in claims
    ]


def match_system_claim(claim_text: str, active_claims: list[SystemBehaviorClaim]) -> SystemBehaviorClaim | None:
    lowered = claim_text.lower()
    for claim in active_claims:
        desc = claim.description.lower()
        if lowered in desc or desc in lowered:
            return claim
        tokens = [t for t in desc.split() if len(t) > 4]
        if tokens and sum(1 for t in tokens if t in lowered) >= 3:
            return claim
    return None
