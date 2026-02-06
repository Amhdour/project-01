from trust_evidence_layer.gate import TrustEvidenceGate


def test_request_context_fields_passthrough_to_retrieval_metadata() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="A draft answer.",
        retrieved_evidence=[],
        context={
            "chat_session_id": "s10",
            "message_id": 10,
            "origin": "API",
            "stream_requested": True,
            "request_path": "/api/chat/send-chat-message",
            "failure_modes": ["endpoint_error"],
        },
    )

    host_context = response.evidence_bundle_user.retrieval_metadata["host_context"]
    assert host_context["origin"] == "API"
    assert host_context["stream_requested"] is True
    assert host_context["request_path"] == "/api/chat/send-chat-message"
    assert host_context["failure_modes"] == ["endpoint_error"]
