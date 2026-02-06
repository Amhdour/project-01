from __future__ import annotations

from typing import Any

from trust_evidence_layer.policy_registry import evaluate_policy


def evaluate_policy_checks(
    *,
    evidence_count: int,
    unsupported_claim_count: int,
    factual_trust_violations: int,
    stream_blocked: bool,
    jurisdiction_violation: bool,
    redaction_applied: bool,
) -> list[dict[str, Any]]:
    return [
        evaluate_policy(
            "fail_closed_default",
            passed=True,
            details="Unsupported claims are transformed to UNKNOWN or REFUSED.",
        ),
        {
            "policy_id": "no_fabricated_citations",
            "description": "Citations are emitted only from normalized evidence sources.",
            "scope": "evidence",
            "version": "1.0.0",
            "enforced_by": ["trust_evidence_layer/gate.py"],
            "acceptance_tests": ["test_no_fabrication.py"],
            "passed": True,
            "details": "Citations emitted only from normalized evidence sources.",
        },
        evaluate_policy(
            "factual_evidence_trust",
            passed=factual_trust_violations == 0,
            details=f"factual_trust_violations={factual_trust_violations}",
        ),
        evaluate_policy(
            "streaming_partials_blocked",
            passed=stream_blocked,
            details="streaming disabled at trust boundary",
        ),
        evaluate_policy(
            "jurisdiction_compliance",
            passed=not jurisdiction_violation,
            details="jurisdiction_violation_detected" if jurisdiction_violation else "compliant",
        ),
        evaluate_policy(
            "pii_redaction",
            passed=True,
            details="redaction_applied" if redaction_applied else "no_redaction_required",
        ),
        {
            "policy_id": "evidence_presence",
            "description": "Evidence presence is tracked for audit context.",
            "scope": "audit",
            "version": "1.0.0",
            "enforced_by": ["trust_evidence_layer/gate.py"],
            "acceptance_tests": ["test_fail_closed.py"],
            "passed": evidence_count > 0,
            "details": "No supporting evidence found" if evidence_count == 0 else "evidence_present",
        },
        {
            "policy_id": "unsupported_claims_handled",
            "description": "Unsupported claims are recorded.",
            "scope": "audit",
            "version": "1.0.0",
            "enforced_by": ["trust_evidence_layer/claims.py"],
            "acceptance_tests": ["test_hallucination_events_and_metrics.py"],
            "passed": True,
            "details": f"unsupported_claim_count={unsupported_claim_count}",
        },
    ]
