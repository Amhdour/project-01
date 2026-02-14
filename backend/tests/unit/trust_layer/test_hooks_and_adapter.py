from __future__ import annotations

import importlib
import sys
import types

from trust_layer.events import TrustContext
from trust_layer.events import TrustEvent
from trust_layer.hook_utils import run_trust_hook_safe
from trust_layer.interface import TrustLayer


class RecorderLayer(TrustLayer):
    def __init__(self) -> None:
        self.calls: list[tuple[TrustEvent, dict]] = []

    def hook(self, event: TrustEvent, ctx: TrustContext, payload: object) -> object:
        assert ctx.request_id == "req-1"
        assert isinstance(payload, dict)
        self.calls.append((event, payload))
        return payload


def test_hooks_run_in_expected_order_and_receive_payloads() -> None:
    layer = RecorderLayer()
    ctx = TrustContext(request_id="req-1")

    events = [
        TrustEvent.BEFORE_RETRIEVAL,
        TrustEvent.AFTER_RETRIEVAL,
        TrustEvent.BEFORE_GENERATION,
        TrustEvent.AFTER_GENERATION,
    ]

    for idx, event in enumerate(events):
        run_trust_hook_safe(
            layer=layer,
            event=event,
            ctx=ctx,
            payload={"stage": event.value, "idx": idx},
        )

    assert [event for event, _ in layer.calls] == events
    assert layer.calls[1][1]["stage"] == "AFTER_RETRIEVAL"
    assert layer.calls[3][1]["idx"] == 3


def test_hook_fail_open_returns_original_payload() -> None:
    class BrokenLayer(TrustLayer):
        def hook(self, event: TrustEvent, ctx: TrustContext, payload: object) -> object:
            raise RuntimeError("boom")

    payload = {"k": "v"}
    returned = run_trust_hook_safe(
        layer=BrokenLayer(),
        event=TrustEvent.BEFORE_GENERATION,
        ctx=TrustContext(request_id="req-1"),
        payload=payload,
    )
    assert returned is payload


def test_onyx_adapter_conversion_with_stubbed_onyx_modules() -> None:
    fake_search_models = types.ModuleType("onyx.context.search.models")
    fake_tools_models = types.ModuleType("onyx.tools.models")

    class FakeSearchDoc:
        def __init__(self) -> None:
            self.document_id = "doc-1"
            self.source_type = "FILE"
            self.link = "https://example.com/doc-1"
            self.chunk_ind = 7
            self.blurb = "important evidence"
            self.score = 0.91
            self.metadata = {"title": "Doc 1"}

    class FakeToolResponse:
        def __init__(self, search_docs: list[FakeSearchDoc]) -> None:
            self.rich_response = types.SimpleNamespace(search_docs=search_docs)

    fake_search_models.SearchDoc = FakeSearchDoc
    fake_tools_models.ToolResponse = FakeToolResponse

    sys.modules["onyx.context.search.models"] = fake_search_models
    sys.modules["onyx.tools.models"] = fake_tools_models

    adapter_mod = importlib.import_module("trust_layer.adapters.onyx_adapter")
    OnyxTrustAdapter = adapter_mod.OnyxTrustAdapter

    doc = FakeSearchDoc()
    trace = OnyxTrustAdapter.build_retrieval_trace(
        query="what is doc 1",
        filters={"source": "kb"},
        top_k=5,
        docs=[doc],
    )

    assert trace.query == "what is doc 1"
    assert trace.results[0].id == "doc-1"
    assert trace.results[0].chunk_id == "7"

    extracted = OnyxTrustAdapter.extract_search_docs([FakeToolResponse([doc])])
    assert len(extracted) == 1


def test_adapter_builds_deterministic_citation_to_evidence_map() -> None:
    fake_search_models = types.ModuleType("onyx.context.search.models")
    fake_tools_models = types.ModuleType("onyx.tools.models")
    fake_search_models.SearchDoc = object
    fake_tools_models.ToolResponse = object
    sys.modules["onyx.context.search.models"] = fake_search_models
    sys.modules["onyx.tools.models"] = fake_tools_models

    adapter_mod = importlib.import_module("trust_layer.adapters.onyx_adapter")
    OnyxTrustAdapter = adapter_mod.OnyxTrustAdapter

    citation_to_document_id = {1: "doc-A", 2: "doc-B", 3: "doc-A"}
    evidence_records = [
        {"id": 40, "document_id": "doc-A", "score": 0.51},
        {"id": 12, "document_id": "doc-A", "score": 0.92},
        {"id": 18, "document_id": "doc-B", "score": 0.81},
    ]

    mapped = OnyxTrustAdapter.build_citation_to_evidence_map(
        citation_to_document_id=citation_to_document_id,
        evidence_records=evidence_records,
    )

    assert mapped == {1: 12, 2: 18, 3: 12}
