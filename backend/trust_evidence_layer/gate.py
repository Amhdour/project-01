from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from datetime import timezone
from datetime import timedelta
from typing import Any

from trust_evidence_layer.claims import ClaimType
from trust_evidence_layer.claims import VerificationStatus
from trust_evidence_layer.claims import enforce_claims
from trust_evidence_layer.evidence import normalize_raw_evidence
from trust_evidence_layer.incidents import classify_incidents
from trust_evidence_layer.kill_switch import current_kill_switch_state
from trust_evidence_layer.kill_switch import should_halt
from trust_evidence_layer.policies import evaluate_policy_checks
from trust_evidence_layer.redaction import redact_text
from trust_evidence_layer.registry import get_default_store
from trust_evidence_layer.registry import get_policy_change_log
from trust_evidence_layer.registry import get_policy_versions_map
from trust_evidence_layer.registry import get_risk_registry
from trust_evidence_layer.registry import get_system_behavior_claims
from trust_evidence_layer.registry import get_trusted_tools
from trust_evidence_layer.replay import TRUST_LAYER_VERSION
from trust_evidence_layer.replay import build_replay_inputs
from trust_evidence_layer.risk_registry import bind_applicable_risks
from trust_evidence_layer.sovereignty import enforce_jurisdiction
from trust_evidence_layer.storage.legal_hold_store import LegalHoldStore
from trust_evidence_layer.threats import apply_threat_containment
from trust_evidence_layer.threats import classify_threat_signals
from trust_evidence_layer.trace import generate_trace_id
from trust_evidence_layer.types import DecisionRecord
from trust_evidence_layer.types import EvidenceBundleUser
from trust_evidence_layer.types import TrustEvidenceResponse

CONTRACT_KEYS = ["contract_version", "decision", "answer", "citations", "attribution", "audit_pack_ref", "policy_trace", "failure_mode", "answer_text", "evidence_bundle_user", "decision_record", "trace_id"]




def _has_missing_critical_provenance(raw_evidence: list[dict[str, Any]]) -> tuple[bool, int]:
    missing_count = 0
    for item in raw_evidence:
        prov = item.get("provenance") if isinstance(item, dict) else None
        if not isinstance(prov, dict):
            continue
        missing_fields = prov.get("missing_fields")
        if isinstance(missing_fields, list) and missing_fields:
            missing_count += 1
    return missing_count > 0, missing_count

def assert_contract_shape(payload: dict[str, Any]) -> None:
    if list(payload.keys()) != CONTRACT_KEYS:
        raise RuntimeError("TRUST_GATE_BYPASS_ATTEMPT: invalid contract shape")


