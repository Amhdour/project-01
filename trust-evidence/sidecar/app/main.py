from __future__ import annotations

from datetime import datetime
import uuid
from pathlib import Path

from fastapi import Body
from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import FileResponse

from app.retention import run_retention_job
from app.settings import load_settings
from auth.jwt_auth import claims_from_auth_header
from auth.jwt_auth import require_scopes
from exporter.audit_pack import build_audit_pack
from store import SidecarStore

# Auth pluggability note:
# v0.1 uses local HS256 validation for bootstrap simplicity. Keep all auth checks
# routed through claims_from_auth_header/require_scopes so this can be swapped
# for JWKS/OIDC verification without changing endpoint business handlers.

app = FastAPI(title="Trust Evidence Sidecar", version="0.1.0")
settings = load_settings()
store = SidecarStore()


@app.get("/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": settings.mode}


@app.post("/v1/events")
def ingest_events(
    body: dict = Body(..., description="{ events: [event, ...] }"),
    claims: dict = Depends(claims_from_auth_header),
) -> dict:
    require_scopes(claims, {"trust:ingest"})
    events = body.get("events") if isinstance(body, dict) else None
    if not isinstance(events, list):
        raise HTTPException(status_code=422, detail="events must be an array")
    inserted = store.ingest_batch(events)
    return {"status": "accepted", **inserted}


@app.get("/v1/traces/{trace_id}")
def get_trace(trace_id: str, claims: dict = Depends(claims_from_auth_header)) -> dict:
    require_scopes(claims, {"trust:read"})
    return store.get_trace_summary(trace_id)


@app.post("/v1/traces/{trace_id}/audit-pack")
def create_audit_pack(trace_id: str, claims: dict = Depends(claims_from_auth_header)) -> dict:
    require_scopes(claims, {"trust:export"})
    pack_id = f"pack_{trace_id}_{uuid.uuid4().hex[:10]}"
    created_at = datetime.utcnow().isoformat() + "Z"

    store.create_audit_pack_record(
        trace_id=trace_id,
        pack_id=pack_id,
        status="queued",
        storage_path=None,
        created_at=created_at,
    )
    _, zip_path = build_audit_pack(trace_id=trace_id, store=store, pack_id=pack_id, packs_dir=settings.packs_dir)
    store.mark_audit_pack_ready(pack_id=pack_id, storage_path=str(zip_path))

    return {"trace_id": trace_id, "pack_id": pack_id, "status": "ready"}


@app.get("/v1/audit-packs/{pack_id}/download")
def download_audit_pack(pack_id: str, claims: dict = Depends(claims_from_auth_header)) -> FileResponse:
    require_scopes(claims, {"trust:read", "trust:export"}, any_of=True)
    record = store.get_audit_pack_record(pack_id)
    if record["status"] != "ready" or not record.get("storage_path"):
        raise HTTPException(status_code=409, detail="Audit pack is not ready")

    path = Path(str(record["storage_path"]))
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audit pack file not found")

    return FileResponse(
        path=path,
        media_type="application/zip",
        filename=f"{pack_id}.zip",
        headers={"Content-Disposition": f'attachment; filename="{pack_id}.zip"'},
    )


@app.post("/v1/admin/traces/{trace_id}/legal-hold")
def place_legal_hold(trace_id: str, claims: dict = Depends(claims_from_auth_header)) -> dict:
    require_scopes(claims, {"trust:admin"})
    store.set_legal_hold(trace_id=trace_id, enabled=True)
    return {"trace_id": trace_id, "legal_hold": True}


@app.delete("/v1/admin/traces/{trace_id}/legal-hold")
def release_legal_hold(trace_id: str, claims: dict = Depends(claims_from_auth_header)) -> dict:
    require_scopes(claims, {"trust:admin"})
    store.set_legal_hold(trace_id=trace_id, enabled=False)
    return {"trace_id": trace_id, "legal_hold": False}


@app.post("/v1/admin/retention/run")
def run_retention(claims: dict = Depends(claims_from_auth_header)) -> dict:
    require_scopes(claims, {"trust:admin"})
    return run_retention_job(store=store, retention_days=settings.retention_days)
