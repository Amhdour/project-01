from trust_evidence_layer.gate import TrustEvidenceGate


def test_policy_versioning_audit() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="Some claim",
        retrieved_evidence=[],
        context={"chat_session_id": "pol2", "message_id": 2},
    )

    replay_meta = response.decision_record.replay_metadata
    assert "policy_versions" in replay_meta
    assert "policy_change_log" in replay_meta
    assert replay_meta["policy_change_log"]
