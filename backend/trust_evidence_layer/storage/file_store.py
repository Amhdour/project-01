from __future__ import annotations

import hashlib
import json
from datetime import datetime
from datetime import timezone
from datetime import timedelta
from pathlib import Path
from typing import Any


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
        out = {
            "trace_id": trace_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "retention": retention,
            "response": response_payload,
            "context": raw_context_minimal,
            "replay_inputs": replay_inputs,
            "response_hash": self._hash_obj(response_payload),
            "context_hash": self._hash_obj(raw_context_minimal),
            "replay_inputs_hash": self._hash_obj(replay_inputs),
        }
        target = self.base_dir / f"{trace_id}.json"
        target.write_text(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2))
        return target

    def load(self, trace_id: str) -> dict[str, Any]:
        target = self.base_dir / f"{trace_id}.json"
        return json.loads(target.read_text())

    def delete(self, trace_id: str) -> None:
        target = self.base_dir / f"{trace_id}.json"
        if not target.exists():
            return
        record = json.loads(target.read_text())
        retention = record.get("retention") if isinstance(record.get("retention"), dict) else {}
        if retention.get("legal_hold"):
            raise PermissionError("Deletion blocked by legal hold")
        target.unlink()
