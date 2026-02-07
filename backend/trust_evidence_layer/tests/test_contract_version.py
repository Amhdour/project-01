from trust_evidence_layer.gate import TrustEvidenceGate


def test_contract_version_present_in_retrieval_metadata() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="Hello",
        retrieved_evidence=[],
        context={"chat_session_id": "s11", "message_id": 11},
    )

    assert response.evidence_bundle_user.retrieval_metadata["contract_version"] == "1.0"
