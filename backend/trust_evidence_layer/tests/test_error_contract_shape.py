from trust_evidence_layer.gate import TrustEvidenceGate


def test_error_context_still_returns_exact_contract_shape() -> None:
    gate = TrustEvidenceGate()
    payload = gate.gate_response(
        draft_answer_text="Request failed: upstream timeout",
        retrieved_evidence=[],
        context={
            "chat_session_id": "s8",
            "message_id": None,
            "failure_modes": ["endpoint_error"],
        },
    ).to_ordered_dict()

    assert list(payload.keys()) == [
        "contract_version",
        "decision",
        "answer",
        "citations",
        "attribution",
        "audit_pack_ref",
        "policy_trace",
        "failure_mode",
        "answer_text",
        "evidence_bundle_user",
        "decision_record",
        "trace_id",
    ]
    assert "endpoint_error" in payload["decision_record"]["failure_modes"]
    assert payload["evidence_bundle_user"]["sources"] == []
    assert payload["evidence_bundle_user"]["citations"] == []



def test_contract_version_and_decision_fields_present() -> None:
    gate = TrustEvidenceGate()
    payload = gate.gate_response(draft_answer_text="UNKNOWN: no supporting evidence found.", retrieved_evidence=[], context={}).to_ordered_dict()
    assert payload["contract_version"] == "1.0"
    assert payload["decision"] == "UNKNOWN"
