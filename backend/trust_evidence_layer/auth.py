from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import time
from typing import Any

from fastapi import Header
from fastapi import HTTPException

REQUIRED_AUDIT_SCOPE = "trust:audit:read"
REQUIRED_GATE_SCOPE = "trust:gate:write"


def _b64url_decode(value: str) -> bytes:
    pad = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode((value + pad).encode("utf-8"))


def _verify_rs256_signature(token: str, public_key_pem: str) -> bool:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError:
        return False

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = _b64url_decode(signature_b64)

    with tempfile.NamedTemporaryFile("wb", delete=True) as data_f, tempfile.NamedTemporaryFile(
        "wb", delete=True
    ) as sig_f, tempfile.NamedTemporaryFile("w", delete=True) as pub_f:
        data_f.write(signing_input)
        data_f.flush()
        sig_f.write(signature)
        sig_f.flush()
        pub_f.write(public_key_pem)
        pub_f.flush()

        proc = subprocess.run(
            [
                "openssl",
                "dgst",
                "-sha256",
                "-verify",
                pub_f.name,
                "-signature",
                sig_f.name,
                data_f.name,
            ],
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0


def _claims_from_token(token: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, _ = token.split(".")
    except ValueError as e:
        raise HTTPException(status_code=401, detail="Malformed JWT") from e

    try:
        header = json.loads(_b64url_decode(header_b64))
        claims = json.loads(_b64url_decode(payload_b64))
    except Exception as e:
        raise HTTPException(status_code=401, detail="Malformed JWT payload") from e

    if header.get("alg") != "RS256":
        raise HTTPException(status_code=401, detail="Unsupported JWT algorithm")

    issuer = os.getenv("TRUST_JWT_ISSUER")
    audience = os.getenv("TRUST_JWT_AUDIENCE")
    public_key = os.getenv("TRUST_JWT_PUBLIC_KEY")

    if not issuer or not audience or not public_key:
        raise HTTPException(status_code=401, detail="JWT trust configuration missing")

    if claims.get("iss") != issuer:
        raise HTTPException(status_code=401, detail="Invalid JWT issuer")

    aud = claims.get("aud")
    if isinstance(aud, str):
        aud_ok = aud == audience
    elif isinstance(aud, list):
        aud_ok = audience in aud
    else:
        aud_ok = False
    if not aud_ok:
        raise HTTPException(status_code=401, detail="Invalid JWT audience")

    exp = claims.get("exp")
    if isinstance(exp, (int, float)) and float(exp) < time.time():
        raise HTTPException(status_code=401, detail="JWT expired")

    if not _verify_rs256_signature(token, public_key):
        raise HTTPException(status_code=401, detail="Invalid JWT signature")

    return claims


def claims_from_authorization_header(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1]
    return _claims_from_token(token)


def _has_scope(claims: dict[str, Any], required_scope: str) -> bool:
    scope = claims.get("scope")
    scopes: set[str] = set()
    if isinstance(scope, str):
        scopes.update(scope.split())

    scopes_list = claims.get("scopes")
    if isinstance(scopes_list, list):
        scopes.update(str(s) for s in scopes_list)

    roles = claims.get("roles")
    if isinstance(roles, list):
        scopes.update(str(r) for r in roles)

    return required_scope in scopes


def require_scope(claims: dict[str, Any], required_scope: str) -> None:
    if not _has_scope(claims, required_scope):
        raise HTTPException(status_code=403, detail="Missing required scope")
