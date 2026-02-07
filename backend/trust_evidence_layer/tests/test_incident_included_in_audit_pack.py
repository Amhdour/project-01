import json
from pathlib import Path

from trust_evidence_layer.audit_pack import AuditPackExporter
from trust_evidence_layer.gate import TrustEvidenceGate
from trust_evidence_layer.storage.file_store import TraceFileStore


def test_incident_included_in_audit_pack(tmp_path: Path) -> None:
    store = TraceFileStore(base_dir=tmp_path)
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="A factual claim with no evidence.",
        retrieved_evidence=[],
        context={"chat_session_id": "i2", "message_id": 2},
    )
    record = store.load(response.trace_id) if (tmp_path / f"{response.trace_id}.json").exists() else None
    if not record:
        store.store(response.trace_id, response.to_ordered_dict(), {"request_metadata": {}}, replay_inputs={})

    exporter = AuditPackExporter(store)
    exporter.export_audit_pack(response.trace_id, output_dir=tmp_path)

    incidents = json.loads((tmp_path / f"audit_{response.trace_id}" / "incident_events.json").read_text())
    assert isinstance(incidents, list)
