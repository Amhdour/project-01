from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from fastapi import Header
from fastapi import HTTPException


def _b64url_decode(value: str) -> bytes:
    pad = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode((value + pad).encode("utf-8"))


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _verify_hs256(token: str, secret: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as e:
        raise HTTPException(status_code=401, detail="Malformed JWT") from e

    try:
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception as e:
        raise HTTPException(status_code=401, detail="Malformed JWT payload") from e

    if header.get("alg") != "HS256":
        raise HTTPException(status_code=401, detail="Unsupported JWT algorithm")

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    expected_b64 = _b64url_encode(expected)
    if not hmac.compare_digest(expected_b64, signature_b64):
        raise HTTPException(status_code=401, detail="Invalid JWT signature")

    exp = payload.get("exp")
    if isinstance(exp, (int, float)) and float(exp) < time.time():
        raise HTTPException(status_code=401, detail="JWT expired")

    return payload


def claims_from_auth_header(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    secret = os.getenv("TRUST_JWT_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="TRUST_JWT_SECRET not configured")

    token = authorization.split(" ", 1)[1]
    return _verify_hs256(token, secret)


def _extract_scopes(claims: dict[str, Any]) -> set[str]:
    scopes: set[str] = set()

    scope = claims.get("scope")
    if isinstance(scope, str):
        scopes.update(scope.split())

    scp = claims.get("scp")
    if isinstance(scp, str):
        scopes.update(scp.split())
    elif isinstance(scp, list):
        scopes.update(str(v) for v in scp)

    return scopes


def require_scopes(claims: dict[str, Any], required_scopes: set[str], any_of: bool = False) -> None:
    scopes = _extract_scopes(claims)
    if any_of:
        ok = any(scope in scopes for scope in required_scopes)
    else:
        ok = required_scopes.issubset(scopes)

    if not ok:
        raise HTTPException(status_code=403, detail="Missing required scope")
