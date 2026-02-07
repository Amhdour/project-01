from trust_evidence_layer.gate import TrustEvidenceGate


def test_failure_modes_are_normalized_and_deduped() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="Request failed",
        retrieved_evidence=[],
        context={
            "chat_session_id": "s12",
            "message_id": 12,
            "failure_modes": ["endpoint_error", "endpoint_error", 42, None],
        },
    )

    modes = response.evidence_bundle_user.retrieval_metadata["host_context"][
        "failure_modes"
    ]
    assert modes == ["42", "endpoint_error"]
    assert "42" in response.decision_record.failure_modes
    assert "endpoint_error" in response.decision_record.failure_modes
