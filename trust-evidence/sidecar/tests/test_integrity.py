from __future__ import annotations

import json

from exporter.integrity import build_chain
from exporter.integrity import build_manifest
from exporter.integrity import compute_payload_hash
from exporter.integrity import verify_chain


def _events() -> list[dict]:
    payload1 = {"query": "hello", "turn_index": 0}
    payload2 = {"decision": "allow"}
    return [
        {
            "id": 1,
            "type": "turn_start",
            "ts": "2026-02-07T18:00:00Z",
            "payload_hash": compute_payload_hash(payload1),
        },
        {
            "id": 2,
            "type": "policy_decision",
            "ts": "2026-02-07T18:00:01Z",
            "payload_hash": compute_payload_hash(payload2),
        },
    ]


def test_manifest_and_chain_build_and_verify() -> None:
    events = _events()
    manifest = build_manifest(events)
    assert manifest["event_count"] == 2
    assert manifest["events"][0]["type"] == "turn_start"

    chain = build_chain(events)
    assert verify_chain(chain) is True


def test_verify_chain_fails_on_tamper() -> None:
    chain = build_chain(_events())
    lines = chain.splitlines()
    obj = json.loads(lines[1])
    obj["payload_hash"] = "f" * 64
    lines[1] = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    tampered = "\n".join(lines) + "\n"
    assert verify_chain(tampered) is False


def test_payload_hash_deterministic() -> None:
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}
    assert compute_payload_hash(left) == compute_payload_hash(right)
