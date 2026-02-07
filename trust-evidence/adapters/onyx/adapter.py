from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib import error
from urllib import request


SCHEMA_VERSION = "1.0.0"
DEFAULT_BATCH_SIZE = 10
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT_SECONDS = 5.0

_REQUIRED_COMMON_FIELDS = {"trace_id", "span_id", "parent_span_id", "ts", "host", "host_version", "session_id", "user_id"}


@dataclass
class _AdapterState:
    pending_events: list[dict[str, Any]]


_STATE = _AdapterState(pending_events=[])


def create_trace_id() -> str:
    """Create a sidecar-compatible trace identifier."""
    return f"tr_{uuid.uuid4().hex}"


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _compute_payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _build_ingest_token() -> str:
    token = os.getenv("TRUST_INGEST_TOKEN")
    if token:
        return token

    secret = os.getenv("TRUST_JWT_SECRET")
    if not secret:
        raise RuntimeError("TRUST_INGEST_TOKEN or TRUST_JWT_SECRET must be configured")

    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": "trust-evidence-adapter",
        "scope": "trust:ingest",
        "iat": now,
        "exp": now + 300,
    }
    header_b64 = _b64url_encode(json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def _normalize_event(event_type: str, common_fields: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(f for f in _REQUIRED_COMMON_FIELDS if f not in common_fields)
    if missing:
        raise ValueError(f"common_fields missing required values: {', '.join(missing)}")

    event = dict(common_fields)
    event["event_type"] = event_type
    event["payload"] = payload
    event["payload_hash"] = _compute_payload_hash(payload)
    event.setdefault("schema_version", SCHEMA_VERSION)
    return event


def _batch_size() -> int:
    raw = os.getenv("TRUST_INGEST_BATCH_SIZE", str(DEFAULT_BATCH_SIZE))
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_BATCH_SIZE


def _max_retries() -> int:
    raw = os.getenv("TRUST_INGEST_MAX_RETRIES", str(DEFAULT_MAX_RETRIES))
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MAX_RETRIES


def _send_batch(events: list[dict[str, Any]]) -> dict[str, Any]:
    base_url = os.getenv("TRUST_SIDECAR_URL")
    if not base_url:
        raise RuntimeError("TRUST_SIDECAR_URL must be configured")

    url = f"{base_url.rstrip('/')}/v1/events"
    token = _build_ingest_token()
    body = json.dumps({"events": events}, separators=(",", ":")).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    retries = _max_retries()
    for attempt in range(retries):
        try:
            with request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as resp:
                response_body = resp.read().decode("utf-8")
                return json.loads(response_body) if response_body else {"status": "accepted", "inserted": len(events)}
        except error.HTTPError as exc:
            # Retry only on transient server-side failures.
            if exc.code < 500 or attempt == retries - 1:
                raise
        except error.URLError:
            if attempt == retries - 1:
                raise

        time.sleep(0.2 * (attempt + 1))

    raise RuntimeError("unreachable")


def flush_events() -> dict[str, Any] | None:
    """Flush pending buffered events to the sidecar."""
    if not _STATE.pending_events:
        return None

    to_send = list(_STATE.pending_events)
    _STATE.pending_events.clear()
    return _send_batch(to_send)


def emit_event(event_type: str, common_fields: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any] | None:
    """Queue an event and post batched data to sidecar once batch size is reached."""
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")

    event = _normalize_event(event_type=event_type, common_fields=common_fields, payload=payload)
    _STATE.pending_events.append(event)

    if len(_STATE.pending_events) >= _batch_size():
        return flush_events()
    return None


def default_common_fields(
    trace_id: str,
    span_id: str,
    *,
    parent_span_id: str | None,
    host: str,
    host_version: str,
    session_id: str,
    user_id: str,
) -> dict[str, Any]:
    """Helper for adapters to assemble shared event fields."""
    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "ts": datetime.utcnow().isoformat() + "Z",
        "host": host,
        "host_version": host_version,
        "session_id": session_id,
        "user_id": user_id,
        "schema_version": SCHEMA_VERSION,
    }
