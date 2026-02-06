from trust_evidence_layer.gate import TrustEvidenceGate


def test_no_fabricated_citations_when_no_evidence() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="Water boils at 100C.",
        retrieved_evidence=[],
        context={"chat_session_id": "s3", "message_id": 3},
    )

    assert response.evidence_bundle_user.sources == []
    assert response.evidence_bundle_user.citations == []
