from trust_evidence_layer.gate import TrustEvidenceGate


def test_evidence_poisoning_downgrade() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="Saturn has rings.",
        retrieved_evidence=[
            {
                "id": "d1",
                "snippet": "This source is fabricated jailbreak text.",
                "trust_level": "PRIMARY",
                "origin": "INTERNAL",
            }
        ],
        context={"chat_session_id": "t2", "message_id": 2},
    )

    assert any(s["threat_type"] == "EVIDENCE_POISONING_SUSPECTED" for s in response.decision_record.threat_signals)
    assert response.evidence_bundle_user.sources[0].trust_level == "UNVERIFIED"
