from __future__ import annotations

import hashlib
import json
from datetime import datetime
from datetime import timezone
from typing import Any

from onyx.context.search.models import SearchDoc
from onyx.tools.models import ToolResponse
from trust_layer.events import TrustContext
from trust_layer.types import EvidenceItem
from trust_layer.types import GenerationTrace
from trust_layer.types import RetrievalTrace


class OnyxTrustAdapter:
    """Translate Onyx chat pipeline objects to portable trust-layer contract types."""

    @staticmethod
    def build_context(
        request_id: str,
        tenant_id: str | None,
        user_id: str | None,
        chat_session_id: str | None,
    ) -> TrustContext:
        return TrustContext(
            request_id=request_id,
            tenant_id=tenant_id,
            user_id=user_id,
            chat_session_id=chat_session_id,
            timestamps={"created_at": datetime.now(tz=timezone.utc)},
            debug_flags={},
        )

    @staticmethod
    def _hash_payload(payload: Any) -> str:
        dumped = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(dumped).hexdigest()

    @staticmethod
    def build_generation_trace(
        *,
        model: str,
        prompt_messages: list[dict[str, Any]],
        safety_flags: list[str] | None,
        output_text: str,
    ) -> GenerationTrace:
        return GenerationTrace(
            model=model,
            prompt_hash=OnyxTrustAdapter._hash_payload(prompt_messages),
            safety_flags=safety_flags or [],
            output_hash=OnyxTrustAdapter._hash_payload(output_text),
        )

    @staticmethod
    def search_doc_to_evidence_item(doc: SearchDoc) -> EvidenceItem:
        return EvidenceItem(
            id=doc.document_id,
            source=str(doc.source_type),
            uri=doc.link,
            chunk_id=str(doc.chunk_ind),
            text_span=doc.blurb,
            score=doc.score,
            metadata=doc.metadata,
        )

    @staticmethod
    def build_retrieval_trace(
        *,
        query: str,
        filters: dict[str, Any],
        top_k: int,
        docs: list[SearchDoc],
    ) -> RetrievalTrace:
        return RetrievalTrace(
            query=query,
            filters=filters,
            top_k=top_k,
            results=[OnyxTrustAdapter.search_doc_to_evidence_item(doc) for doc in docs],
        )

    @staticmethod
    def extract_search_docs(tool_responses: list[ToolResponse]) -> list[SearchDoc]:
        docs: list[SearchDoc] = []
        for response in tool_responses:
            rich = response.rich_response
            # SearchDocsResponse is not imported to keep coupling minimal
            search_docs = getattr(rich, "search_docs", None)
            if search_docs:
                docs.extend(search_docs)
        return docs

    @staticmethod
    def build_citation_to_evidence_map(
        *,
        citation_to_document_id: dict[int, str],
        evidence_records: list[dict[str, Any]],
    ) -> dict[int, int]:
        """Build deterministic citation_number -> evidence_record_id mapping."""
        best_by_document: dict[str, dict[str, Any]] = {}
        for record in evidence_records:
            document_id = record.get("document_id")
            record_id = record.get("id")
            if not isinstance(document_id, str) or not isinstance(record_id, int):
                continue

            existing = best_by_document.get(document_id)
            if existing is None:
                best_by_document[document_id] = record
                continue

            current_score = record.get("score")
            existing_score = existing.get("score")
            current_score_val = current_score if isinstance(current_score, (int, float)) else float("-inf")
            existing_score_val = existing_score if isinstance(existing_score, (int, float)) else float("-inf")

            if current_score_val > existing_score_val:
                best_by_document[document_id] = record
            elif current_score_val == existing_score_val and record_id < int(existing.get("id", record_id)):
                best_by_document[document_id] = record

        mapped: dict[int, int] = {}
        for citation_number, document_id in citation_to_document_id.items():
            candidate = best_by_document.get(document_id)
            if candidate is not None:
                mapped[citation_number] = int(candidate["id"])

        return mapped

