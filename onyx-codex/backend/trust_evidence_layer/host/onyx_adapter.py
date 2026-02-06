from __future__ import annotations

from typing import Any

from trust_evidence_layer.host.adapter_base import HostAdapter
from trust_evidence_layer.types import TrustEvidenceResponse


class OnyxHostAdapter(HostAdapter):
    """Thin adapter for Onyx ChatFullResponse objects."""

    def get_retrieved_evidence(self, host_context: dict[str, Any]) -> list[dict[str, Any]]:
        chat_result = host_context.get("chat_result")
        if chat_result is None:
            return []

        evidence: list[dict[str, Any]] = []

        top_documents = getattr(chat_result, "top_documents", []) or []
        for doc in top_documents:
            evidence.append(
                {
                    "id": getattr(doc, "document_id", None),
                    "title": getattr(doc, "semantic_identifier", None),
                    "uri": getattr(doc, "link", None),
                    "snippet": getattr(doc, "blurb", "") or "",
                    "origin": "INTERNAL",
                    "trust_level": "PRIMARY",
                    "confidence_weight": 0.95,
                    "jurisdiction": "US",
                    "data_classification": "INTERNAL",
                    "allowed_scopes": ["response_generation", "retrieval", "enforcement"],
                }
            )

        tool_calls = getattr(chat_result, "tool_calls", []) or []
        for call in tool_calls:
            tool_name = str(getattr(call, "tool_name", "") or "")
            for doc in (getattr(call, "search_docs", None) or []):
                evidence.append(
                    {
                        "id": getattr(doc, "document_id", None),
                        "title": getattr(doc, "semantic_identifier", None),
                        "uri": getattr(doc, "link", None),
                        "snippet": getattr(doc, "blurb", "") or "",
                        "origin": "TOOL",
                        "tool_name": tool_name,
                        "jurisdiction": "UNKNOWN",
                        "data_classification": "INTERNAL",
                        "allowed_scopes": ["response_generation", "retrieval"],
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
