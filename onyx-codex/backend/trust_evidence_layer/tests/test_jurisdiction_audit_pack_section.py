import json
from pathlib import Path

from trust_evidence_layer.audit_pack import AuditPackExporter
from trust_evidence_layer.gate import TrustEvidenceGate
from trust_evidence_layer.storage.file_store import TraceFileStore


def test_jurisdiction_audit_pack_section(tmp_path: Path) -> None:
    store = TraceFileStore(base_dir=tmp_path)
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="Claim",
        retrieved_evidence=[
            {
                "id": "e1",
                "snippet": "Snippet",
                "jurisdiction": "EU",
                "allowed_scopes": ["response_generation"],
            }
        ],
        context={"chat_session_id": "j2", "message_id": 2, "allowed_jurisdictions": ["US"]},
    )
    store.store(response.trace_id, response.to_ordered_dict(), {"request_metadata": {}}, replay_inputs={})

    exporter = AuditPackExporter(store)
    exporter.export_audit_pack(response.trace_id, output_dir=tmp_path)

    payload = json.loads((tmp_path / f"audit_{response.trace_id}" / "jurisdiction_compliance.json").read_text())
    assert "allowed_jurisdictions" in payload
    narrative = (tmp_path / f"audit_{response.trace_id}" / "chain_of_custody.md").read_text()
    assert "Jurisdiction Compliance" in narrative
