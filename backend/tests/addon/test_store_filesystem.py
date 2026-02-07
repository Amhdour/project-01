from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from datetime import timezone

from trust_evidence_addon.store.filesystem import FilesystemEvidenceStore
import trust_evidence_addon.store.crypto as crypto


class _FakeFernet:
    def __init__(self, key: str) -> None:
        self.key = key

    def encrypt(self, payload: bytes) -> bytes:
        return b"enc:" + payload

    def decrypt(self, payload: bytes) -> bytes:
        assert payload.startswith(b"enc:")
        return payload[4:]


def test_filesystem_roundtrip_and_gc(tmp_path) -> None:
    store = FilesystemEvidenceStore(tmp_path)
    store.put_event("t1", {"a": 1})
    assert store.list_events("t1") == [{"a": 1}]

    store.put_audit_pack("t1", b"blob", {"m": 1})
    blob, manifest = store.get_audit_pack("t1")
    assert blob == b"blob"
    assert manifest == {"m": 1}

    # force old timestamp
    pack = tmp_path / "t1.pack.json"
    import json

    payload = json.loads(pack.read_text())
    payload["created_at"] = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    pack.write_text(json.dumps(payload))
    deleted = store.gc(retention_days=30)
    assert deleted == 1


def test_filesystem_encryption_toggle(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(crypto, "_build_fernet", lambda key: _FakeFernet(key))
    store = FilesystemEvidenceStore(tmp_path, encryption_key="key")
    store.put_audit_pack("t2", b"secret", {"x": 2})
    blob, manifest = store.get_audit_pack("t2")
    assert blob == b"secret"
    assert manifest == {"x": 2}
