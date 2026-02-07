from __future__ import annotations

import hashlib
from typing import Any

from trust_evidence_layer.host.adapter_base import HostAdapter
from trust_evidence_layer.types import TrustEvidenceResponse

CRITICAL_PROVENANCE_FIELDS = (
    "connector_id",
    "source_identifier",
    "jurisdiction",
    "data_classification",
)

# Central place for non-critical defaults used when host data does not provide richer values.
EVIDENCE_OPTIONAL_DEFAULTS: dict[str, Any] = {
    "origin_internal": "INTERNAL",
    "origin_tool": "TOOL",
    "trust_level_internal": "PRIMARY",
    "allowed_scopes_internal": ["response_generation", "retrieval", "enforcement"],
    "allowed_scopes_tool": ["response_generation", "retrieval"],
}


class OnyxHostAdapter(HostAdapter):
    """Thin adapter for Onyx ChatFullResponse objects."""

    @staticmethod
    def _stable_source_id(
        *,
        connector_id: str | None,
        source_identifier: str | None,
        uri: str | None,
    ) -> str:
        if source_identifier:
            return str(source_identifier)

        payload = (
            f"{connector_id or ''}|{source_identifier or ''}|{uri or ''}".encode(
                "utf-8", errors="ignore"
            )
        )
        digest = hashlib.sha256(payload).hexdigest()[:16]
        return f"derived:{digest}"

    @staticmethod
    def _extract_metadata(doc: Any) -> dict[str, Any]:
        metadata = getattr(doc, "metadata", {}) or {}

        connector_id = metadata.get("connector_id") or metadata.get("connector")
        source_identifier = getattr(doc, "document_id", None) or metadata.get("document_id")
        uri = getattr(doc, "link", None)
        jurisdiction = metadata.get("jurisdiction") or metadata.get("region")
        data_classification = metadata.get("data_classification") or metadata.get(
            "classification"
        )

        missing_fields: list[str] = []
        if not connector_id:
            missing_fields.append("connector_id")
        if not source_identifier:
            missing_fields.append("source_identifier")
        if not jurisdiction:
            missing_fields.append("jurisdiction")
        if not data_classification:
            missing_fields.append("data_classification")

        return {
            "connector_id": str(connector_id) if connector_id else None,
            "source_identifier": str(source_identifier) if source_identifier else None,
            "uri": uri,
            "jurisdiction": str(jurisdiction).upper() if jurisdiction else None,
            "data_classification": (
                str(data_classification).upper() if data_classification else None
            ),
            "missing_fields": missing_fields,
        }

    def _build_evidence_item(
        self,
        *,
        doc: Any,
        origin: str,
        tool_name: str | None = None,
    ) -> dict[str, Any]:
        extracted = self._extract_metadata(doc)
        source_id = self._stable_source_id(
            connector_id=extracted.get("connector_id"),
            source_identifier=extracted.get("source_identifier"),
            uri=extracted.get("uri"),
        )

        evidence = {
            "id": source_id,
            "title": getattr(doc, "semantic_identifier", None),
            "uri": extracted.get("uri"),
            "snippet": getattr(doc, "blurb", "") or "",
            "origin": origin,
            "jurisdiction": extracted.get("jurisdiction"),
            "data_classification": extracted.get("data_classification"),
            "allowed_scopes": (
                EVIDENCE_OPTIONAL_DEFAULTS["allowed_scopes_tool"]
                if origin == EVIDENCE_OPTIONAL_DEFAULTS["origin_tool"]
                else EVIDENCE_OPTIONAL_DEFAULTS["allowed_scopes_internal"]
            ),
            "provenance": {
                "connector_id": extracted.get("connector_id"),
                "source_identifier": extracted.get("source_identifier"),
                "missing_fields": extracted.get("missing_fields", []),
            },
        }

        if origin == EVIDENCE_OPTIONAL_DEFAULTS["origin_internal"]:
            evidence["trust_level"] = EVIDENCE_OPTIONAL_DEFAULTS["trust_level_internal"]

        if tool_name:
            evidence["tool_name"] = tool_name

        return evidence

    def get_retrieved_evidence(self, host_context: dict[str, Any]) -> list[dict[str, Any]]:
        chat_result = host_context.get("chat_result")
        if chat_result is None:
            return []

        evidence: list[dict[str, Any]] = []

        top_documents = getattr(chat_result, "top_documents", []) or []
        for doc in top_documents:
            evidence.append(
                self._build_evidence_item(
                    doc=doc,
                    origin=EVIDENCE_OPTIONAL_DEFAULTS["origin_internal"],
                )
            )

        tool_calls = getattr(chat_result, "tool_calls", []) or []
        for call in tool_calls:
            tool_name = str(getattr(call, "tool_name", "") or "")
            for doc in (getattr(call, "search_docs", None) or []):
                evidence.append(
                    self._build_evidence_item(
                        doc=doc,
                        origin=EVIDENCE_OPTIONAL_DEFAULTS["origin_tool"],
                        tool_name=tool_name,
                    )
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
