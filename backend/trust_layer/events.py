from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel
from pydantic import Field


class TrustEvent(str, Enum):
    BEFORE_RETRIEVAL = "BEFORE_RETRIEVAL"
    AFTER_RETRIEVAL = "AFTER_RETRIEVAL"
    BEFORE_GENERATION = "BEFORE_GENERATION"
    AFTER_GENERATION = "AFTER_GENERATION"


class TrustContext(BaseModel):
    request_id: str
    tenant_id: str | None = None
    user_id: str | None = None
    chat_session_id: str | None = None
    timestamps: dict[str, datetime] = Field(default_factory=dict)
    debug_flags: dict[str, bool] = Field(default_factory=dict)
