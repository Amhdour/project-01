from __future__ import annotations

import base64
import hashlib
import hmac
import json

import pytest

from trust_evidence_addon.auth.jwt_auth import AuthError
from trust_evidence_addon.auth.jwt_auth import JWTConfig
from trust_evidence_addon.auth.jwt_auth import require_claim
from trust_evidence_addon.auth.jwt_auth import verify_hs256_jwt


def _enc(obj: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")


def _token(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h = _enc(header)
    p = _enc(payload)
    sig = hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    s = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    return f"{h}.{p}.{s}"


def test_jwt_verify_success_and_claim_required() -> None:
    cfg = JWTConfig(issuer="iss", audience="aud", hs256_secret="secret")
    tok = _token({"iss": "iss", "aud": "aud", "scope": "trust:audit:read"}, "secret")
    claims = verify_hs256_jwt(tok, cfg)
    require_claim(claims, "trust:audit:read")


def test_jwt_invalid_signature() -> None:
    cfg = JWTConfig(issuer="iss", audience="aud", hs256_secret="secret")
    tok = _token({"iss": "iss", "aud": "aud"}, "wrong")
    with pytest.raises(AuthError):
        verify_hs256_jwt(tok, cfg)


def test_jwt_invalid_issuer_audience() -> None:
    cfg = JWTConfig(issuer="iss", audience="aud", hs256_secret="secret")
    tok = _token({"iss": "bad", "aud": "aud"}, "secret")
    with pytest.raises(AuthError):
        verify_hs256_jwt(tok, cfg)
    tok2 = _token({"iss": "iss", "aud": "bad"}, "secret")
    with pytest.raises(AuthError):
        verify_hs256_jwt(tok2, cfg)
