from trust_evidence_layer.gate import TrustEvidenceGate


def test_jurisdiction_violation_refusal() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="Patient record indicates blood pressure trend.",
        retrieved_evidence=[
            {
                "id": "e1",
                "snippet": "Patient MRN-123456 has elevated blood pressure.",
                "trust_level": "PRIMARY",
                "origin": "INTERNAL",
                "jurisdiction": "EU",
                "allowed_scopes": ["response_generation"],
            }
        ],
        context={
            "chat_session_id": "j1",
            "message_id": 1,
            "allowed_jurisdictions": ["US"],
        },
    )

    assert response.answer_text.startswith("REFUSE:")
    assert "jurisdiction_violation" in response.decision_record.failure_modes
