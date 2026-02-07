from __future__ import annotations

import base64
import json
import subprocess
import time
from pathlib import Path

import pytest
from fastapi import HTTPException

from trust_evidence_layer.auth import claims_from_authorization_header
from trust_evidence_layer.auth import require_scope


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _build_rs256_token(payload: dict, private_key_path: Path) -> str:
    header = {"alg": "RS256", "typ": "JWT"}
    header_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    data_path = private_key_path.parent / "jwt_data.bin"
    sig_path = private_key_path.parent / "jwt_sig.bin"
    data_path.write_bytes(signing_input)

    subprocess.run(
        [
            "openssl",
            "dgst",
            "-sha256",
            "-sign",
            str(private_key_path),
            "-out",
            str(sig_path),
            str(data_path),
        ],
        check=True,
        capture_output=True,
    )
    signature_b64 = _b64url(sig_path.read_bytes())
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def _gen_keypair(tmp_path: Path) -> tuple[Path, str]:
    priv = tmp_path / "private.pem"
    pub = tmp_path / "public.pem"
    subprocess.run(["openssl", "genrsa", "-out", str(priv), "2048"], check=True, capture_output=True)
    subprocess.run(
        ["openssl", "rsa", "-in", str(priv), "-pubout", "-out", str(pub)],
        check=True,
        capture_output=True,
    )
    return priv, pub.read_text()


def test_401_missing_or_invalid_token(monkeypatch, tmp_path: Path) -> None:
    priv, pub = _gen_keypair(tmp_path)
    monkeypatch.setenv("TRUST_JWT_ISSUER", "issuer")
    monkeypatch.setenv("TRUST_JWT_AUDIENCE", "aud")
    monkeypatch.setenv("TRUST_JWT_PUBLIC_KEY", pub)

    with pytest.raises(HTTPException) as exc:
        claims_from_authorization_header(None)
    assert exc.value.status_code == 401

    bad = "Bearer not.a.jwt"
    with pytest.raises(HTTPException) as exc2:
        claims_from_authorization_header(bad)
    assert exc2.value.status_code == 401


def test_403_when_scope_missing(monkeypatch, tmp_path: Path) -> None:
    priv, pub = _gen_keypair(tmp_path)
    monkeypatch.setenv("TRUST_JWT_ISSUER", "issuer")
    monkeypatch.setenv("TRUST_JWT_AUDIENCE", "aud")
    monkeypatch.setenv("TRUST_JWT_PUBLIC_KEY", pub)

    tok = _build_rs256_token(
        {
            "iss": "issuer",
            "aud": "aud",
            "exp": int(time.time()) + 120,
            "scope": "profile email",
        },
        priv,
    )

    claims = claims_from_authorization_header(f"Bearer {tok}")
    with pytest.raises(HTTPException) as exc:
        require_scope(claims, "trust:audit:read")
    assert exc.value.status_code == 403


def test_200_equivalent_when_valid_and_scope_present(monkeypatch, tmp_path: Path) -> None:
    priv, pub = _gen_keypair(tmp_path)
    monkeypatch.setenv("TRUST_JWT_ISSUER", "issuer")
    monkeypatch.setenv("TRUST_JWT_AUDIENCE", "aud")
    monkeypatch.setenv("TRUST_JWT_PUBLIC_KEY", pub)

    tok = _build_rs256_token(
        {
            "iss": "issuer",
            "aud": "aud",
            "exp": int(time.time()) + 120,
            "scope": "trust:audit:read trust:gate:write",
        },
        priv,
    )

    claims = claims_from_authorization_header(f"Bearer {tok}")
    require_scope(claims, "trust:audit:read")
    require_scope(claims, "trust:gate:write")
