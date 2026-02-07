from trust_evidence_layer.gate import TrustEvidenceGate
from trust_evidence_layer.registry import get_default_store
from trust_evidence_layer.replay import replay


def test_replay_decision_equivalence() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="Paris is the capital of France.",
        retrieved_evidence=[],
        context={"chat_session_id": "r1", "message_id": 1},
    )

    replay_result = replay(response.trace_id, get_default_store())
    assert replay_result["equivalent"] is True
