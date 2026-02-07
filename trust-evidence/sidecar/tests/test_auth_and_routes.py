from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi import HTTPException

from auth.jwt_auth import claims_from_auth_header
from auth.jwt_auth import require_scopes
from app.main import app
from app.main import health


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _token(secret: str, payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(secret.encode("utf-8"), f"{h}.{p}".encode("utf-8"), hashlib.sha256).digest()
    s = _b64url(sig)
    return f"{h}.{p}.{s}"


def test_health_no_auth() -> None:
    out = health()
    assert out["status"] == "ok"


def test_auth_and_scope_enforced(monkeypatch) -> None:
    monkeypatch.setenv("TRUST_JWT_SECRET", "secret")
    tok = _token(
        "secret",
        {
            "exp": int(time.time()) + 60,
            "scope": "trust:ingest trust:read",
        },
    )

    claims = claims_from_auth_header(f"Bearer {tok}")
    require_scopes(claims, {"trust:ingest"})

    with pytest.raises(HTTPException) as exc:
        require_scopes(claims, {"trust:export"})
    assert exc.value.status_code == 403


def test_route_registration() -> None:
    paths = {r.path for r in app.routes}
    assert "/v1/health" in paths
    assert "/v1/events" in paths
    assert "/v1/traces/{trace_id}" in paths
    assert "/v1/traces/{trace_id}/audit-pack" in paths
    assert "/v1/audit-packs/{pack_id}/download" in paths
