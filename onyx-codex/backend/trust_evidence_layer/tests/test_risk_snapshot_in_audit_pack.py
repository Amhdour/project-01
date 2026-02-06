import json
from pathlib import Path

from trust_evidence_layer.audit_pack import AuditPackExporter
from trust_evidence_layer.gate import TrustEvidenceGate
from trust_evidence_layer.storage.file_store import TraceFileStore


def test_risk_snapshot_in_audit_pack(tmp_path: Path) -> None:
    store = TraceFileStore(base_dir=tmp_path)
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="Any claim",
        retrieved_evidence=[],
        context={"chat_session_id": "rsk2", "message_id": 2},
    )
    store.store(response.trace_id, response.to_ordered_dict(), {"request_metadata": {}}, replay_inputs={})

    exporter = AuditPackExporter(store)
    exporter.export_audit_pack(response.trace_id, output_dir=tmp_path)

    payload = json.loads((tmp_path / f"audit_{response.trace_id}" / "risk_register_snapshot.json").read_text())
    assert isinstance(payload, list)
    assert payload
