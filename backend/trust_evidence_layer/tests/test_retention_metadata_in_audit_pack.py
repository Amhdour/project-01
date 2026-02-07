import json
from pathlib import Path

import pytest

from trust_evidence_layer.audit_pack import AuditPackExporter
from trust_evidence_layer.gate import TrustEvidenceGate
from trust_evidence_layer.storage.file_store import TraceFileStore


def test_retention_metadata_written_to_manifest_and_delete_blocked(tmp_path: Path) -> None:
    store = TraceFileStore(base_dir=tmp_path)
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="The sky is blue.",
        retrieved_evidence=[{"id": "d", "snippet": "The sky is blue.", "origin": "INTERNAL", "trust_level": "PRIMARY"}],
        context={
            "chat_session_id": "ret1",
            "message_id": 6,
            "retention_policy": "LEGAL_HOLD",
            "retention_reason": "INCIDENT",
            "legal_hold": True,
        },
    )

    store.store(
        trace_id=response.trace_id,
        response_payload=response.to_ordered_dict(),
        raw_context_minimal={"request_metadata": {"chat_session_id": "ret1"}},
    )

    exporter = AuditPackExporter(store)
    exporter.export_audit_pack(response.trace_id, output_dir=tmp_path)
    manifest = json.loads((tmp_path / f"audit_{response.trace_id}" / "manifest.json").read_text())

    assert manifest["retention"]["retention_policy"] == "LEGAL_HOLD"
    assert manifest["retention"]["legal_hold"] is True

    with pytest.raises(PermissionError, match="legal hold"):
        store.delete(response.trace_id)
