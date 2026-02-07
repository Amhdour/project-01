from trust_evidence_layer.gate import TrustEvidenceGate


def test_hallucination_events_and_metrics_recorded() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="Paris is the capital of France.",
        retrieved_evidence=[],
        context={"chat_session_id": "hm1", "message_id": 2},
    )

    assert response.decision_record.metrics["num_claims_total"] == 1
    assert response.decision_record.metrics["num_claims_unsupported"] == 1
    assert response.decision_record.metrics["pct_suppressed"] == 1.0
    assert response.decision_record.hallucination_events
    assert response.decision_record.hallucination_events[0]["event_type"] == "HALLUCINATION_SUPPRESSED"
