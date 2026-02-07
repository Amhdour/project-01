from __future__ import annotations

import pytest
from fastapi import HTTPException

from trust_evidence_addon.api import _claims_from_auth_header
from trust_evidence_addon.auth.jwt_auth import JWTConfig
from trust_evidence_addon.auth.jwt_auth import verify_hs256_jwt
from trust_evidence_addon.auth.jwt_auth import require_claim


def _make_token(secret: str) -> str:
    import base64, hashlib, hmac, json

    h = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    p = base64.urlsafe_b64encode(
        json.dumps({"iss": "iss", "aud": "aud", "scope": "trust:audit:read"}).encode()
    ).decode().rstrip("=")
    s = base64.urlsafe_b64encode(hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()).decode().rstrip("=")
    return f"{h}.{p}.{s}"


def test_claim_helpers(monkeypatch):
    monkeypatch.setenv("TRUST_JWT_ISSUER", "iss")
    monkeypatch.setenv("TRUST_JWT_AUDIENCE", "aud")
    monkeypatch.setenv("TRUST_JWT_HS256_SECRET", "secret")
    tok = _make_token("secret")
    claims = _claims_from_auth_header(f"Bearer {tok}")
    require_claim(claims, "trust:audit:read")


def test_missing_auth_header_unauthorized(monkeypatch):
    monkeypatch.setenv("TRUST_JWT_HS256_SECRET", "secret")
    with pytest.raises(HTTPException):
        _claims_from_auth_header(None)


def test_signature_issuer_audience_enforced():
    cfg = JWTConfig(issuer="iss", audience="aud", hs256_secret="secret")
    tok = _make_token("secret")
    claims = verify_hs256_jwt(tok, cfg)
    assert claims["iss"] == "iss"
