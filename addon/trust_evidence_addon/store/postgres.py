from __future__ import annotations

import json
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Callable

from trust_evidence_addon.store.base import EvidenceStoreBase
from trust_evidence_addon.store.crypto import decrypt_bytes
from trust_evidence_addon.store.crypto import encode_manifest_blob
from trust_evidence_addon.store.crypto import encrypt_bytes


class PostgresEvidenceStore(EvidenceStoreBase):
    def __init__(
        self,
        connect: Callable[[], Any],
        encryption_key: str | None = None,
    ) -> None:
        self._connect = connect
        self.encryption_key = encryption_key

    def put_event(self, trace_id: str, event: dict[str, Any]) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO trust_events(trace_id, payload, created_at) VALUES (%s, %s, %s)",
                    (trace_id, json.dumps(event), datetime.now(timezone.utc).isoformat()),
                )
            conn.commit()

    def list_events(self, trace_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT payload FROM trust_events WHERE trace_id=%s", (trace_id,))
                return [json.loads(row[0]) for row in cur.fetchall()]

    def put_audit_pack(self, trace_id: str, blob: bytes, manifest: dict[str, Any]) -> None:
        encrypted = encrypt_bytes(blob, self.encryption_key)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO trust_packs(trace_id, blob_b64, manifest, created_at, encrypted) VALUES (%s, %s, %s, %s, %s) "
                    "ON CONFLICT (trace_id) DO UPDATE SET blob_b64=EXCLUDED.blob_b64, manifest=EXCLUDED.manifest, created_at=EXCLUDED.created_at, encrypted=EXCLUDED.encrypted",
                    (
                        trace_id,
                        encode_manifest_blob(encrypted),
                        json.dumps(manifest),
                        datetime.now(timezone.utc).isoformat(),
                        bool(self.encryption_key),
                    ),
                )
            conn.commit()

    def get_audit_pack(self, trace_id: str) -> tuple[bytes, dict[str, Any]]:
        from trust_evidence_addon.store.crypto import decode_manifest_blob

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT blob_b64, manifest FROM trust_packs WHERE trace_id=%s",
                    (trace_id,),
                )
                row = cur.fetchone()
        if row is None:
            raise KeyError(trace_id)
        blob = decrypt_bytes(decode_manifest_blob(row[0]), self.encryption_key)
        return blob, json.loads(row[1])

    def gc(self, *, retention_days: int, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM trust_packs WHERE created_at < (%s::timestamptz - (%s || ' days')::interval)",
                    (now.isoformat(), str(retention_days)),
                )
                deleted = getattr(cur, "rowcount", 0)
                cur.execute(
                    "DELETE FROM trust_events WHERE created_at < (%s::timestamptz - (%s || ' days')::interval)",
                    (now.isoformat(), str(retention_days)),
                )
            conn.commit()
        return int(deleted)
