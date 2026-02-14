from datetime import datetime

import pytest
from pydantic import ValidationError

from trust_layer.events import TrustContext
from trust_layer.events import TrustEvent
from trust_layer.interface import TrustLayer
from trust_layer.types import EvidenceItem
from trust_layer.types import GenerationTrace
from trust_layer.types import RetrievalTrace
from trust_layer.types import TrustReport


class PassthroughTrustLayer(TrustLayer):
    def hook(self, event: TrustEvent, ctx: TrustContext, payload: object) -> object:
        return {
            "event": event.value,
            "request_id": ctx.request_id,
            "payload": payload,
        }


def test_retrieval_trace_serialization_round_trip() -> None:
    trace = RetrievalTrace(
        query="where is policy x",
        filters={"source": "docs"},
        top_k=3,
        results=[
            EvidenceItem(
                id="doc-1",
                source="knowledge_base",
                uri="https://example.com/doc-1",
                chunk_id="chunk-7",
                text_span="policy x applies to...",
                score=0.88,
                metadata={"title": "Policy X"},
            )
        ],
    )

    payload = trace.model_dump(mode="json")
    restored = RetrievalTrace.model_validate(payload)

    assert restored.query == "where is policy x"
    assert restored.results[0].id == "doc-1"
    assert restored.results[0].metadata["title"] == "Policy X"


def test_trust_report_confidence_invariant() -> None:
    TrustReport(
        claims=["Claim A"],
        evidence_map={"claim-1": ["doc-1"]},
        warnings=[],
        confidence=0.75,
    )

    with pytest.raises(ValidationError):
        TrustReport(
            claims=["Claim B"],
            evidence_map={"claim-2": ["doc-2"]},
            warnings=[],
            confidence=1.5,
        )


def test_generation_trace_and_context_serialization() -> None:
    gen_trace = GenerationTrace(
        model="gpt-4.1",
        prompt_hash="sha256:abc123",
        safety_flags=["pii-filter"],
        output_hash="sha256:def456",
    )
    ctx = TrustContext(
        request_id="req-123",
        tenant_id="tenant-1",
        user_id="user-1",
        chat_session_id="chat-1",
        timestamps={"before_generation": datetime(2025, 1, 1, 12, 0, 0)},
        debug_flags={"trace_enabled": True},
    )

    assert gen_trace.model_dump()["model"] == "gpt-4.1"
    assert ctx.model_dump(mode="json")["debug_flags"]["trace_enabled"] is True


def test_trust_layer_hook_interface_minimal_contract() -> None:
    layer = PassthroughTrustLayer()
    ctx = TrustContext(request_id="req-hook")

    result = layer.hook(TrustEvent.BEFORE_RETRIEVAL, ctx, {"query": "hello"})

    assert result["event"] == "BEFORE_RETRIEVAL"
    assert result["request_id"] == "req-hook"
    assert result["payload"]["query"] == "hello"
