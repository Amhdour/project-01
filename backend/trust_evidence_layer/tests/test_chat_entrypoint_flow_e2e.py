from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from trust_evidence_layer.audit_pack import AuditPackExporter
from trust_evidence_layer.boundary import assert_no_bypass_inputs
from trust_evidence_layer.boundary import assert_no_raw_output
from trust_evidence_layer.gate import TrustEvidenceGate
from trust_evidence_layer.host.onyx_adapter import OnyxHostAdapter
from trust_evidence_layer.integration_controls import maybe_apply_trust
from trust_evidence_layer.storage.file_store import TraceFileStore
import trust_evidence_layer.registry as registry


def _host_context() -> dict:
    result = SimpleNamespace(
        answer="Host answer",
        top_documents=[
            SimpleNamespace(
                document_id="doc-1",
                semantic_identifier="Doc 1",
                link="https://example.local/doc-1",
                blurb="Evidence snippet",
                metadata={
                    "connector_id": "conn-1",
                    "jurisdiction": "us",
                    "data_classification": "internal",
                },
            )
        ],
        tool_calls=[],
        message_id=101,
        chat_session_id="session-1",
    )
    req = SimpleNamespace(stream=False, origin="api")
    return {"chat_result": result, "chat_message_req": req}


def _real_gate_fn(host_context: dict, context_override: dict | None) -> dict:
    adapter = OnyxHostAdapter()
    context = {**adapter.get_request_metadata(host_context), **(context_override or {})}
    assert_no_bypass_inputs(host_context, context)
    payload = adapter.set_final_response(
        host_context,
        TrustEvidenceGate().gate_response(
            draft_answer_text=adapter.get_draft_answer(host_context),
            retrieved_evidence=adapter.get_retrieved_evidence(host_context),
            context=context,
        ),
    )
    assert_no_raw_output(payload)
    return payload


def test_enforce_mode_returns_four_key_contract_and_audit_id(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("TRUST_EVIDENCE_ENABLED", "true")
    monkeypatch.setenv("TRUST_EVIDENCE_MODE", "enforce")
    monkeypatch.setattr(registry, "_default_store", TraceFileStore(base_dir=tmp_path / "store"))

    response = maybe_apply_trust(
        host_context=_host_context(),
        original_response={"response_type": "host"},
        gate_fn=_real_gate_fn,
        tenant_id="tenant-e2e",
        request_path="/api/chat/send-chat-message",
    )

    assert set(response.keys()) == {"final_answer", "citations", "trust", "audit_pack_id"}
    assert response["audit_pack_id"]
    assert response["citations"]


def test_observe_mode_returns_host_shape_and_creates_exportable_audit_pack(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("TRUST_EVIDENCE_ENABLED", "true")
    monkeypatch.setenv("TRUST_EVIDENCE_MODE", "observe")
    monkeypatch.setattr(registry, "_default_store", TraceFileStore(base_dir=tmp_path / "store"))

    response = maybe_apply_trust(
        host_context=_host_context(),
        original_response={"response_type": "host"},
        gate_fn=_real_gate_fn,
        tenant_id="tenant-e2e",
        request_path="/api/chat/send-chat-message",
    )

    assert response == {"response_type": "host"}
    records = list((tmp_path / "store").glob("*.json"))
    assert records

    trace_id = records[0].stem
    zip_path = AuditPackExporter(registry.get_default_store()).export_audit_pack(
        trace_id, output_dir=tmp_path / "audit"
    )
    assert zip_path.exists()


def test_off_mode_returns_host_shape_and_creates_no_audit_pack(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("TRUST_EVIDENCE_ENABLED", "false")
    monkeypatch.setenv("TRUST_EVIDENCE_MODE", "enforce")
    monkeypatch.setattr(registry, "_default_store", TraceFileStore(base_dir=tmp_path / "store"))

    response = maybe_apply_trust(
        host_context=_host_context(),
        original_response={"response_type": "host"},
        gate_fn=_real_gate_fn,
        tenant_id="tenant-e2e",
        request_path="/api/chat/send-chat-message",
    )

    assert response == {"response_type": "host"}
    assert list((tmp_path / "store").glob("*.json")) == []
