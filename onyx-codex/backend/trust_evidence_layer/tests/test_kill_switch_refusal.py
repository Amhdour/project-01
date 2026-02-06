from trust_evidence_layer.gate import TrustEvidenceGate
from trust_evidence_layer.kill_switch import activate_kill_switch
from trust_evidence_layer.kill_switch import clear_kill_switch


def test_kill_switch_refusal() -> None:
    activate_kill_switch("SYSTEM_HALT", reason="manual safety stop")
    try:
        gate = TrustEvidenceGate()
        response = gate.gate_response(
            draft_answer_text="Any answer",
            retrieved_evidence=[],
            context={"chat_session_id": "k1", "message_id": 1},
        )
        assert response.answer_text.startswith("REFUSE: kill_switch_active")
    finally:
        clear_kill_switch()
