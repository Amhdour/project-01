from trust_evidence_layer.gate import TrustEvidenceGate


def test_factual_claim_requires_primary_or_two_secondary() -> None:
    gate = TrustEvidenceGate()

    one_secondary = gate.gate_response(
        draft_answer_text="Saturn has rings.",
        retrieved_evidence=[
            {"id": "s1", "snippet": "Saturn has rings.", "trust_level": "SECONDARY", "origin": "THIRD_PARTY"}
        ],
        context={"chat_session_id": "tr1", "message_id": 3},
    )
    assert one_secondary.answer_text.startswith("UNKNOWN:")

    two_secondary = gate.gate_response(
        draft_answer_text="Saturn has rings.",
        retrieved_evidence=[
            {"id": "s1", "snippet": "Saturn has rings.", "trust_level": "SECONDARY", "origin": "THIRD_PARTY"},
            {"id": "s2", "snippet": "Astronomy text: Saturn has rings.", "trust_level": "SECONDARY", "origin": "THIRD_PARTY"},
        ],
        context={"chat_session_id": "tr2", "message_id": 4},
    )
    assert not two_secondary.answer_text.startswith("UNKNOWN:")


def test_untrusted_tool_evidence_cannot_support_factual() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="Mercury is the smallest planet.",
        retrieved_evidence=[
            {
                "id": "tool1",
                "snippet": "Mercury is the smallest planet.",
                "origin": "TOOL",
                "tool_name": "untrusted_tool",
            }
        ],
        context={"chat_session_id": "tr3", "message_id": 5},
    )

    assert response.answer_text.startswith("UNKNOWN:")
    assert "TOOL_UNTRUSTED" in response.decision_record.failure_modes
