from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import Field


class PolicyTraceEntry(BaseModel):
    policy_id: str
    passed: bool
    version: str


class AttributionItem(BaseModel):
    source_id: str
    title: str | None = None
    uri: str | None = None


class TrustLayerResponseContract(BaseModel):
    contract_version: str = "1.0"
    decision: str
    answer: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    attribution: list[AttributionItem] = Field(default_factory=list)
    audit_pack_ref: str
    policy_trace: list[PolicyTraceEntry] = Field(default_factory=list)
    failure_mode: str = "none"


class AuditPackMetadata(BaseModel):
    trace_id: str
    retention: dict[str, Any]
    narrative_hash: str
    artifacts: dict[str, str]
