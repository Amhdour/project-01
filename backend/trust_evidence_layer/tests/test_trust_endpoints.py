import json
import zipfile
from contextlib import contextmanager
from types import SimpleNamespace

from onyx.chat.models import MessageResponseIDInfo
from onyx.server.query_and_chat.models import MessageOrigin
from onyx.server.query_and_chat.models import SendMessageRequest
from onyx.server.query_and_chat.placement import Placement
from onyx.server.query_and_chat.streaming_models import AgentResponseDelta
from onyx.server.query_and_chat.streaming_models import AgentResponseStart
from onyx.server.query_and_chat.streaming_models import Packet
from onyx.server.trust_api import get_audit_pack
from onyx.server.trust_api import trust_send_chat_message
from onyx.server.trust_api import trust_stream_chat_message
from trust_evidence_layer.storage.file_store import TraceFileStore


@contextmanager
def _fake_session():
    yield object()


def _fake_packets(*args, **kwargs):
    yield MessageResponseIDInfo(reserved_assistant_message_id=12)
    yield Packet(placement=Placement(turn_index=0), obj=AgentResponseStart(final_documents=[]))
    yield Packet(placement=Placement(turn_index=0), obj=AgentResponseDelta(content="raw model text"))


def test_non_stream_endpoint_gated(monkeypatch):
    import onyx.server.trust_api as trust_api

    monkeypatch.setattr(trust_api, "get_session_with_current_tenant", _fake_session)
    monkeypatch.setattr(trust_api, "handle_stream_message_objects", _fake_packets)

    payload = trust_send_chat_message(
        chat_message_req=SendMessageRequest(message="hi", stream=False),
        request=SimpleNamespace(headers={}, url=SimpleNamespace(path="/trust/send-chat-message")),
        user=None,
        _rate_limit_check=None,
        _api_key_usage_check=None,
        claims={"scope": "trust:gate:write"},
    )
    assert payload["contract_version"] == "1.0"
    assert "audit_pack_ref" in payload


def test_stream_endpoint_no_raw_delta(monkeypatch):
    import onyx.server.trust_api as trust_api

    monkeypatch.setattr(trust_api, "get_session_with_current_tenant", _fake_session)
    monkeypatch.setattr(trust_api, "handle_stream_message_objects", _fake_packets)

    response = trust_stream_chat_message(
        chat_message_req=SendMessageRequest(message="hi", stream=True, origin=MessageOrigin.API),
        request=SimpleNamespace(headers={}, url=SimpleNamespace(path="/trust/stream-chat-message")),
        user=None,
        _rate_limit_check=None,
        _api_key_usage_check=None,
        claims={"scope": "trust:gate:write"},
    )

    chunks = list(response.body_iterator)
    body = "".join(chunks)
    assert '"type": "processing"' in body
    assert '"type": "final"' in body
    assert "message_delta" not in body


def test_audit_pack_endpoint_downloads_zip(monkeypatch, tmp_path):
    import onyx.server.trust_api as trust_api

    trace_id = "trace-endpoint-zip"
    store = TraceFileStore(base_dir=tmp_path / "store")
    store.store(
        trace_id=trace_id,
        response_payload={
            "trace_id": trace_id,
            "answer_text": "safe answer",
            "decision_record": {
                "policy_checks": [],
                "claims": [],
                "evidence_links": [],
                "failure_modes": [],
                "incidents": [{"code": "TEST_INCIDENT", "severity": "low"}],
            },
            "evidence_bundle_user": {
                "sources": [{"id": "src1", "title": "doc", "snippet": "evidence"}],
                "retrieval_metadata": {"jurisdiction_compliance": {}},
            },
        },
        raw_context_minimal={"request_metadata": {"chat_session_id": "s1"}},
        replay_inputs={},
    )

    monkeypatch.setattr(trust_api, "get_default_store", lambda: store)
    monkeypatch.setenv("TRUST_EVIDENCE_AUDIT_OUTPUT_DIR", str(tmp_path / "audit_out"))

    response = get_audit_pack(trace_id=trace_id, claims={"scope": "trust:audit:read"})

    assert response.media_type == "application/zip"
    assert response.headers["content-disposition"] == f'attachment; filename="audit_pack_{trace_id}.zip"'

    with zipfile.ZipFile(response.path) as zf:
        names = set(zf.namelist())
        assert "manifest.json" in names
        assert "incident_events.json" in names

        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["trace_id"] == trace_id

        events = json.loads(zf.read("incident_events.json"))
        assert events[0]["code"] == "TEST_INCIDENT"
