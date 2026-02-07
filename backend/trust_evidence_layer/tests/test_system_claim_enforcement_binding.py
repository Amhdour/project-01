from trust_evidence_layer.gate import TrustEvidenceGate


def test_system_claim_enforcement_binding() -> None:
    gate = TrustEvidenceGate()

    backed = gate.gate_response(
        draft_answer_text="System enforces strict four-key response contract at boundary.",
        retrieved_evidence=[],
        context={"chat_session_id": "sc1", "message_id": 1},
    )
    assert backed.decision_record.system_claim_references
    assert not backed.answer_text.startswith("UNKNOWN:")

    unknown = gate.gate_response(
        draft_answer_text="System has quantum safe attestation guarantees.",
        retrieved_evidence=[],
        context={"chat_session_id": "sc2", "message_id": 2},
    )
    assert unknown.answer_text.startswith("UNKNOWN:")
