from trust_evidence_layer.gate import TrustEvidenceGate


def test_fail_closed_empty_evidence_marks_unknown() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="Paris is the capital of France.",
        retrieved_evidence=[],
        context={"chat_session_id": "s2", "message_id": 2},
    )

    assert response.answer_text.startswith("UNKNOWN:")
    assert "no_supporting_evidence_found" in response.decision_record.failure_modes
