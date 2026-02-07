from __future__ import annotations

import base64


def _build_fernet(key: str):
    from cryptography.fernet import Fernet  # type: ignore

    return Fernet(key.encode("utf-8"))


def encrypt_bytes(payload: bytes, key: str | None) -> bytes:
    if not key:
        return payload
    f = _build_fernet(key)
    return f.encrypt(payload)


def decrypt_bytes(payload: bytes, key: str | None) -> bytes:
    if not key:
        return payload
    f = _build_fernet(key)
    return f.decrypt(payload)


def encode_manifest_blob(payload: bytes) -> str:
    return base64.b64encode(payload).decode("utf-8")


def decode_manifest_blob(payload: str) -> bytes:
    return base64.b64decode(payload.encode("utf-8"))
