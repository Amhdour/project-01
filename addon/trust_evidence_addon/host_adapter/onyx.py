from __future__ import annotations

from pathlib import Path

from trust_evidence_layer.audit_pack import AuditPackExporter
from trust_evidence_layer.host.onyx_adapter import OnyxHostAdapter
from trust_evidence_layer.registry import get_default_store

from trust_evidence_addon.host_adapter.base import AuditPackEvent
from trust_evidence_addon.host_adapter.base import CitationEvent
from trust_evidence_addon.host_adapter.base import FinalizeTurnEvent
from trust_evidence_addon.host_adapter.base import HostAdapterBase
from trust_evidence_addon.host_adapter.base import RetrievalEvent
from trust_evidence_addon.host_adapter.base import ToolCallEvent
from trust_evidence_addon.host_adapter.base import TurnStartEvent


class OnyxAddonAdapter(HostAdapterBase):
    """Thin runtime bridge for Onyx CE integration points."""

    def __init__(self) -> None:
        self._adapter = OnyxHostAdapter()

    def start_turn(self, event: TurnStartEvent) -> None:
        _ = event

    def record_tool_call(self, event: ToolCallEvent) -> None:
        _ = event

    def record_retrieval(self, event: RetrievalEvent) -> None:
        _ = event

    def record_citations(self, event: CitationEvent) -> None:
        _ = event

    def finalize_turn(self, event: FinalizeTurnEvent) -> None:
        _ = event

    def build_audit_pack(self, trace_id: str) -> AuditPackEvent:
        exporter = AuditPackExporter(get_default_store())
        zip_path = exporter.export_audit_pack(trace_id)
        return AuditPackEvent(trace_id=trace_id, manifest={"path": str(Path(zip_path))})
