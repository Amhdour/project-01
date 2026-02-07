from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from datetime import datetime
from typing import Any


class EvidenceStoreBase(ABC):
    @abstractmethod
    def put_event(self, trace_id: str, event: dict[str, Any]) -> None: ...

    @abstractmethod
    def list_events(self, trace_id: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    def put_audit_pack(self, trace_id: str, blob: bytes, manifest: dict[str, Any]) -> None: ...

    @abstractmethod
    def get_audit_pack(self, trace_id: str) -> tuple[bytes, dict[str, Any]]: ...

    @abstractmethod
    def gc(self, *, retention_days: int, now: datetime | None = None) -> int: ...
