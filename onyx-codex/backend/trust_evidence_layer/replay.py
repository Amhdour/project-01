from __future__ import annotations

from typing import Any

from trust_evidence_layer.claims import enforce_claims
from trust_evidence_layer.evidence import normalize_raw_evidence
from trust_evidence_layer.registry import get_policy_versions_map
from trust_evidence_layer.registry import get_system_behavior_claims
from trust_evidence_layer.registry import get_trusted_tools
from trust_evidence_layer.storage.file_store import TraceFileStore


TRUST_LAYER_VERSION = "1.2.0"


def build_replay_inputs(
    draft_answer_text: str,
    retrieved_evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    evidence = normalize_raw_evidence(retrieved_evidence, trusted_tools=get_trusted_tools())
    return {
        "sanitized_prompt": " ".join(draft_answer_text.split())[:500],
        "retrieved_evidence": [
            {
                "id": src.id,
                "snippet": src.snippet,
                "hash": src.hash,
                "trust_level": src.trust_level,
                "origin": src.origin,
                "jurisdiction": src.jurisdiction,
                "data_classification": src.data_classification,
                "allowed_scopes": src.allowed_scopes,
            }
            for src in evidence
        ],
        "policy_versions": get_policy_versions_map(),
        "trust_layer_version": TRUST_LAYER_VERSION,
    }


def replay(trace_id: str, store: TraceFileStore) -> dict[str, Any]:
    record = store.load(trace_id)
    replay_inputs = record.get("replay_inputs", {})
    evidence_inputs = replay_inputs.get("retrieved_evidence", [])
    prompt = replay_inputs.get("sanitized_prompt", "")

    normalized = normalize_raw_evidence(evidence_inputs, trusted_tools=get_trusted_tools())
    system_claims = get_system_behavior_claims()

    (
        _enforced_answer,
        claim_records,
        _evidence_links,
        _claim_graph,
        failure_modes,
        _hallucination_events,
        metrics,
        _system_refs,
    ) = enforce_claims(
        draft_answer_text=prompt,
        evidence_sources=normalized,
        system_claims=system_claims,
    )

    original = record.get("response", {}).get("decision_record", {})
    equivalent = (
        original.get("claims") == claim_records
        and original.get("failure_modes") == failure_modes
        and original.get("metrics") == metrics
    )

    return {
        "trace_id": trace_id,
        "equivalent": equivalent,
        "replayed_claims": claim_records,
        "replayed_failure_modes": failure_modes,
        "replayed_metrics": metrics,
        "policy_versions": replay_inputs.get("policy_versions", {}),
        "trust_layer_version": replay_inputs.get("trust_layer_version"),
    }
