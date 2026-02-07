from __future__ import annotations

from datetime import datetime
from datetime import timedelta

from fastapi import HTTPException

from exporter.integrity import compute_payload_hash
from app.main import place_legal_hold
from app.main import release_legal_hold
from store.repository import SidecarStore
from store.repository import StoreConfig


def _event(trace_id: str, ts: str) -> dict:
    payload = {"turn_index": 0, "query": "hello"}
    return {
        "trace_id": trace_id,
        "span_id": "sp_1",
        "parent_span_id": None,
        "ts": ts,
        "host": "onyx",
        "host_version": "Development",
        "session_id": "sess_1",
        "user_id": "user_1",
        "payload": payload,
        "payload_hash": compute_payload_hash(payload),
        "schema_version": "1.0.0",
        "event_type": "turn_start",
    }


def test_legal_hold_prevents_retention_deletion(tmp_path, monkeypatch) -> None:
    import app.main as app_main

    store = SidecarStore(StoreConfig(database_url=f"sqlite:///{tmp_path}/sidecar.db"))
    monkeypatch.setattr(app_main, "store", store)

    old_ts = (datetime.utcnow() - timedelta(days=90)).isoformat() + "Z"
    store.ingest_batch([_event("tr_hold", old_ts)])
    store.ingest_batch([_event("tr_delete", old_ts)])

    place_legal_hold("tr_hold", claims={"scope": "trust:admin"})

    result = store.run_retention(retention_days=30, now=datetime.utcnow())
    assert result["deleted_traces"] >= 1

    hold_summary = store.get_trace_summary("tr_hold")
    assert hold_summary["legal_hold"] is True


def test_release_legal_hold_allows_retention(tmp_path, monkeypatch) -> None:
    import app.main as app_main

    store = SidecarStore(StoreConfig(database_url=f"sqlite:///{tmp_path}/sidecar.db"))
    monkeypatch.setattr(app_main, "store", store)

    old_ts = (datetime.utcnow() - timedelta(days=90)).isoformat() + "Z"
    store.ingest_batch([_event("tr_release", old_ts)])

    place_legal_hold("tr_release", claims={"scope": "trust:admin"})
    release_legal_hold("tr_release", claims={"scope": "trust:admin"})

    store.run_retention(retention_days=30, now=datetime.utcnow())

    try:
        store.get_trace_summary("tr_release")
        raise AssertionError("trace should have been deleted after hold release")
    except HTTPException as exc:
        assert exc.status_code == 404
