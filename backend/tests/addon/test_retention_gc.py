from __future__ import annotations

from trust_evidence_addon.config import AddonConfig
from trust_evidence_addon.service import build_store


def test_gc_command_backend_filesystem(monkeypatch, tmp_path):
    monkeypatch.setenv("TRUST_STORE_BACKEND", "filesystem")
    monkeypatch.setenv("TRUST_STORE_FILESYSTEM_DIR", str(tmp_path))
    cfg = AddonConfig.from_env()
    store = build_store(cfg)
    store.put_audit_pack("t", b"x", {"m": 1})
    deleted = store.gc(retention_days=0)
    assert deleted in (0, 1)
