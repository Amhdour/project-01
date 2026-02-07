from __future__ import annotations

from typing import Any


class InMemoryTraceStore:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}

    def store(
        self,
        trace_id: str,
        payload: dict[str, Any],
        raw_context_minimal: dict[str, Any],
        replay_inputs: dict[str, Any] | None = None,
    ) -> None:
        self._data[trace_id] = {
            "response": payload,
            "context": raw_context_minimal,
            "replay_inputs": replay_inputs or {},
        }

    def get(self, trace_id: str) -> dict[str, Any] | None:
        return self._data.get(trace_id)
