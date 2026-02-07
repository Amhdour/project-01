from __future__ import annotations

import json
from dataclasses import asdict
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceSource:
    id: str
    title: str | None
    uri_or_path: str | None
    snippet: str
    offsets: dict[str, int] | None
    hash: str
    trust_level: str
    origin: str
    confidence_weight: float
    jurisdiction: str
    data_classification: str
    allowed_scopes: list[str]


@dataclass(frozen=True)
class EvidenceBundleUser:
    sources: list[EvidenceSource]
    citations: list[dict[str, Any]]
    retrieval_metadata: dict[str, Any]


@dataclass(frozen=True)
class DecisionRecord:
    claims: list[dict[str, Any]]
    claim_graph: list[dict[str, str]]
    system_claim_references: list[dict[str, str]]
    evidence_links: list[dict[str, Any]]
    policy_checks: list[dict[str, Any]]
    hallucination_events: list[dict[str, Any]]
    threat_signals: list[dict[str, Any]]
    incidents: list[dict[str, Any]]
    risk_references: list[str]
    redaction_events: list[dict[str, Any]]
    replay_metadata: dict[str, Any]
    metrics: dict[str, Any]
    failure_modes: list[str]
    timestamps: dict[str, str]
    retention: dict[str, Any]


@dataclass(frozen=True)
class TrustEvidenceResponse:
    answer_text: str
    evidence_bundle_user: EvidenceBundleUser
    decision_record: DecisionRecord
    trace_id: str

    def to_ordered_dict(self) -> dict[str, Any]:
        return {
            "answer_text": self.answer_text,
            "evidence_bundle_user": {
                "sources": [asdict(s) for s in self.evidence_bundle_user.sources],
                "citations": self.evidence_bundle_user.citations,
                "retrieval_metadata": self.evidence_bundle_user.retrieval_metadata,
            },
            "decision_record": {
                "claims": self.decision_record.claims,
                "claim_graph": self.decision_record.claim_graph,
                "system_claim_references": self.decision_record.system_claim_references,
                "evidence_links": self.decision_record.evidence_links,
                "policy_checks": self.decision_record.policy_checks,
                "hallucination_events": self.decision_record.hallucination_events,
                "threat_signals": self.decision_record.threat_signals,
                "incidents": self.decision_record.incidents,
                "risk_references": self.decision_record.risk_references,
                "redaction_events": self.decision_record.redaction_events,
                "replay_metadata": self.decision_record.replay_metadata,
                "metrics": self.decision_record.metrics,
                "failure_modes": self.decision_record.failure_modes,
                "timestamps": self.decision_record.timestamps,
                "retention": self.decision_record.retention,
            },
            "trace_id": self.trace_id,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_ordered_dict(), ensure_ascii=False, sort_keys=False)
