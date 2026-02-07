from __future__ import annotations

from pathlib import Path

from trust_evidence_addon.config import AddonConfig
from trust_evidence_addon.store.filesystem import FilesystemEvidenceStore
from trust_evidence_addon.store.postgres import PostgresEvidenceStore


def build_store(config: AddonConfig):
    if config.store_backend == "postgres":
        if not config.postgres_dsn:
            raise RuntimeError("TRUST_STORE_POSTGRES_DSN required for postgres backend")

        def _connect():
            import psycopg  # type: ignore

            return psycopg.connect(config.postgres_dsn)

        return PostgresEvidenceStore(_connect, encryption_key=config.encryption_key)

    return FilesystemEvidenceStore(Path(config.filesystem_dir), encryption_key=config.encryption_key)
