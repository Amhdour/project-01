from __future__ import annotations

from exporter.integrity import compute_payload_hash
from app.main import get_trace
from app.main import ingest_events
from app.main import store


def test_ingest_and_trace_summary(tmp_path, monkeypatch) -> None:
    # point shared store to isolated DB
    monkeypatch.setattr(store, "db_path", str(tmp_path / "sidecar.db"))

    payload = {"turn_index": 0, "query": "hello"}
    body = {
        "events": [
            {
                "trace_id": "tr_api_1",
                "span_id": "sp_1",
                "parent_span_id": None,
                "ts": "2026-02-07T18:00:00Z",
                "host": "onyx",
                "host_version": "Development",
                "session_id": "sess_1",
                "user_id": "user_1",
                "payload": payload,
                "payload_hash": compute_payload_hash(payload),
                "schema_version": "1.0.0",
                "event_type": "turn_start",
            }
        ]
    }

    out = ingest_events(body=body, claims={"scope": "trust:ingest"})
    assert out["inserted"] == 1

    summary = get_trace("tr_api_1", claims={"scope": "trust:read"})
    assert summary["trace_id"] == "tr_api_1"
    assert summary["total_events"] == 1
