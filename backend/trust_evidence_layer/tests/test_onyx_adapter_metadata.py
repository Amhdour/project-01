from types import SimpleNamespace

from trust_evidence_layer.host.onyx_adapter import OnyxHostAdapter


def test_adapter_sets_unknown_with_reason_when_metadata_missing() -> None:
    doc = SimpleNamespace(document_id="d1", semantic_identifier="Doc", link=None, blurb="b", metadata={})
    host_context = {"chat_result": SimpleNamespace(top_documents=[doc], tool_calls=[])}
    evidence = OnyxHostAdapter().get_retrieved_evidence(host_context)
    assert evidence[0]["jurisdiction"] == "UNKNOWN"
    assert evidence[0]["data_classification"] == "UNKNOWN"
    assert "unknown_reasons" in evidence[0]["provenance_gaps"]
