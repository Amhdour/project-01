from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResidualRisk:
    risk_id: str
    description: str
    mitigation: str
    accepted_by: str
    review_cycle: str
    status: str


_ACTIVE_RISKS: list[ResidualRisk] = [
    ResidualRisk(
        risk_id="RISK-001",
        description="Lexical heuristics may miss nuanced entailment.",
        mitigation="Fail-closed suppression and periodic rule review.",
        accepted_by="Chief Risk Officer",
        review_cycle="quarterly",
        status="accepted",
    ),
    ResidualRisk(
        risk_id="RISK-002",
        description="Threat classification is deterministic and may under-detect advanced attacks.",
        mitigation="Escalate suspicious traces and add model-based detector in roadmap.",
        accepted_by="Security Governance Board",
        review_cycle="monthly",
        status="accepted",
    ),
]


def get_active_risks() -> list[ResidualRisk]:
    return list(_ACTIVE_RISKS)


def as_dicts(risks: list[ResidualRisk]) -> list[dict[str, Any]]:
    return [
        {
            "risk_id": r.risk_id,
            "description": r.description,
            "mitigation": r.mitigation,
            "accepted_by": r.accepted_by,
            "review_cycle": r.review_cycle,
            "status": r.status,
        }
        for r in risks
    ]


def bind_applicable_risks(
    *,
    threat_signals: list[dict[str, Any]],
    failure_modes: list[str],
) -> list[str]:
    bound: set[str] = set()
    if any(m in {"unsupported_claim", "OUT_OF_SCOPE", "NO_EVIDENCE"} for m in failure_modes):
        bound.add("RISK-001")
    if threat_signals:
        bound.add("RISK-002")
    return sorted(bound)
