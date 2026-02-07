from __future__ import annotations

import hashlib
import json
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path
from typing import Any

from trust_evidence_layer.storage.hash_chain import build_hash_chain
from trust_evidence_layer.storage.hash_chain import decode_events_jsonl
from trust_evidence_layer.storage.hash_chain import encode_events_jsonl


class TraceFileStore:
    def __init__(self, base_dir: str | Path = ".trust_evidence") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _hash_obj(self, obj: dict[str, Any]) -> str:
        payload = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _default_retention() -> dict[str, Any]:
        expiry = datetime.now(timezone.utc) + timedelta(days=30)
        return {
            "retention_policy": "30_DAYS",
            "retention_reason": "AUDIT",
            "legal_hold": False,
            "expiry_at": expiry.isoformat(),
        }

    @staticmethod
    def _build_events(response_payload: dict[str, Any]) -> list[dict[str, Any]]:
        incidents = response_payload.get("decision_record", {}).get("incidents", [])
        raw_events: list[dict[str, Any]] = []
        if isinstance(incidents, list):
            for incident in incidents:
                raw_events.append(
                    {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "event_type": "incident",
                        "payload": incident if isinstance(incident, dict) else {"value": incident},
                    }
                )
        if not raw_events:
            raw_events.append(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "event_type": "trace_created",
                    "payload": {"trace_id": response_payload.get("trace_id")},
                }
            )
        return build_hash_chain(raw_events)

    def _events_path(self, trace_id: str) -> Path:
        return self.base_dir / f"{trace_id}.events.jsonl"

    def store(
        self,
        trace_id: str,
        response_payload: dict[str, Any],
        raw_context_minimal: dict[str, Any],
        replay_inputs: dict[str, Any] | None = None,
    ) -> Path:
        response_retention = response_payload.get("decision_record", {}).get("retention")
        retention = (
            response_retention if isinstance(response_retention, dict) else self._default_retention()
        )
        replay_inputs = replay_inputs if isinstance(replay_inputs, dict) else {}
        created_at = datetime.now(timezone.utc).isoformat()
        events = self._build_events(response_payload)
        out = {
            "trace_id": trace_id,
            "created_at": created_at,
            "retention": retention,
            "response": response_payload,
            "context": raw_context_minimal,
            "replay_inputs": replay_inputs,
            "response_hash": self._hash_obj(response_payload),
            "context_hash": self._hash_obj(raw_context_minimal),
            "replay_inputs_hash": self._hash_obj(replay_inputs),
            "events_count": len(events),
            "events_hash_chain_version": "prev_hash_plus_canonical_event_v1",
        }
        target = self.base_dir / f"{trace_id}.json"
        target.write_text(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2))
        self._events_path(trace_id).write_text(encode_events_jsonl(events))
        return target

    def load(self, trace_id: str) -> dict[str, Any]:
        target = self.base_dir / f"{trace_id}.json"
        data = json.loads(target.read_text())
        events_target = self._events_path(trace_id)
        if events_target.exists():
            data["events"] = decode_events_jsonl(events_target.read_text())
        else:
            data["events"] = []
        return data

    def delete(self, trace_id: str) -> None:
        target = self.base_dir / f"{trace_id}.json"
        if not target.exists():
            return
        record = json.loads(target.read_text())
        retention = record.get("retention") if isinstance(record.get("retention"), dict) else {}
        if retention.get("legal_hold"):
            raise PermissionError("Deletion blocked by legal hold")
        target.unlink()
        events_target = self._events_path(trace_id)
        if events_target.exists():
            events_target.unlink()
