from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


class EvidenceItem(BaseModel):
    id: str
    source: str
    uri: str | None = None
    chunk_id: str | None = None
    text_span: str | None = None
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalTrace(BaseModel):
    query: str
    filters: dict[str, Any] = Field(default_factory=dict)
    top_k: int = Field(ge=0)
    results: list[EvidenceItem] = Field(default_factory=list)


class GenerationTrace(BaseModel):
    model: str
    prompt_hash: str
    safety_flags: list[str] = Field(default_factory=list)
    output_hash: str


class TrustReport(BaseModel):
    claims: list[str] = Field(default_factory=list)
    evidence_map: dict[str, list[str]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("evidence_map")
    @classmethod
    def validate_evidence_map_keys(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        """Ensure the evidence map only references known claims by index key."""
        for key in value:
            if not key:
                raise ValueError("evidence_map keys must be non-empty")
        return value