class TrustEvidenceGate:
    @staticmethod
    def _normalize_failure_modes(context: dict[str, Any]) -> list[str]:
        raw = context.get("failure_modes", [])
        if not isinstance(raw, list):
            return []
        return sorted({str(v) for v in raw if v is not None})

    @staticmethod
    def _retention_from_context(context: dict[str, Any]) -> dict[str, Any]:
        policy = str(context.get("retention_policy") or "30_DAYS")
        reason = str(context.get("retention_reason") or "AUDIT")
        legal_hold = bool(context.get("legal_hold", False))

        expiry_at = None
        if policy == "30_DAYS":
            expiry_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        elif policy == "90_DAYS":
            expiry_at = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()

        return {
            "retention_policy": policy,
            "retention_reason": reason,
            "legal_hold": legal_hold,
            "expiry_at": expiry_at,
        }

    def gate_response(
        self,
        draft_answer_text: str,
        retrieved_evidence: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> TrustEvidenceResponse:
        trace_id = generate_trace_id()
        now_iso = datetime.now(timezone.utc).isoformat()

        normalized_evidence = normalize_raw_evidence(
            retrieved_evidence,
            trusted_tools=get_trusted_tools(),
        )

        allowed_jurisdictions = context.get("allowed_jurisdictions")
        if not isinstance(allowed_jurisdictions, list) or not allowed_jurisdictions:
            allowed_jurisdictions = ["US", "EU", "UK", "CA", "UNKNOWN"]

        accepted_evidence, accepted_meta, rejected_meta, jurisdiction_violation = enforce_jurisdiction(
            evidence_sources=normalized_evidence,
            allowed_jurisdictions=allowed_jurisdictions,
            required_scope="response_generation",
        )

        threat_signals = classify_threat_signals(draft_answer_text, accepted_evidence)
        evidence_sources = apply_threat_containment(accepted_evidence, threat_signals)

        (
            enforced_answer,
            claim_records,
            evidence_links,
            claim_graph,
            failure_modes,
            hallucination_events,
            metrics,
            system_claim_refs,
        ) = enforce_claims(
            draft_answer_text=draft_answer_text,
            evidence_sources=evidence_sources,
            system_claims=get_system_behavior_claims(),
        )

        claim_types = sorted({c["claim_type"] for c in claim_records})
        domain = str(context.get("domain") or "general")
        halted, halt_reason = should_halt(domain=domain, claim_types=claim_types)

        contextual_failure_modes = self._normalize_failure_modes(context)
        failure_modes = sorted(set(failure_modes + contextual_failure_modes))

        missing_critical_provenance, missing_provenance_count = _has_missing_critical_provenance(
            retrieved_evidence
        )
        trust_mode_effective = str(context.get("trust_mode_effective") or "")
        if missing_critical_provenance and trust_mode_effective == "enforce":
            failure_modes.append("critical_provenance_missing")

        unsupported_count = metrics["num_claims_unsupported"]
        factual_violations = sum(
            1
            for claim in claim_records
            if claim["claim_type"] == ClaimType.FACTUAL
            and claim["verification_status"] != VerificationStatus.SUPPORTED
        )
        stream_blocked = not bool(context.get("stream_requested", False))

        redaction_events: list[dict[str, Any]] = []
        redacted_answer, answer_redactions = redact_text(enforced_answer)
        redaction_events.extend(answer_redactions)

        redacted_sources = []
        for src in evidence_sources:
            redacted_snippet, snippet_redactions = redact_text(src.snippet)
            if snippet_redactions:
                redaction_events.extend(snippet_redactions)
            redacted_sources.append(replace(src, snippet=redacted_snippet))
        evidence_sources = redacted_sources

        policy_checks = evaluate_policy_checks(
            evidence_count=len(evidence_sources),
            unsupported_claim_count=unsupported_count,
            factual_trust_violations=factual_violations,
            stream_blocked=stream_blocked,
            jurisdiction_violation=jurisdiction_violation,
            redaction_applied=bool(redaction_events),
        )

        citations = [
            {"citation_number": idx + 1, "source_id": source.id}
            for idx, source in enumerate(evidence_sources)
        ]

        refusal_reasons: list[str] = []
        if jurisdiction_violation:
            refusal_reasons.append("REFUSE: jurisdiction_violation_disallowed_evidence")
            failure_modes.append("jurisdiction_violation")

        if halted:
            refusal_reasons.append(f"REFUSE: kill_switch_active ({halt_reason})")
            failure_modes.append("kill_switch_active")

        if missing_critical_provenance and trust_mode_effective == "enforce":
            refusal_reasons.append("REFUSE: critical_provenance_missing")

        if refusal_reasons:
            final_answer = "\n".join(refusal_reasons)
        else:
            final_answer = redacted_answer
            if (
                not evidence_sources
                and unsupported_count > 0
                and not final_answer.strip().lower().startswith("unknown:")
            ):
                final_answer = "UNKNOWN: no supporting evidence found."

        retention = self._retention_from_context(context)
        replay_inputs = build_replay_inputs(draft_answer_text, retrieved_evidence)
        replay_metadata = {
            "policy_versions": get_policy_versions_map(),
            "policy_change_log": get_policy_change_log(),
            "trust_layer_version": TRUST_LAYER_VERSION,
            "replay_status": "available",
        }

        incidents = classify_incidents(
            trace_id=trace_id,
            failure_modes=sorted(set(failure_modes)),
            metrics=metrics,
            replay_consistent=True,
        )

        risk_references = bind_applicable_risks(
            threat_signals=threat_signals,
            failure_modes=failure_modes,
        )

        response = TrustEvidenceResponse(
            answer_text=final_answer,
            evidence_bundle_user=EvidenceBundleUser(
                sources=evidence_sources,
                citations=citations,
                retrieval_metadata={
                    "contract_version": "1.0",
                    "evidence_count": len(evidence_sources),
                    "missing_critical_provenance": missing_critical_provenance,
                    "missing_provenance_count": missing_provenance_count,
                    "jurisdiction_compliance": {
                        "allowed_jurisdictions": sorted({j.upper() for j in allowed_jurisdictions}),
                        "accepted_evidence": accepted_meta,
                        "rejected_evidence": rejected_meta,
                    },
                    "host_context": {
                        "chat_session_id": context.get("chat_session_id"),
                        "message_id": context.get("message_id"),
                        "origin": context.get("origin"),
                        "stream_requested": context.get("stream_requested"),
                        "request_path": context.get("request_path"),
                        "failure_modes": contextual_failure_modes,
                        "domain": domain,
                    },
                },
            ),
            decision_record=DecisionRecord(
                claims=claim_records,
                claim_graph=claim_graph,
                system_claim_references=system_claim_refs,
                evidence_links=evidence_links,
                policy_checks=policy_checks,
                hallucination_events=hallucination_events,
                threat_signals=threat_signals,
                incidents=incidents,
                risk_references=risk_references,
                redaction_events=redaction_events,
                replay_metadata=replay_metadata,
                metrics=metrics,
                failure_modes=sorted(set(failure_modes)),
                timestamps={"gated_at": now_iso},
                retention=retention,
            ),
            trace_id=trace_id,
        )

        payload = response.to_ordered_dict()
        assert_contract_shape(payload)

        get_default_store().store(
            trace_id=trace_id,
            response_payload=payload,
            raw_context_minimal={
                "request_metadata": context,
                "retrieved_evidence_count": len(retrieved_evidence),
                "kill_switch_state": current_kill_switch_state(),
            },
            replay_inputs=replay_inputs,
        )

        if retention.get("legal_hold"):
            LegalHoldStore().store_unredacted(
                trace_id=trace_id,
                unredacted_answer=enforced_answer,
                unredacted_evidence=retrieved_evidence,
                unredacted_narrative="",
            )

        return response
