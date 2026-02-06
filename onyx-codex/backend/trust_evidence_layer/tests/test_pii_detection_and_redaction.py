from trust_evidence_layer.gate import TrustEvidenceGate


def test_pii_detection_and_redaction() -> None:
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="Contact john.doe@example.com or +1 555-123-4567 MRN-123456.",
        retrieved_evidence=[
            {
                "id": "p1",
                "snippet": "Email john.doe@example.com and SSN 123-45-6789",
                "trust_level": "PRIMARY",
                "origin": "INTERNAL",
            }
        ],
        context={"chat_session_id": "p1", "message_id": 1},
    )

    assert "[REDACTED_EMAIL]" in response.answer_text
    assert "[REDACTED_PHONE]" in response.answer_text or "[REDACTED_MEDICAL_RECORD]" in response.answer_text
    assert response.decision_record.redaction_events
    assert "[REDACTED_EMAIL]" in response.evidence_bundle_user.sources[0].snippet
