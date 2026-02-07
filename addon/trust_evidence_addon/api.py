from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException

from trust_evidence_addon.auth.jwt_auth import AuthError
from trust_evidence_addon.auth.jwt_auth import JWTConfig
from trust_evidence_addon.auth.jwt_auth import require_claim
from trust_evidence_addon.auth.jwt_auth import verify_hs256_jwt
from trust_evidence_addon.config import AddonConfig
from trust_evidence_addon.service import build_store

router = APIRouter(prefix="/trust-addon")


def _claims_from_auth_header(authorization: str | None = Header(default=None)) -> dict:
    cfg = AddonConfig.from_env()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    if not cfg.jwt_hs256_secret:
        raise HTTPException(status_code=500, detail="JWT secret not configured")

    token = authorization.split(" ", 1)[1]
    try:
        claims = verify_hs256_jwt(
            token,
            JWTConfig(
                issuer=cfg.jwt_issuer,
                audience=cfg.jwt_audience,
                hs256_secret=cfg.jwt_hs256_secret,
                jwks_url=cfg.jwks_url,
            ),
        )
        return claims
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


@router.get("/audit-packs/{trace_id}")
def get_audit_pack(trace_id: str, claims: dict = Depends(_claims_from_auth_header)) -> dict:
    try:
        require_claim(claims, "trust:audit:read")
    except AuthError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

    blob, manifest = build_store(AddonConfig.from_env()).get_audit_pack(trace_id)
    return {"trace_id": trace_id, "manifest": manifest, "size_bytes": len(blob)}
