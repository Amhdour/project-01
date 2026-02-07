from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SidecarSettings:
    host: str
    port: int
    jwt_secret: str | None
    mode: str
    database_url: str
    packs_dir: str
    retention_days: int


def load_settings() -> SidecarSettings:
    return SidecarSettings(
        host=os.getenv("SIDECAR_HOST", "0.0.0.0"),
        port=int(os.getenv("SIDECAR_PORT", "8085")),
        jwt_secret=os.getenv("TRUST_JWT_SECRET"),
        mode=os.getenv("TRUST_EVIDENCE_MODE", "observe"),
        database_url=os.getenv("SIDECAR_DATABASE_URL", "sqlite:///trust_evidence_sidecar.db"),
        packs_dir=os.getenv("TRUST_PACKS_DIR", ".trust_packs"),
        retention_days=int(os.getenv("TRUST_RETENTION_DAYS", "30")),
    )
