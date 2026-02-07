from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any

from trust_evidence_layer.types import TrustEvidenceResponse


class HostAdapter(ABC):
    @abstractmethod
    def get_retrieved_evidence(self, host_context: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_draft_answer(self, host_context: dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def set_final_response(self, host_context: dict[str, Any], response: TrustEvidenceResponse) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_request_metadata(self, host_context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
