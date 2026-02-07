from __future__ import annotations

import json
from urllib import error

import adapter


class _Resp:
    def __init__(self, body: str) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _common(trace_id: str = "tr_1") -> dict:
    return {
        "trace_id": trace_id,
        "span_id": "sp_1",
        "parent_span_id": None,
        "ts": "2026-02-07T00:00:00Z",
        "host": "onyx",
        "host_version": "dev",
        "session_id": "sess_1",
        "user_id": "user_1",
    }


def test_emit_event_flushes_batch(monkeypatch) -> None:
    calls: list[dict] = []

    def _fake_urlopen(req, timeout):
        calls.append({
            "url": req.full_url,
            "headers": dict(req.header_items()),
            "body": json.loads(req.data.decode("utf-8")),
        })
        return _Resp('{"status":"accepted","inserted":2}')

    monkeypatch.setenv("TRUST_SIDECAR_URL", "http://localhost:8085")
    monkeypatch.setenv("TRUST_INGEST_TOKEN", "fake-token")
    monkeypatch.setenv("TRUST_INGEST_BATCH_SIZE", "2")
    monkeypatch.setattr(adapter.request, "urlopen", _fake_urlopen)
    adapter._STATE.pending_events.clear()

    assert adapter.emit_event("turn_start", _common("tr_a"), {"query": "hello"}) is None
    out = adapter.emit_event("turn_final", _common("tr_a"), {"finish_reason": "stop"})

    assert out == {"status": "accepted", "inserted": 2}
    assert len(calls) == 1
    sent = calls[0]["body"]["events"]
    assert sent[0]["payload_hash"] == adapter._compute_payload_hash({"query": "hello"})


def test_retry_on_5xx(monkeypatch) -> None:
    attempts = {"n": 0}

    def _flaky(req, timeout):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise error.HTTPError(req.full_url, 503, "unavailable", hdrs=None, fp=None)
        return _Resp('{"status":"accepted","inserted":1}')

    monkeypatch.setenv("TRUST_SIDECAR_URL", "http://localhost:8085")
    monkeypatch.setenv("TRUST_INGEST_TOKEN", "fake-token")
    monkeypatch.setenv("TRUST_INGEST_MAX_RETRIES", "3")
    monkeypatch.setattr(adapter.request, "urlopen", _flaky)
    adapter._STATE.pending_events = [adapter._normalize_event("turn_start", _common(), {"query": "x"})]

    out = adapter.flush_events()

    assert out == {"status": "accepted", "inserted": 1}
    assert attempts["n"] == 2
