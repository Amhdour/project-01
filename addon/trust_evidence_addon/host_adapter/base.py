from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any

from pydantic import BaseModel


class TurnStartEvent(BaseModel):
    trace_id: str
    tenant_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None


class ToolCallEvent(BaseModel):
    trace_id: str
    tool_name: str
    arguments: dict[str, Any] | None = None
    result: dict[str, Any] | str | None = None


class RetrievalEvent(BaseModel):
    trace_id: str
    source_id: str
    title: str | None = None
    uri: str | None = None
    metadata: dict[str, Any] = {}


class CitationEvent(BaseModel):
    trace_id: str
    citation_number: int
    source_id: str


class FinalizeTurnEvent(BaseModel):
    trace_id: str
    answer: str
    decision: str | None = None


class AuditPackEvent(BaseModel):
    trace_id: str
    manifest: dict[str, Any]


class HostAdapterBase(ABC):
    @abstractmethod
    def start_turn(self, event: TurnStartEvent) -> None: ...

    @abstractmethod
    def record_tool_call(self, event: ToolCallEvent) -> None: ...

    @abstractmethod
    def record_retrieval(self, event: RetrievalEvent) -> None: ...

    @abstractmethod
    def record_citations(self, event: CitationEvent) -> None: ...

    @abstractmethod
    def finalize_turn(self, event: FinalizeTurnEvent) -> None: ...

    @abstractmethod
    def build_audit_pack(self, trace_id: str) -> AuditPackEvent: ...
