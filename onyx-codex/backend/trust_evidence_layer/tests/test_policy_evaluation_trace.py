from trust_evidence_layer.gate import TrustEvidenceGate


def test_policy_evaluation_trace() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="A claim without evidence",
        retrieved_evidence=[],
        context={"chat_session_id": "pol1", "message_id": 1},
    )

    checks = response.decision_record.policy_checks
    assert checks
    assert all("policy_id" in c and "version" in c and "passed" in c for c in checks)
