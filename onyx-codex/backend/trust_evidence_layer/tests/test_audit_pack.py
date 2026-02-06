import json
from pathlib import Path

from trust_evidence_layer.audit_pack import AuditPackExporter
from trust_evidence_layer.gate import TrustEvidenceGate
from trust_evidence_layer.storage.file_store import TraceFileStore


def test_audit_pack_export_contains_manifest_and_artifacts(tmp_path: Path) -> None:
    store = TraceFileStore(base_dir=tmp_path)
    gate = TrustEvidenceGate()

    response = gate.gate_response(
        draft_answer_text="The sky is blue.",
        retrieved_evidence=[
            {
                "id": "doc1",
                "title": "Weather",
                "uri": "https://example.com/weather",
                "snippet": "The sky is blue in clear daytime conditions.",
            }
        ],
        context={"chat_session_id": "s6", "message_id": 6},
    )

    # Re-store response in tmp-specific store for exporter
    store.store(
        trace_id=response.trace_id,
        response_payload=response.to_ordered_dict(),
        raw_context_minimal={"request_metadata": {"chat_session_id": "s6"}},
    )

    exporter = AuditPackExporter(store)
    zip_path = exporter.export_audit_pack(response.trace_id, output_dir=tmp_path)

    assert zip_path.exists()

    manifest_path = tmp_path / f"audit_{response.trace_id}" / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert "artifacts" in manifest
    assert "final_response.json" in manifest["artifacts"]
