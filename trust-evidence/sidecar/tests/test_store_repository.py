from __future__ import annotations

from datetime import datetime

from exporter.integrity import compute_payload_hash
from store.repository import SidecarStore
from store.repository import StoreConfig


def _event(trace_id: str = "tr_001", event_type: str = "turn_start") -> dict:
    return {
        "trace_id": trace_id,
        "span_id": "sp_1",
        "parent_span_id": None,
        "ts": "2026-02-07T18:00:00Z",
        "host": "onyx",
        "host_version": "Development",
        "session_id": "s1",
        "user_id": "u1",
        "payload": {"hello": "world"},
        "payload_hash": compute_payload_hash({"hello": "world"}),
        "schema_version": "1.0.0",
        "event_type": event_type,
    }


def test_insert_and_summary(tmp_path) -> None:
    store = SidecarStore(StoreConfig(database_url=f"sqlite:///{tmp_path}/sidecar.db"))
    store.ingest_batch([_event(), _event(event_type="retrieval_batch"), _event(event_type="citations_resolved")])

    summary = store.get_trace_summary("tr_001")
    assert summary["total_events"] == 3
    assert summary["event_counts"]["turn_start"] == 1
    assert summary["evidence_status"] == "complete"


def test_audit_pack_record_lifecycle(tmp_path) -> None:
    store = SidecarStore(StoreConfig(database_url=f"sqlite:///{tmp_path}/sidecar.db"))
    store.create_trace_if_missing("tr_1", "onyx", "Development", "s", "u")
    store.create_audit_pack_record(
        trace_id="tr_1",
        pack_id="pack_1",
        status="queued",
        storage_path=None,
        created_at=datetime.utcnow().isoformat() + "Z",
    )
    store.mark_audit_pack_ready("pack_1", "s3://bucket/pack_1.zip")
