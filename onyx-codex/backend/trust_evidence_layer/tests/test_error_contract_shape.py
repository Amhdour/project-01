from trust_evidence_layer.gate import TrustEvidenceGate


def test_error_context_still_returns_exact_contract_shape() -> None:
    gate = TrustEvidenceGate()
    payload = gate.gate_response(
        draft_answer_text="Request failed: upstream timeout",
        retrieved_evidence=[],
        context={
            "chat_session_id": "s8",
            "message_id": None,
            "failure_modes": ["endpoint_error"],
        },
    ).to_ordered_dict()

    assert list(payload.keys()) == [
        "answer_text",
        "evidence_bundle_user",
        "decision_record",
        "trace_id",
    ]
    assert "endpoint_error" in payload["decision_record"]["failure_modes"]
    assert payload["evidence_bundle_user"]["sources"] == []
    assert payload["evidence_bundle_user"]["citations"] == []
