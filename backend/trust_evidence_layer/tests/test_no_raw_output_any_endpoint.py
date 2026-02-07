from trust_evidence_layer.boundary import assert_no_raw_output


def test_no_raw_output_guarantee_rejects_non_contract_payload() -> None:
    try:
        assert_no_raw_output({"answer_text": "raw only"})
    except RuntimeError as e:
        assert "TRUST_GATE_BYPASS_ATTEMPT" in str(e)
    else:
        raise AssertionError("expected non-contract payload to be rejected")
