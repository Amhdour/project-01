from __future__ import annotations

from fastapi import Depends
from fastapi import FastAPI

from app.settings import load_settings
from auth.jwt_auth import claims_from_auth_header
from auth.jwt_auth import require_scopes

# Auth pluggability note:
# v0.1 uses local HS256 validation for bootstrap simplicity. Keep all auth checks
# routed through claims_from_auth_header/require_scopes so this can be swapped
# for JWKS/OIDC verification without changing endpoint business handlers.

app = FastAPI(title="Trust Evidence Sidecar", version="0.1.0")
settings = load_settings()


@app.get("/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": settings.mode}


@app.post("/v1/events")
def ingest_events(claims: dict = Depends(claims_from_auth_header)) -> dict:
    require_scopes(claims, {"trust:ingest"})
    return {"status": "accepted", "detail": "stub ingest endpoint"}


@app.get("/v1/traces/{trace_id}")
def get_trace(trace_id: str, claims: dict = Depends(claims_from_auth_header)) -> dict:
    require_scopes(claims, {"trust:read"})
    return {"trace_id": trace_id, "status": "stub"}


@app.post("/v1/traces/{trace_id}/audit-pack")
def create_audit_pack(trace_id: str, claims: dict = Depends(claims_from_auth_header)) -> dict:
    require_scopes(claims, {"trust:export"})
    return {"trace_id": trace_id, "pack_id": f"pack_{trace_id}", "status": "queued"}


@app.get("/v1/audit-packs/{pack_id}/download")
def download_audit_pack(pack_id: str, claims: dict = Depends(claims_from_auth_header)) -> dict:
    require_scopes(claims, {"trust:read", "trust:export"}, any_of=True)
    return {"pack_id": pack_id, "download": "stub"}
