import pytest

from trust_evidence_layer.boundary import TrustGateBypassError
from trust_evidence_layer.boundary import assert_no_bypass_inputs


def test_gate_bypass_canary_raises_runtime_error() -> None:
    with pytest.raises(TrustGateBypassError, match="TRUST_GATE_BYPASS_ATTEMPT"):
        assert_no_bypass_inputs(
            host_context={"raw_model_output": "unsafe"},
            context={"stream_requested": False},
        )
