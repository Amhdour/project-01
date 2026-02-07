from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SidecarSettings:
    host: str
    port: int
    jwt_secret: str | None
    mode: str


def load_settings() -> SidecarSettings:
    return SidecarSettings(
        host=os.getenv("SIDECAR_HOST", "0.0.0.0"),
        port=int(os.getenv("SIDECAR_PORT", "8085")),
        jwt_secret=os.getenv("TRUST_JWT_SECRET"),
        mode=os.getenv("TRUST_EVIDENCE_MODE", "observe"),
    )
