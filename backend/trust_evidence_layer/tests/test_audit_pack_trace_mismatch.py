import json
from pathlib import Path

import pytest

from trust_evidence_layer.audit_pack import AuditPackExporter
from trust_evidence_layer.storage.file_store import TraceFileStore


def test_audit_export_rejects_trace_id_mismatch(tmp_path: Path) -> None:
    store = TraceFileStore(base_dir=tmp_path)
    trace_id = "trace-expected"

    store.store(
        trace_id=trace_id,
        response_payload={
            "answer_text": "UNKNOWN: no supporting evidence found.",
            "evidence_bundle_user": {
                "sources": [],
                "citations": [],
                "retrieval_metadata": {},
            },
            "decision_record": {
                "claims": [],
                "evidence_links": [],
                "policy_checks": [],
                "failure_modes": [],
                "timestamps": {},
            },
            "trace_id": trace_id,
        },
        raw_context_minimal={},
    )

    # Tamper with stored trace_id
    trace_file = tmp_path / f"{trace_id}.json"
    record = json.loads(trace_file.read_text())
    record["trace_id"] = "trace-tampered"
    trace_file.write_text(json.dumps(record))

    exporter = AuditPackExporter(store)
    with pytest.raises(ValueError, match="Trace ID mismatch"):
        exporter.export_audit_pack(trace_id, output_dir=tmp_path)
