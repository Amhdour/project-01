from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any, Iterator

from fastapi import HTTPException

from exporter.integrity import compute_payload_hash
from store.migrations import apply_migrations


@dataclass(frozen=True)
class StoreConfig:
    database_url: str


def _sqlite_path_from_url(url: str) -> str:
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "", 1)
    if url.startswith("postgres"):
        raise RuntimeError("Postgres URL configured but SQLAlchemy/asyncpg runtime is not yet wired in v0.1")
    return url


def _validate_event_payload(event: dict[str, Any]) -> None:
    required = {
        "trace_id",
        "span_id",
        "parent_span_id",
        "ts",
        "host",
        "host_version",
        "session_id",
        "user_id",
        "payload",
        "payload_hash",
        "schema_version",
        "event_type",
    }
    missing = sorted(k for k in required if k not in event)
    if missing:
        raise HTTPException(status_code=422, detail=f"Event missing required fields: {', '.join(missing)}")


class SidecarStore:
    def __init__(self, config: StoreConfig | None = None) -> None:
        self.config = config or StoreConfig(database_url=os.getenv("SIDECAR_DATABASE_URL", "sqlite:///trust_evidence_sidecar.db"))
        self.db_path = _sqlite_path_from_url(self.config.database_url)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        path = Path(self.db_path)
        if path.parent and str(path.parent) != ".":
            path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        try:
            apply_migrations(conn)
            yield conn
            conn.commit()
        finally:
            conn.close()

    def create_trace_if_missing(self, trace_id: str, host: str, host_version: str, session_id: str, user_id: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO traces(trace_id, host, host_version, session_id, user_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(trace_id) DO NOTHING
                """,
                (trace_id, host, host_version, session_id, user_id),
            )

    def insert_event(
        self,
        trace_id: str,
        span_id: str,
        parent_span_id: str | None,
        ts: str,
        type: str,
        payload_json: dict[str, Any],
        payload_hash: str,
        schema_version: str,
    ) -> None:
        if not schema_version:
            raise HTTPException(status_code=422, detail="schema_version is required")

        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO spans(trace_id, span_id, parent_span_id, ts)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(trace_id, span_id) DO NOTHING
                """,
                (trace_id, span_id, parent_span_id, ts),
            )
            conn.execute(
                """
                INSERT INTO events(trace_id, span_id, parent_span_id, ts, type, payload_json, payload_hash, schema_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (trace_id, span_id, parent_span_id, ts, type, json.dumps(payload_json), payload_hash, schema_version),
            )

    def ingest_batch(self, events: list[dict[str, Any]]) -> dict[str, int]:
        count = 0
        for event in events:
            _validate_event_payload(event)
            self.create_trace_if_missing(
                trace_id=event["trace_id"],
                host=event["host"],
                host_version=event["host_version"],
                session_id=event["session_id"],
                user_id=event["user_id"],
            )
            computed_hash = compute_payload_hash(event["payload"])
            if event.get("payload_hash") and event["payload_hash"] != computed_hash:
                raise HTTPException(status_code=422, detail="payload_hash does not match canonical payload hash")

            self.insert_event(
                trace_id=event["trace_id"],
                span_id=event["span_id"],
                parent_span_id=event["parent_span_id"],
                ts=event["ts"],
                type=event["event_type"],
                payload_json=event["payload"],
                payload_hash=computed_hash,
                schema_version=event["schema_version"],
            )
            count += 1
        return {"inserted": count}

    def get_trace_summary(self, trace_id: str) -> dict[str, Any]:
        with self.connection() as conn:
            events = conn.execute("SELECT type FROM events WHERE trace_id = ?", (trace_id,)).fetchall()
            trace_row = conn.execute(
                "SELECT trace_id, retention_until, legal_hold FROM traces WHERE trace_id = ?", (trace_id,)
            ).fetchone()
            if not trace_row:
                raise HTTPException(status_code=404, detail="Trace not found")

        counts = Counter(r[0] for r in events)
        evidence_status = "none"
        if counts:
            evidence_status = "partial"
        if counts.get("retrieval_batch", 0) > 0 and counts.get("citations_resolved", 0) > 0:
            evidence_status = "complete"

        return {
            "trace_id": trace_id,
            "event_counts": dict(counts),
            "total_events": sum(counts.values()),
            "evidence_status": evidence_status,
            "retention_until": trace_row[1],
            "legal_hold": bool(trace_row[2]),
        }

    def get_events_for_trace(self, trace_id: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, trace_id, span_id, parent_span_id, ts, type, payload_json, payload_hash, schema_version
                FROM events
                WHERE trace_id = ?
                ORDER BY ts ASC, id ASC
                """,
                (trace_id,),
            ).fetchall()
        events: list[dict[str, Any]] = []
        for r in rows:
            events.append(
                {
                    "id": r[0],
                    "trace_id": r[1],
                    "span_id": r[2],
                    "parent_span_id": r[3],
                    "ts": r[4],
                    "type": r[5],
                    "payload_json": json.loads(r[6]) if isinstance(r[6], str) else r[6],
                    "payload_hash": r[7],
                    "schema_version": r[8],
                }
            )
        return events

    def get_audit_pack_record(self, pack_id: str) -> dict[str, Any]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT pack_id, trace_id, status, storage_path, created_at, ready_at, retention_until, legal_hold
                FROM audit_packs
                WHERE pack_id = ?
                """,
                (pack_id,),
            ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Audit pack not found")
        return {
            "pack_id": row[0],
            "trace_id": row[1],
            "status": row[2],
            "storage_path": row[3],
            "created_at": row[4],
            "ready_at": row[5],
            "retention_until": row[6],
            "legal_hold": bool(row[7]),
        }

    def create_audit_pack_record(self, trace_id: str, pack_id: str, status: str, storage_path: str | None, created_at: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_packs(pack_id, trace_id, status, storage_path, created_at, retention_until, legal_hold)
                VALUES (?, ?, ?, ?, ?, NULL, 0)
                """,
                (pack_id, trace_id, status, storage_path, created_at),
            )

    def mark_audit_pack_ready(self, pack_id: str, storage_path: str) -> None:
        with self.connection() as conn:
            now = datetime.utcnow().isoformat() + "Z"
            cur = conn.execute(
                """
                UPDATE audit_packs
                SET status = ?, storage_path = ?, ready_at = ?
                WHERE pack_id = ?
                """,
                ("ready", storage_path, now, pack_id),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Audit pack not found")

    def set_legal_hold(self, trace_id: str, enabled: bool) -> None:
        hold_val = 1 if enabled else 0
        with self.connection() as conn:
            cur = conn.execute(
                "UPDATE traces SET legal_hold = ? WHERE trace_id = ?",
                (hold_val, trace_id),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Trace not found")
            conn.execute(
                "UPDATE audit_packs SET legal_hold = ? WHERE trace_id = ?",
                (hold_val, trace_id),
            )

    def run_retention(self, retention_days: int = 30, now: datetime | None = None) -> dict[str, int]:
        now = now or datetime.utcnow()
        now_iso = now.isoformat() + "Z"
        cutoff_iso = (now - timedelta(days=retention_days)).isoformat() + "Z"

        deleted_pack_files = 0
        deleted_packs = 0
        deleted_traces = 0

        with self.connection() as conn:
            pack_rows = conn.execute(
                """
                SELECT pack_id, storage_path
                FROM audit_packs
                WHERE legal_hold = 0
                  AND (
                    (retention_until IS NOT NULL AND julianday(retention_until) <= julianday(?))
                    OR (retention_until IS NULL AND julianday(created_at) <= julianday(?))
                  )
                """,
                (now_iso, cutoff_iso),
            ).fetchall()

            for _, storage_path in pack_rows:
                if storage_path:
                    p = Path(storage_path)
                    if p.exists():
                        try:
                            p.unlink()
                            deleted_pack_files += 1
                        except Exception:
                            pass

            deleted_packs = conn.execute(
                """
                DELETE FROM audit_packs
                WHERE legal_hold = 0
                  AND (
                    (retention_until IS NOT NULL AND julianday(retention_until) <= julianday(?))
                    OR (retention_until IS NULL AND julianday(created_at) <= julianday(?))
                  )
                """,
                (now_iso, cutoff_iso),
            ).rowcount

            trace_rows = conn.execute(
                """
                SELECT trace_id
                FROM traces t
                WHERE t.legal_hold = 0
                  AND NOT EXISTS (
                    SELECT 1 FROM audit_packs ap WHERE ap.trace_id = t.trace_id AND ap.legal_hold = 1
                  )
                  AND (
                    (t.retention_until IS NOT NULL AND julianday(t.retention_until) <= julianday(?))
                    OR (
                      t.retention_until IS NULL
                      AND julianday(
                        COALESCE(
                          (SELECT MIN(e.ts) FROM events e WHERE e.trace_id = t.trace_id),
                          t.created_at
                        )
                      ) <= julianday(?)
                    )
                  )
                """,
                (now_iso, cutoff_iso),
            ).fetchall()

            trace_ids = [r[0] for r in trace_rows]
            for trace_id in trace_ids:
                conn.execute("DELETE FROM events WHERE trace_id = ?", (trace_id,))
                conn.execute("DELETE FROM spans WHERE trace_id = ?", (trace_id,))
                conn.execute("DELETE FROM policy_decisions WHERE trace_id = ?", (trace_id,))
                conn.execute("DELETE FROM audit_packs WHERE trace_id = ? AND legal_hold = 0", (trace_id,))
                deleted_traces += conn.execute("DELETE FROM traces WHERE trace_id = ?", (trace_id,)).rowcount

        return {
            "deleted_traces": deleted_traces,
            "deleted_packs": deleted_packs,
            "deleted_pack_files": deleted_pack_files,
            "retention_days": retention_days,
        }
