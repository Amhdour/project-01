from types import SimpleNamespace

from trust_evidence_layer.host.onyx_adapter import OnyxHostAdapter


def test_adapter_marks_missing_fields_when_metadata_absent() -> None:
    doc = SimpleNamespace(document_id=None, semantic_identifier="Doc", link=None, blurb="b", metadata={})
    host_context = {"chat_result": SimpleNamespace(top_documents=[doc], tool_calls=[])}
    evidence = OnyxHostAdapter().get_retrieved_evidence(host_context)

    assert evidence[0]["id"].startswith("derived:")
    assert evidence[0]["jurisdiction"] is None
    assert evidence[0]["data_classification"] is None
    assert set(evidence[0]["provenance"]["missing_fields"]) >= {
        "connector_id",
        "source_identifier",
        "jurisdiction",
        "data_classification",
    }


def test_adapter_uses_source_identifier_when_available() -> None:
    doc = SimpleNamespace(
        document_id="doc-123",
        semantic_identifier="Doc",
        link="https://example.local/doc-123",
        blurb="b",
        metadata={"connector_id": "conn-9", "jurisdiction": "eu", "data_classification": "restricted"},
    )
    host_context = {"chat_result": SimpleNamespace(top_documents=[doc], tool_calls=[])}
    evidence = OnyxHostAdapter().get_retrieved_evidence(host_context)

    assert evidence[0]["id"] == "doc-123"
    assert evidence[0]["jurisdiction"] == "EU"
    assert evidence[0]["data_classification"] == "RESTRICTED"
    assert evidence[0]["provenance"]["missing_fields"] == []
