from __future__ import annotations

import hashlib
import json
from typing import Any

GENESIS_HASH = "0" * 64


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def compute_payload_hash(payload_json: dict[str, Any]) -> str:
    canonical = _canonical_json(payload_json).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def build_manifest(events: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "manifest_version": "1.0.0",
        "event_count": len(events),
        "events": [
            {
                "id": event.get("id"),
                "type": event.get("type"),
                "ts": event.get("ts"),
                "payload_hash": event.get("payload_hash"),
            }
            for event in events
        ],
    }


def _line_hash(line_without_hash: dict[str, Any]) -> str:
    canonical = _canonical_json(line_without_hash).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def build_chain(events: list[dict[str, Any]]) -> str:
    prev_hash = GENESIS_HASH
    lines: list[str] = []
    for idx, event in enumerate(events, start=1):
        line = {
            "index": idx,
            "event_id": event.get("id"),
            "type": event.get("type"),
            "ts": event.get("ts"),
            "payload_hash": event.get("payload_hash"),
            "prev_hash": prev_hash,
        }
        line_hash = _line_hash(line)
        line["hash"] = line_hash
        lines.append(_canonical_json(line))
        prev_hash = line_hash
    return "\n".join(lines) + ("\n" if lines else "")


def verify_chain(chain_jsonl: str) -> bool:
    prev_hash = GENESIS_HASH
    for expected_index, line in enumerate(chain_jsonl.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception:
            return False

        if obj.get("index") != expected_index:
            return False
        if obj.get("prev_hash") != prev_hash:
            return False

        materialized = {
            "index": obj.get("index"),
            "event_id": obj.get("event_id"),
            "type": obj.get("type"),
            "ts": obj.get("ts"),
            "payload_hash": obj.get("payload_hash"),
            "prev_hash": obj.get("prev_hash"),
        }
        computed = _line_hash(materialized)
        if obj.get("hash") != computed:
            return False
        prev_hash = computed
    return True
