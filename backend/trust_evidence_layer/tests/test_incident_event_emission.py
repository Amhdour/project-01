from trust_evidence_layer.gate import TrustEvidenceGate


def test_incident_event_emission() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="A factual claim with no evidence.",
        retrieved_evidence=[],
        context={"chat_session_id": "i1", "message_id": 1},
    )

    assert response.decision_record.incidents
    assert {e["incident_type"] for e in response.decision_record.incidents} & {
        "EVIDENCE_FAILURE",
        "HALLUCINATION_SPIKE",
    }
