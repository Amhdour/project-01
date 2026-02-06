from __future__ import annotations

from typing import Any

from trust_evidence_layer.gate import assert_contract_shape


class TrustGateBypassError(RuntimeError):
    pass


def assert_no_bypass_inputs(host_context: dict[str, Any], context: dict[str, Any]) -> None:
    if host_context.get("raw_model_output") is not None:
        raise TrustGateBypassError("TRUST_GATE_BYPASS_ATTEMPT")
    if context.get("stream_requested"):
        raise TrustGateBypassError("TRUST_GATE_BYPASS_ATTEMPT")


def assert_no_raw_output(payload: dict[str, Any]) -> None:
    assert_contract_shape(payload)
