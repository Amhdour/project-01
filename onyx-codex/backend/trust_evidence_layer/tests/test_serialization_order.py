import json

from trust_evidence_layer.gate import TrustEvidenceGate


def test_serialization_preserves_top_level_key_order() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="The sky is blue.",
        retrieved_evidence=[{"id": "doc1", "snippet": "The sky is blue."}],
        context={"chat_session_id": "s9", "message_id": 9},
    )

    parsed = json.loads(response.to_json())
    assert list(parsed.keys()) == [
        "answer_text",
        "evidence_bundle_user",
        "decision_record",
        "trace_id",
    ]
