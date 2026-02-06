from trust_evidence_layer.gate import TrustEvidenceGate


def test_claim_typing_and_derived_graph_chaining() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text=(
            "The policy says unsupported claims are transformed to UNKNOWN. "
            "The report likely suggests elevated latency. "
            "Therefore we should open an incident."
        ),
        retrieved_evidence=[
            {
                "id": "d1",
                "snippet": "The report suggests elevated latency and recommends escalation.",
                "origin": "INTERNAL",
                "trust_level": "PRIMARY",
            },
            {
                "id": "d2",
                "snippet": "Operational report indicates elevated latency during peak load.",
                "origin": "INTERNAL",
                "trust_level": "SECONDARY",
            },
        ],
        context={"chat_session_id": "cg1", "message_id": 1},
    )

    claims = response.decision_record.claims
    assert claims[0]["claim_type"] == "SYSTEM"
    assert claims[1]["claim_type"] == "INTERPRETIVE"
    assert claims[2]["claim_type"] == "DERIVED"
    assert any(edge["claim_id"] == claims[2]["claim_id"] for edge in response.decision_record.claim_graph)
