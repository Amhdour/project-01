from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AddonConfig:
    store_backend: str
    retention_days: int
    encryption_key: str | None
    filesystem_dir: str
    postgres_dsn: str | None

    jwt_issuer: str
    jwt_audience: str
    jwt_hs256_secret: str | None
    jwks_url: str | None

    @classmethod
    def from_env(cls) -> "AddonConfig":
        return cls(
            store_backend=os.getenv("TRUST_STORE_BACKEND", "filesystem"),
            retention_days=int(os.getenv("TRUST_RETENTION_DAYS", "30")),
            encryption_key=os.getenv("TRUST_ENCRYPTION_KEY"),
            filesystem_dir=os.getenv("TRUST_STORE_FILESYSTEM_DIR", ".trust_evidence_addon"),
            postgres_dsn=os.getenv("TRUST_STORE_POSTGRES_DSN"),
            jwt_issuer=os.getenv("TRUST_JWT_ISSUER", "trust-addon"),
            jwt_audience=os.getenv("TRUST_JWT_AUDIENCE", "trust-addon"),
            jwt_hs256_secret=os.getenv("TRUST_JWT_HS256_SECRET"),
            jwks_url=os.getenv("TRUST_JWKS_URL"),
        )
