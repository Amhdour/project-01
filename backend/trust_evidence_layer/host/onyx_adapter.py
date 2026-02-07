from __future__ import annotations

from typing import Any

from trust_evidence_layer.host.adapter_base import HostAdapter
from trust_evidence_layer.types import TrustEvidenceResponse


class OnyxHostAdapter(HostAdapter):
    """Thin adapter for Onyx ChatFullResponse objects."""

    @staticmethod
    def _extract_meta(doc: Any) -> tuple[str, str, dict[str, Any]]:
        metadata = getattr(doc, "metadata", {}) or {}
        connector_id = str(
            metadata.get("connector_id")
            or metadata.get("connector")
            or metadata.get("source_id")
            or "unknown"
        )

        jurisdiction = metadata.get("jurisdiction") or metadata.get("region") or "UNKNOWN"
        classification = (
            metadata.get("data_classification")
            or metadata.get("classification")
            or "UNKNOWN"
        )
        gaps: dict[str, Any] = {
            "connector_id": connector_id,
            "source_id": getattr(doc, "document_id", None),
            "unknown_reasons": [],
        }
        if jurisdiction == "UNKNOWN":
            gaps["unknown_reasons"].append("jurisdiction_missing_from_source_metadata")
        if classification == "UNKNOWN":
            gaps["unknown_reasons"].append("classification_missing_from_source_metadata")

        return str(jurisdiction).upper(), str(classification).upper(), gaps

    def get_retrieved_evidence(self, host_context: dict[str, Any]) -> list[dict[str, Any]]:
        chat_result = host_context.get("chat_result")
        if chat_result is None:
            return []

        evidence: list[dict[str, Any]] = []

        top_documents = getattr(chat_result, "top_documents", []) or []
        for doc in top_documents:
            jurisdiction, classification, gaps = self._extract_meta(doc)
            evidence.append(
                {
                    "id": getattr(doc, "document_id", None),
                    "title": getattr(doc, "semantic_identifier", None),
                    "uri": getattr(doc, "link", None),
                    "snippet": getattr(doc, "blurb", "") or "",
                    "origin": "INTERNAL",
                    "trust_level": "PRIMARY",
                    "confidence_weight": 0.95,
                    "jurisdiction": jurisdiction,
                    "data_classification": classification,
                    "allowed_scopes": ["response_generation", "retrieval", "enforcement"],
                    "provenance_gaps": gaps,
                }
            )

        tool_calls = getattr(chat_result, "tool_calls", []) or []
        for call in tool_calls:
            tool_name = str(getattr(call, "tool_name", "") or "")
            for doc in (getattr(call, "search_docs", None) or []):
                jurisdiction, classification, gaps = self._extract_meta(doc)
                evidence.append(
                    {
                        "id": getattr(doc, "document_id", None),
                        "title": getattr(doc, "semantic_identifier", None),
                        "uri": getattr(doc, "link", None),
                        "snippet": getattr(doc, "blurb", "") or "",
                        "origin": "TOOL",
                        "tool_name": tool_name,
                        "jurisdiction": jurisdiction,
                        "data_classification": classification,
                        "allowed_scopes": ["response_generation", "retrieval"],
                        "provenance_gaps": gaps,
                    }
                )

        return evidence

    def get_draft_answer(self, host_context: dict[str, Any]) -> str:
        chat_result = host_context.get("chat_result")
        if chat_result is None:
            return ""
        return str(getattr(chat_result, "answer", "") or "")

    def set_final_response(
        self, host_context: dict[str, Any], response: TrustEvidenceResponse
    ) -> dict[str, Any]:
        return response.to_ordered_dict()

    def get_request_metadata(self, host_context: dict[str, Any]) -> dict[str, Any]:
        chat_result = host_context.get("chat_result")
        chat_req = host_context.get("chat_message_req")

        return {
            "chat_session_id": str(getattr(chat_result, "chat_session_id", "") or ""),
            "message_id": getattr(chat_result, "message_id", None),
            "stream_requested": getattr(chat_req, "stream", None),
            "origin": str(getattr(chat_req, "origin", "") or ""),
        }
