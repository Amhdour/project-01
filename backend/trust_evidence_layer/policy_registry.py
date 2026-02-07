from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from typing import Any


@dataclass(frozen=True)
class PolicyDefinition:
    policy_id: str
    description: str
    scope: str
    enforced_by: list[str]
    acceptance_tests: list[str]
    version: str


_POLICIES: dict[str, PolicyDefinition] = {
    "fail_closed_default": PolicyDefinition(
        policy_id="fail_closed_default",
        description="Unsupported claims are transformed to UNKNOWN or REFUSED.",
        scope="enforcement",
        enforced_by=["trust_evidence_layer/claims.py", "trust_evidence_layer/gate.py"],
        acceptance_tests=["test_fail_closed.py"],
        version="2.0.0",
    ),
    "factual_evidence_trust": PolicyDefinition(
        policy_id="factual_evidence_trust",
        description="Factual claims require trusted evidence coverage.",
        scope="evidence",
        enforced_by=["trust_evidence_layer/claims.py"],
        acceptance_tests=["test_evidence_trust_rules.py"],
        version="2.0.0",
    ),
    "streaming_partials_blocked": PolicyDefinition(
        policy_id="streaming_partials_blocked",
        description="Streaming partials are blocked at trust boundary.",
        scope="boundary",
        enforced_by=["trust_evidence_layer/boundary.py"],
        acceptance_tests=["test_gate_bypass_canary.py"],
        version="2.0.0",
    ),
    "jurisdiction_compliance": PolicyDefinition(
        policy_id="jurisdiction_compliance",
        description="Disallowed-jurisdiction evidence cannot support claims.",
        scope="sovereignty",
        enforced_by=["trust_evidence_layer/gate.py"],
        acceptance_tests=["test_jurisdiction_violation_refusal.py"],
        version="1.0.0",
    ),
    "pii_redaction": PolicyDefinition(
        policy_id="pii_redaction",
        description="PII is redacted from user-facing and narrative artifacts.",
        scope="privacy",
        enforced_by=["trust_evidence_layer/redaction.py", "trust_evidence_layer/audit_pack.py"],
        acceptance_tests=["test_pii_detection_and_redaction.py"],
        version="1.0.0",
    ),
}

_POLICY_VERSION_CHANGE_LOG: list[dict[str, Any]] = [
    {
        "policy_id": "fail_closed_default",
        "from_version": "1.1.0",
        "to_version": "2.0.0",
        "changed_at": "2026-02-01T00:00:00+00:00",
        "reason": "Added regulator-grade refusal semantics.",
    },
    {
        "policy_id": "factual_evidence_trust",
        "from_version": "1.1.0",
        "to_version": "2.0.0",
        "changed_at": "2026-02-01T00:00:00+00:00",
        "reason": "Aligned with updated governance trace model.",
    },
]


def get_policy_definitions() -> dict[str, PolicyDefinition]:
    return dict(_POLICIES)


def get_policy_versions() -> dict[str, str]:
    return {policy_id: p.version for policy_id, p in _POLICIES.items()}


def get_policy_version_change_log() -> list[dict[str, Any]]:
    return list(_POLICY_VERSION_CHANGE_LOG)


def evaluate_policy(
    policy_id: str,
    *,
    passed: bool,
    details: str,
) -> dict[str, Any]:
    definition = _POLICIES[policy_id]
    return {
        "policy_id": definition.policy_id,
        "description": definition.description,
        "scope": definition.scope,
        "version": definition.version,
        "enforced_by": definition.enforced_by,
        "acceptance_tests": definition.acceptance_tests,
        "passed": passed,
        "details": details,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
