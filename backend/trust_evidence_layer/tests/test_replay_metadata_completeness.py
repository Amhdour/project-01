from trust_evidence_layer.gate import TrustEvidenceGate


def test_replay_metadata_completeness() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="Water boils at 100C.",
        retrieved_evidence=[],
        context={"chat_session_id": "r2", "message_id": 2},
    )

    replay_meta = response.decision_record.replay_metadata
    assert "policy_versions" in replay_meta
    assert "trust_layer_version" in replay_meta
    assert replay_meta["replay_status"] == "available"
