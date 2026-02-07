from __future__ import annotations

import json
import zipfile
from pathlib import Path

from exporter.integrity import compute_payload_hash
from app.main import create_audit_pack
from app.main import download_audit_pack
from app.main import ingest_events
from app.main import store
from app.settings import SidecarSettings


def _event(trace_id: str, event_type: str, payload: dict) -> dict:
    return {
        "trace_id": trace_id,
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
        "event_type": event_type,
    }


def test_audit_pack_export_and_download(tmp_path, monkeypatch) -> None:
    import app.main as app_main

    monkeypatch.setattr(store, "db_path", str(tmp_path / "sidecar.db"))
    app_main.settings = SidecarSettings(
        host="0.0.0.0",
        port=8085,
        jwt_secret="secret",
        mode="observe",
        database_url=f"sqlite:///{tmp_path}/sidecar.db",
        packs_dir=str(tmp_path / "packs"),
        retention_days=30,
    )

    trace_id = "tr_export_1"
    body = {
        "events": [
            _event(trace_id, "turn_start", {"query": "hello", "turn_index": 0}),
            _event(trace_id, "retrieval_batch", {"batch_id": "b1", "documents": [{"doc_id": "d1", "uri": "https://example.com"}]}),
            _event(trace_id, "citations_resolved", {"citations": [{"citation_id": "c1", "doc_id": "d1"}]}),
            _event(trace_id, "policy_decision", {"decision": "allow", "rules_evaluated": ["R1"]}),
        ]
    }
    ingest_events(body=body, claims={"scope": "trust:ingest"})

    pack_resp = create_audit_pack(trace_id, claims={"scope": "trust:export"})
    assert pack_resp["status"] == "ready"
    pack_id = pack_resp["pack_id"]

    download_resp = download_audit_pack(pack_id, claims={"scope": "trust:read"})
    zip_path = Path(download_resp.path)
    assert zip_path.exists()

    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        assert "contract.json" in names
        assert "evidence/events.jsonl" in names
        assert "retrieval/retrieval_events.json" in names
        assert "tools/tool_events.json" in names
        assert "citations.json" in names
        assert "policy.json" in names
        assert "integrity/manifest.json" in names
        assert "integrity/chain.jsonl" in names

        manifest = json.loads(zf.read("integrity/manifest.json"))
        assert manifest["event_count"] >= 1
        chain = zf.read("integrity/chain.jsonl").decode("utf-8")
        assert len(chain.strip()) > 0
