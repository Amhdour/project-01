from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from trust_evidence_layer.audit_pack import AuditPackExporter
from trust_evidence_layer.storage.file_store import TraceFileStore
from trust_evidence_layer.storage.hash_chain import decode_events_jsonl
from trust_evidence_layer.storage.hash_chain import validate_hash_chain


def _response(trace_id: str) -> dict:
    return {
        "trace_id": trace_id,
        "answer_text": "safe answer",
        "decision_record": {
            "policy_checks": [],
            "claims": [],
            "evidence_links": [],
            "failure_modes": [],
            "incidents": [
                {"code": "A", "severity": "low"},
                {"code": "B", "severity": "medium"},
            ],
        },
        "evidence_bundle_user": {
            "sources": [{"id": "src1", "title": "doc", "snippet": "evidence"}],
            "retrieval_metadata": {"jurisdiction_compliance": {}},
        },
    }


def test_exported_pack_contains_valid_event_hash_chain(tmp_path: Path) -> None:
    trace_id = "trace-chain-valid"
    store = TraceFileStore(base_dir=tmp_path / "store")
    store.store(trace_id=trace_id, response_payload=_response(trace_id), raw_context_minimal={"request_metadata": {}}, replay_inputs={})

    zip_path = AuditPackExporter(store).export_audit_pack(trace_id, output_dir=tmp_path)

    with zipfile.ZipFile(zip_path) as zf:
        events = decode_events_jsonl(zf.read("events.jsonl").decode("utf-8"))
        assert validate_hash_chain(events)

        hash_chain = json.loads(zf.read("hash_chain.json"))
        assert hash_chain["chain_valid"] is True
        assert hash_chain["event_count"] == 2

        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["trace_id"] == trace_id
        assert manifest["counts"]["events"] == 2
        assert "algo_versions" in manifest


def test_tampered_event_hash_chain_fails_validation(tmp_path: Path) -> None:
    trace_id = "trace-chain-tamper"
    store = TraceFileStore(base_dir=tmp_path / "store")
    store.store(trace_id=trace_id, response_payload=_response(trace_id), raw_context_minimal={"request_metadata": {}}, replay_inputs={})

    events_path = (tmp_path / "store" / f"{trace_id}.events.jsonl")
    events = decode_events_jsonl(events_path.read_text())
    events[0]["payload"]["code"] = "TAMPERED"
    events_path.write_text("\n".join(json.dumps(e) for e in events) + "\n")

    with pytest.raises(ValueError, match="hash chain"):
        AuditPackExporter(store).export_audit_pack(trace_id, output_dir=tmp_path)
