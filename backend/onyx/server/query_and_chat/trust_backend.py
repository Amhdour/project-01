from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from pydantic import BaseModel

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
else:
    Session = Any

from onyx.auth.users import current_chat_accessible_user
from onyx.configs.constants import PUBLIC_API_TAGS
from onyx.db.chat import get_chat_message
from onyx.db.evidence import get_citation_evidence_map_by_message_id
from onyx.db.evidence import get_evidence_records_by_message_id
from onyx.db.engine.sql_engine import get_session
from onyx.db.models import User
from shared_configs.contextvars import get_current_tenant_id

router = APIRouter(prefix="/trust")


class EvidenceTraceContext(BaseModel):
    tenant_id: str
    user_id: str | None
    chat_session_id: UUID
    message_id: int


class RetrievalTraceExport(BaseModel):
    query: str | None
    filters: dict[str, str]
    top_k: int


class EvidenceItemExport(BaseModel):
    evidence_record_id: int
    source_type: str
    source_uri: str | None
    chunk_id: str | None
    score: float | None
    snippet: str | None
    metadata_json: dict | None


class EvidenceTraceResponse(BaseModel):
    context: EvidenceTraceContext
    retrieval_trace: RetrievalTraceExport
    evidence_items: list[EvidenceItemExport]
    citation_map: dict[int, int]
    trust_warnings: list[str]


@router.get("/evidence-trace", response_model=EvidenceTraceResponse, tags=PUBLIC_API_TAGS)
def get_evidence_trace(
    message_id: int,
    user: User | None = Depends(current_chat_accessible_user),
    db_session: Session = Depends(get_session),
) -> EvidenceTraceResponse:
    user_id = user.id if user is not None else None
    try:
        chat_message = get_chat_message(
            chat_message_id=message_id,
            user_id=user_id,
            db_session=db_session,
        )
    except ValueError as e:
        # Includes user ownership check; fail closed for cross-tenant/cross-user attempts
        raise HTTPException(status_code=404, detail=str(e))

    evidence_records = get_evidence_records_by_message_id(
        db_session=db_session,
        message_id=message_id,
    )
    citation_map_records = get_citation_evidence_map_by_message_id(
        db_session=db_session,
        message_id=message_id,
    )
    citation_map = {
        citation_number: evidence_record.id
        for citation_number, evidence_record in citation_map_records.items()
    }

    parent_query = None
    if chat_message.parent_message is not None:
        parent_query = chat_message.parent_message.message

    trust_warnings = []

    return EvidenceTraceResponse(
        context=EvidenceTraceContext(
            tenant_id=get_current_tenant_id(),
            user_id=str(user_id) if user_id is not None else None,
            chat_session_id=chat_message.chat_session_id,
            message_id=message_id,
        ),
        retrieval_trace=RetrievalTraceExport(
            query=parent_query,
            filters={},
            top_k=len(evidence_records),
        ),
        evidence_items=[
            EvidenceItemExport(
                evidence_record_id=record.id,
                source_type=record.source_type,
                source_uri=record.source_uri,
                chunk_id=record.chunk_id,
                score=record.score,
                snippet=record.snippet,
                metadata_json=record.metadata_json,
            )
            for record in evidence_records
        ],
        citation_map=citation_map,
        trust_warnings=trust_warnings,
    )
