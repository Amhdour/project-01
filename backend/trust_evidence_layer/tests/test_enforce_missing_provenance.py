from trust_evidence_layer.gate import TrustEvidenceGate


def test_enforce_mode_refuses_when_critical_provenance_missing() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="Some answer",
        retrieved_evidence=[
            {
                "id": "derived:abc",
                "snippet": "evidence snippet",
                "origin": "INTERNAL",
                "provenance": {"missing_fields": ["connector_id", "jurisdiction"]},
            }
        ],
        context={"trust_mode_effective": "enforce"},
    )

    assert response.answer_text.startswith("REFUSE: critical_provenance_missing")
    assert "critical_provenance_missing" in response.decision_record.failure_modes
    assert (
        response.evidence_bundle_user.retrieval_metadata["missing_critical_provenance"]
        is True
    )
