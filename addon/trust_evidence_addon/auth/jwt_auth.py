from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any


class AuthError(PermissionError):
    pass


def _b64url_decode(payload: str) -> bytes:
    pad = '=' * ((4 - len(payload) % 4) % 4)
    return base64.urlsafe_b64decode((payload + pad).encode("utf-8"))


def _b64url_encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")


@dataclass(frozen=True)
class JWTConfig:
    issuer: str
    audience: str
    hs256_secret: str
    jwks_url: str | None = None


def verify_hs256_jwt(token: str, cfg: JWTConfig) -> dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as e:
        raise AuthError("Malformed token") from e

    header = json.loads(_b64url_decode(header_b64))
    if header.get("alg") != "HS256":
        raise AuthError("Unsupported jwt alg")

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected = hmac.new(
        cfg.hs256_secret.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    if not hmac.compare_digest(_b64url_encode(expected), signature_b64):
        raise AuthError("Invalid token signature")

    claims = json.loads(_b64url_decode(payload_b64))
    if claims.get("iss") != cfg.issuer:
        raise AuthError("Invalid issuer")
    aud = claims.get("aud")
    if isinstance(aud, str):
        valid_aud = aud == cfg.audience
    elif isinstance(aud, list):
        valid_aud = cfg.audience in aud
    else:
        valid_aud = False
    if not valid_aud:
        raise AuthError("Invalid audience")
    return claims


def require_claim(claims: dict[str, Any], required: str) -> None:
    scope = claims.get("scope")
    roles = claims.get("roles")
    scopes: set[str] = set()
    if isinstance(scope, str):
        scopes.update(scope.split())
    if isinstance(roles, list):
        scopes.update(str(r) for r in roles)
    if required not in scopes:
        raise AuthError("Missing required claim")
