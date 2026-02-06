from trust_evidence_layer.gate import TrustEvidenceGate


def test_schema_contract() -> None:
    gate = TrustEvidenceGate()
    result = gate.gate_response(
        draft_answer_text="The sky is blue.",
        retrieved_evidence=[
            {
                "id": "doc1",
                "title": "Weather",
                "uri": "https://example.com/weather",
                "snippet": "The sky is blue in clear daytime conditions.",
            }
        ],
        context={"chat_session_id": "s1", "message_id": 1},
    ).to_ordered_dict()

    assert list(result.keys()) == [
        "answer_text",
        "evidence_bundle_user",
        "decision_record",
        "trace_id",
    ]
    assert "sources" in result["evidence_bundle_user"]
    assert "citations" in result["evidence_bundle_user"]
    assert "retrieval_metadata" in result["evidence_bundle_user"]
    assert "claims" in result["decision_record"]
    assert "evidence_links" in result["decision_record"]
    assert "policy_checks" in result["decision_record"]
    assert "claim_graph" in result["decision_record"]
    assert "replay_metadata" in result["decision_record"]
    assert "redaction_events" in result["decision_record"]
    assert "risk_references" in result["decision_record"]
    assert "incidents" in result["decision_record"]
    assert "threat_signals" in result["decision_record"]
    assert "system_claim_references" in result["decision_record"]
    assert "hallucination_events" in result["decision_record"]
    assert "metrics" in result["decision_record"]
    assert "retention" in result["decision_record"]
    assert "failure_modes" in result["decision_record"]
    assert "timestamps" in result["decision_record"]
