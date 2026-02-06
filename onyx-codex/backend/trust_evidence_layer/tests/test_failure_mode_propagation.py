from trust_evidence_layer.gate import TrustEvidenceGate


def test_context_failure_modes_propagate_to_decision_record() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="Request failed due to timeout.",
        retrieved_evidence=[],
        context={
            "chat_session_id": "s7",
            "message_id": 7,
            "failure_modes": ["endpoint_error", "timeout"],
        },
    )

    assert "endpoint_error" in response.decision_record.failure_modes
    assert "timeout" in response.decision_record.failure_modes
