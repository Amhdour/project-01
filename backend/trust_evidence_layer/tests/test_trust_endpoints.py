import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from onyx.chat.models import MessageResponseIDInfo
from onyx.server.query_and_chat.models import MessageOrigin
from onyx.server.query_and_chat.models import SendMessageRequest
from onyx.server.query_and_chat.placement import Placement
from onyx.server.query_and_chat.streaming_models import AgentResponseDelta
from onyx.server.query_and_chat.streaming_models import AgentResponseStart
from onyx.server.query_and_chat.streaming_models import Packet
from onyx.server.trust_api import _require_audit_role
from onyx.server.trust_api import trust_send_chat_message
from onyx.server.trust_api import trust_stream_chat_message


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
    )

    chunks = list(response.body_iterator)
    body = "".join(chunks)
    assert '"type": "processing"' in body
    assert '"type": "final"' in body
    assert "message_delta" not in body


def test_audit_pack_endpoint_rbac():
    with pytest.raises(HTTPException):
        _require_audit_role("viewer")
