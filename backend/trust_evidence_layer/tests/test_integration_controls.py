from __future__ import annotations

from trust_evidence_layer.integration_controls import maybe_apply_trust


def test_off_mode_returns_original_and_skips_gate(monkeypatch) -> None:
    monkeypatch.setenv("TRUST_EVIDENCE_ENABLED", "false")
    monkeypatch.setenv("TRUST_EVIDENCE_MODE", "enforce")

    called = {"gate": False}

    def gate_fn(host_context, context_override):
        called["gate"] = True
        return {"trace_id": "t1"}

    original = {"answer": "host"}
    out = maybe_apply_trust(
        host_context={"chat_result": object()},
        original_response=original,
        gate_fn=gate_fn,
        tenant_id="tenant-1",
        request_path="/api/chat/send-chat-message",
    )
    assert out == original
    assert called["gate"] is False


def test_observe_mode_returns_original_and_calls_gate(monkeypatch) -> None:
    monkeypatch.setenv("TRUST_EVIDENCE_ENABLED", "true")
    monkeypatch.setenv("TRUST_EVIDENCE_MODE", "observe")

    calls: dict[str, object] = {}

    def gate_fn(host_context, context_override):
        calls["context"] = context_override
        return {
            "trace_id": "audit-123",
            "contract_version": "1.0",
            "decision": "ALLOW",
            "policy_trace": [],
            "failure_mode": "none",
            "answer": "gated",
            "citations": [],
        }

    original = {"answer": "host"}
    out = maybe_apply_trust(
        host_context={"chat_result": object()},
        original_response=original,
        gate_fn=gate_fn,
        tenant_id="tenant-2",
        request_path="/api/chat/send-chat-message",
    )
    assert out == original
    assert calls["context"] == {
        "tenant_id": "tenant-2",
        "request_path": "/api/chat/send-chat-message",
    }


def test_enforce_mode_returns_four_key_contract(monkeypatch) -> None:
    monkeypatch.setenv("TRUST_EVIDENCE_ENABLED", "true")
    monkeypatch.setenv("TRUST_EVIDENCE_MODE", "enforce")

    def gate_fn(host_context, context_override):
        return {
            "trace_id": "audit-999",
            "contract_version": "1.0",
            "decision": "ALLOW",
            "policy_trace": [{"policy_id": "p1", "passed": True, "version": "1.0"}],
            "failure_mode": "none",
            "answer": "safe",
            "citations": [{"citation_number": 1, "source_id": "doc-1"}],
        }

    out = maybe_apply_trust(
        host_context={"chat_result": object()},
        original_response={"answer": "host"},
        gate_fn=gate_fn,
        tenant_id="tenant-3",
        request_path="/api/chat/send-chat-message",
    )
    assert set(out.keys()) == {"final_answer", "citations", "trust", "audit_pack_id"}
    assert out["audit_pack_id"] == "audit-999"
    assert out["trust"]["decision"] == "ALLOW"
