from uuid import UUID

from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.orm import Session

from onyx.db.models import CitationEvidenceMap
from onyx.db.models import EvidenceRecord
from trust_layer.adapters.onyx_adapter import OnyxTrustAdapter
from trust_layer.types import EvidenceItem


def persist_evidence_records(
    *,
    db_session: Session,
    request_id: str,
    chat_session_id: str | UUID,
    message_id: int,
    evidence_items: list[EvidenceItem],
) -> None:
    if not evidence_items:
        return

    session_id = (
        chat_session_id if isinstance(chat_session_id, UUID) else UUID(chat_session_id)
    )

    records = [
        EvidenceRecord(
            request_id=request_id,
            chat_session_id=session_id,
            message_id=message_id,
            source_type=item.source,
            source_uri=item.uri,
            chunk_id=item.chunk_id,
            score=item.score,
            snippet=item.text_span,
            metadata_json={**item.metadata, "document_id": item.id},
        )
        for item in evidence_items
    ]

    db_session.add_all(records)
    db_session.flush()


def get_evidence_records_by_message_id(
    *, db_session: Session, message_id: int
) -> list[EvidenceRecord]:
    stmt = (
        select(EvidenceRecord)
        .where(EvidenceRecord.message_id == message_id)
        .order_by(EvidenceRecord.created_at.asc(), EvidenceRecord.id.asc())
    )
    return list(db_session.scalars(stmt).all())


def build_citation_to_evidence_record_map(
    *,
    citation_to_document_id: dict[int, str],
    evidence_records: list[EvidenceRecord],
) -> dict[int, int]:
    normalized_records = []
    for record in evidence_records:
        metadata_json = record.metadata_json or {}
        document_id = metadata_json.get("document_id") if isinstance(metadata_json, dict) else None
        normalized_records.append(
            {
                "id": record.id,
                "document_id": document_id,
                "score": record.score,
            }
        )

    return OnyxTrustAdapter.build_citation_to_evidence_map(
        citation_to_document_id=citation_to_document_id,
        evidence_records=normalized_records,
    )


def persist_citation_evidence_map(
    *,
    db_session: Session,
    message_id: int,
    citation_to_evidence_record_id: dict[int, int],
) -> None:
    db_session.execute(
        delete(CitationEvidenceMap).where(CitationEvidenceMap.message_id == message_id)
    )

    rows = [
        CitationEvidenceMap(
            message_id=message_id,
            citation_number=citation_number,
            evidence_record_id=evidence_record_id,
        )
        for citation_number, evidence_record_id in sorted(
            citation_to_evidence_record_id.items(), key=lambda item: item[0]
        )
    ]

    if rows:
        db_session.add_all(rows)
    db_session.flush()


def get_citation_evidence_map_by_message_id(
    *, db_session: Session, message_id: int
) -> dict[int, EvidenceRecord]:
    stmt = (
        select(CitationEvidenceMap, EvidenceRecord)
        .join(
            EvidenceRecord,
            CitationEvidenceMap.evidence_record_id == EvidenceRecord.id,
        )
        .where(CitationEvidenceMap.message_id == message_id)
        .order_by(CitationEvidenceMap.citation_number.asc())
    )

    rows = db_session.execute(stmt).all()
    return {citation_map.citation_number: evidence for citation_map, evidence in rows}
