from __future__ import annotations

import hashlib
import json
from datetime import datetime
from datetime import timezone
from typing import Any

HASH_ALGO = "sha256"
CANONICAL_JSON_ALGO = "json_sort_keys_utf8_compact_v1"
HASH_CHAIN_ALGO = "prev_hash_plus_canonical_event_v1"
GENESIS_HASH = "0" * 64


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def event_hash(prev_hash: str, event_without_hash: dict[str, Any]) -> str:
    message = (prev_hash + canonical_json(event_without_hash)).encode("utf-8")
    return hashlib.sha256(message).hexdigest()


def build_hash_chain(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    prev_hash = GENESIS_HASH
    for i, raw in enumerate(events, start=1):
        event = {
            "seq": i,
            "ts": raw.get("ts") or datetime.now(timezone.utc).isoformat(),
            "event_type": str(raw.get("event_type", "unknown")),
            "payload": raw.get("payload", {}),
            "prev_hash": prev_hash,
        }
        digest = event_hash(prev_hash, event)
        event["hash"] = digest
        chain.append(event)
        prev_hash = digest
    return chain


def validate_hash_chain(events: list[dict[str, Any]]) -> bool:
    prev_hash = GENESIS_HASH
    expected_seq = 1
    for event in events:
        if event.get("seq") != expected_seq:
            return False
        if event.get("prev_hash") != prev_hash:
            return False
        materialized = {
            "seq": event.get("seq"),
            "ts": event.get("ts"),
            "event_type": event.get("event_type"),
            "payload": event.get("payload"),
            "prev_hash": event.get("prev_hash"),
        }
        expected_hash = event_hash(prev_hash, materialized)
        if event.get("hash") != expected_hash:
            return False
        prev_hash = expected_hash
        expected_seq += 1
    return True


def encode_events_jsonl(events: list[dict[str, Any]]) -> str:
    return "\n".join(canonical_json(e) for e in events) + ("\n" if events else "")


def decode_events_jsonl(text: str) -> list[dict[str, Any]]:
    lines = [line for line in text.splitlines() if line.strip()]
    return [json.loads(line) for line in lines]
