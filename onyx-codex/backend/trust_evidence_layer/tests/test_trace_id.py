import uuid

from trust_evidence_layer.gate import TrustEvidenceGate


def test_trace_id_uuid() -> None:
    gate = TrustEvidenceGate()
    r1 = gate.gate_response(
        draft_answer_text="Hello there.",
        retrieved_evidence=[],
        context={"chat_session_id": "s4", "message_id": 4},
    )
    r2 = gate.gate_response(
        draft_answer_text="Hello there.",
        retrieved_evidence=[],
        context={"chat_session_id": "s5", "message_id": 5},
    )

    uuid.UUID(r1.trace_id)
    uuid.UUID(r2.trace_id)
    assert r1.trace_id != r2.trace_id
