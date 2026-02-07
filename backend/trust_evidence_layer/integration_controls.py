from __future__ import annotations

import os
from typing import Any
from typing import Callable
from typing import Literal

TrustMode = Literal["off", "observe", "enforce"]

STREAMING_ENFORCEMENT_BYPASS_MODE = "streaming_enforcement_bypassed"


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def get_trust_mode() -> TrustMode:
    enabled = _env_bool("TRUST_EVIDENCE_ENABLED", default=False)
    raw_mode = (os.environ.get("TRUST_EVIDENCE_MODE") or "off").strip().lower()
    if not enabled:
        return "off"
    if raw_mode in {"observe", "enforce"}:
        return raw_mode  # type: ignore[return-value]
    return "off"


def should_enforce_on_streaming() -> bool:
    return _env_bool("TRUST_EVIDENCE_ENFORCE_ON_STREAMING", default=False)


def _is_streaming_requested(host_context: dict[str, Any]) -> bool:
    req = host_context.get("chat_message_req")
    return bool(getattr(req, "stream", False))


def to_enforced_contract(gated_payload: dict[str, Any]) -> dict[str, Any]:
    trace_id = str(gated_payload.get("trace_id") or "")
    return {
        "final_answer": gated_payload.get("answer", gated_payload.get("answer_text", "")),
        "citations": gated_payload.get("citations", []),
        "trust": {
            "contract_version": gated_payload.get("contract_version", "1.0"),
            "decision": gated_payload.get("decision", "UNKNOWN"),
            "policy_trace": gated_payload.get("policy_trace", []),
            "failure_mode": gated_payload.get("failure_mode", "none"),
        },
        "audit_pack_id": trace_id,
    }


def maybe_apply_trust(
    *,
    host_context: dict[str, Any],
    original_response: Any,
    gate_fn: Callable[[dict[str, Any], dict[str, Any] | None], dict[str, Any]],
    tenant_id: str | None,
    request_path: str | None,
) -> Any:
    mode = get_trust_mode()
    if mode == "off":
        return original_response

    stream_requested = _is_streaming_requested(host_context)
    enforce_requested = mode == "enforce"
    enforce_streaming_allowed = should_enforce_on_streaming()

    downgrade_to_observe_for_stream = (
        stream_requested and enforce_requested and not enforce_streaming_allowed
    )

    effective_mode = "observe" if downgrade_to_observe_for_stream else mode
    context_override: dict[str, Any] = {
        "tenant_id": tenant_id,
        "request_path": request_path,
        "trust_mode_effective": effective_mode,
    }
    if downgrade_to_observe_for_stream:
        context_override["failure_modes"] = [STREAMING_ENFORCEMENT_BYPASS_MODE]
        context_override["trust_enforcement_bypassed_reason"] = (
            "streaming_enforce_disabled"
        )

    gated_payload = gate_fn(host_context, context_override)

    if mode == "observe" or downgrade_to_observe_for_stream:
        return original_response

    return to_enforced_contract(gated_payload)
