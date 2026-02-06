from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class LegalHoldStore:
    def __init__(self, base_dir: str | Path = ".trust_evidence_legal_hold") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def store_unredacted(
        self,
        *,
        trace_id: str,
        unredacted_answer: str,
        unredacted_evidence: list[dict[str, Any]],
        unredacted_narrative: str,
    ) -> Path:
        target = self.base_dir / f"{trace_id}_unredacted.json"
        payload = {
            "trace_id": trace_id,
            "answer_text": unredacted_answer,
            "evidence_sources": unredacted_evidence,
            "narrative": unredacted_narrative,
        }
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return target
