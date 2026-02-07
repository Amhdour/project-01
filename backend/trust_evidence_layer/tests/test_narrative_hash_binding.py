import json
from pathlib import Path

from trust_evidence_layer.audit_pack import AuditPackExporter
from trust_evidence_layer.gate import TrustEvidenceGate
from trust_evidence_layer.storage.file_store import TraceFileStore


def test_narrative_hash_binding(tmp_path: Path) -> None:
    store = TraceFileStore(base_dir=tmp_path)
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="The sky is blue.",
        retrieved_evidence=[{"id": "d1", "snippet": "The sky is blue.", "trust_level": "PRIMARY", "origin": "INTERNAL"}],
        context={"chat_session_id": "n2", "message_id": 2},
    )
    record = store.load(response.trace_id) if (tmp_path / f"{response.trace_id}.json").exists() else None
    if not record:
        store.store(response.trace_id, response.to_ordered_dict(), {"request_metadata": {}}, replay_inputs={})

    exporter = AuditPackExporter(store)
    exporter.export_audit_pack(response.trace_id, output_dir=tmp_path)

    manifest = json.loads((tmp_path / f"audit_{response.trace_id}" / "manifest.json").read_text())
    assert "narrative_hash" in manifest
    assert manifest["artifacts"]["chain_of_custody.md"] == manifest["narrative_hash"]
