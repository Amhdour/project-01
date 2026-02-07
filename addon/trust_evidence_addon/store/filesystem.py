from __future__ import annotations

import json
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path
from typing import Any

from trust_evidence_addon.store.base import EvidenceStoreBase
from trust_evidence_addon.store.crypto import decode_manifest_blob
from trust_evidence_addon.store.crypto import decrypt_bytes
from trust_evidence_addon.store.crypto import encode_manifest_blob
from trust_evidence_addon.store.crypto import encrypt_bytes


class FilesystemEvidenceStore(EvidenceStoreBase):
    def __init__(self, base_dir: str | Path, encryption_key: str | None = None) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.encryption_key = encryption_key

    def _event_path(self, trace_id: str) -> Path:
        return self.base_dir / f"{trace_id}.events.json"

    def _pack_path(self, trace_id: str) -> Path:
        return self.base_dir / f"{trace_id}.pack.json"

    def put_event(self, trace_id: str, event: dict[str, Any]) -> None:
        path = self._event_path(trace_id)
        events: list[dict[str, Any]] = []
        if path.exists():
            events = json.loads(path.read_text())
        events.append(event)
        path.write_text(json.dumps(events, ensure_ascii=False, indent=2, sort_keys=True))

    def list_events(self, trace_id: str) -> list[dict[str, Any]]:
        path = self._event_path(trace_id)
        if not path.exists():
            return []
        return json.loads(path.read_text())

    def put_audit_pack(self, trace_id: str, blob: bytes, manifest: dict[str, Any]) -> None:
        encrypted = encrypt_bytes(blob, self.encryption_key)
        payload = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "manifest": manifest,
            "blob_b64": encode_manifest_blob(encrypted),
            "encrypted": bool(self.encryption_key),
        }
        self._pack_path(trace_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        )

    def get_audit_pack(self, trace_id: str) -> tuple[bytes, dict[str, Any]]:
        payload = json.loads(self._pack_path(trace_id).read_text())
        encrypted_blob = decode_manifest_blob(payload["blob_b64"])
        blob = decrypt_bytes(encrypted_blob, self.encryption_key)
        return blob, payload["manifest"]

    def gc(self, *, retention_days: int, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        cutoff = now - timedelta(days=retention_days)
        deleted = 0
        for pack in self.base_dir.glob("*.pack.json"):
            payload = json.loads(pack.read_text())
            created = datetime.fromisoformat(payload["created_at"])
            if created < cutoff:
                trace_id = pack.name.replace(".pack.json", "")
                events = self._event_path(trace_id)
                if events.exists():
                    events.unlink()
                pack.unlink()
                deleted += 1
        return deleted
