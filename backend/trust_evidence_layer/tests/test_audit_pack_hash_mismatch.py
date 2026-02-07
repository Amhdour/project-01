import json
from pathlib import Path

import pytest

from trust_evidence_layer.audit_pack import AuditPackExporter
from trust_evidence_layer.storage.file_store import TraceFileStore


def _base_response(trace_id: str) -> dict:
    return {
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
    }


def test_audit_export_rejects_response_hash_mismatch(tmp_path: Path) -> None:
    store = TraceFileStore(base_dir=tmp_path)
    trace_id = "trace-hash-response"

    store.store(trace_id=trace_id, response_payload=_base_response(trace_id), raw_context_minimal={})

    trace_file = tmp_path / f"{trace_id}.json"
    record = json.loads(trace_file.read_text())
    record["response"]["answer_text"] = "tampered"
    trace_file.write_text(json.dumps(record))

    exporter = AuditPackExporter(store)
    with pytest.raises(ValueError, match="Response hash mismatch"):
        exporter.export_audit_pack(trace_id, output_dir=tmp_path)


def test_audit_export_rejects_context_hash_mismatch(tmp_path: Path) -> None:
    store = TraceFileStore(base_dir=tmp_path)
    trace_id = "trace-hash-context"

    store.store(
        trace_id=trace_id,
        response_payload=_base_response(trace_id),
        raw_context_minimal={"request_metadata": {"path": "/api/chat/send-chat-message"}},
    )

    trace_file = tmp_path / f"{trace_id}.json"
    record = json.loads(trace_file.read_text())
    record["context"]["request_metadata"]["path"] = "/tampered"
    trace_file.write_text(json.dumps(record))

    exporter = AuditPackExporter(store)
    with pytest.raises(ValueError, match="Context hash mismatch"):
        exporter.export_audit_pack(trace_id, output_dir=tmp_path)
