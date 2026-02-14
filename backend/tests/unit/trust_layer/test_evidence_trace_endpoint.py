from __future__ import annotations

import importlib
import sys
import types
from uuid import uuid4

import pytest


def _install_stub_modules() -> None:
    auth_users_mod = types.ModuleType("onyx.auth.users")
    auth_users_mod.current_chat_accessible_user = lambda: None

    constants_mod = types.ModuleType("onyx.configs.constants")
    constants_mod.PUBLIC_API_TAGS = ["public"]

    db_chat_mod = types.ModuleType("onyx.db.chat")
    db_chat_mod.get_chat_message = lambda **kwargs: None

    db_evidence_mod = types.ModuleType("onyx.db.evidence")
    db_evidence_mod.get_citation_evidence_map_by_message_id = lambda **kwargs: {}
    db_evidence_mod.get_evidence_records_by_message_id = lambda **kwargs: []

    db_engine_mod = types.ModuleType("onyx.db.engine.sql_engine")
    db_engine_mod.get_session = lambda: None

    db_models_mod = types.ModuleType("onyx.db.models")

    class User:  # minimal stub
        def __init__(self, user_id: str | None = None) -> None:
            self.id = user_id

    db_models_mod.User = User

    context_mod = types.ModuleType("shared_configs.contextvars")
    context_mod.get_current_tenant_id = lambda: "tenant-1"

    sys.modules["onyx.auth.users"] = auth_users_mod
    sys.modules["onyx.configs.constants"] = constants_mod
    sys.modules["onyx.db.chat"] = db_chat_mod
    sys.modules["onyx.db.evidence"] = db_evidence_mod
    sys.modules["onyx.db.engine.sql_engine"] = db_engine_mod
    sys.modules["onyx.db.models"] = db_models_mod
    sys.modules["shared_configs.contextvars"] = context_mod


def test_evidence_trace_endpoint_returns_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_stub_modules()
    mod = importlib.import_module("onyx.server.query_and_chat.trust_backend")

    session_id = uuid4()
    parent = types.SimpleNamespace(message="what is policy x")
    chat_message = types.SimpleNamespace(
        chat_session_id=session_id,
        parent_message=parent,
    )
    evidence_record = types.SimpleNamespace(
        id=10,
        source_type="FILE",
        source_uri="https://example.com/policy",
        chunk_id="7",
        score=0.88,
        snippet="policy excerpt",
        metadata_json={"title": "Policy X"},
    )

    monkeypatch.setattr(mod, "get_chat_message", lambda **kwargs: chat_message)
    monkeypatch.setattr(
        mod,
        "get_evidence_records_by_message_id",
        lambda **kwargs: [evidence_record],
    )
    monkeypatch.setattr(
        mod,
        "get_citation_evidence_map_by_message_id",
        lambda **kwargs: {1: evidence_record},
    )
    monkeypatch.setattr(mod, "get_current_tenant_id", lambda: "tenant-test")

    user = types.SimpleNamespace(id="user-1")
    response = mod.get_evidence_trace(message_id=123, user=user, db_session=object())

    assert response.context.tenant_id == "tenant-test"
    assert str(response.context.chat_session_id) == str(session_id)
    assert response.retrieval_trace.query == "what is policy x"
    assert response.citation_map == {1: 10}
    assert response.evidence_items[0].score == 0.88


def test_evidence_trace_endpoint_denies_cross_user_or_tenant_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_stub_modules()
    mod = importlib.import_module("onyx.server.query_and_chat.trust_backend")

    def _raise_not_owned(**kwargs: object) -> None:
        raise ValueError("Chat message does not belong to user")

    monkeypatch.setattr(mod, "get_chat_message", _raise_not_owned)

    with pytest.raises(mod.HTTPException) as exc:
        mod.get_evidence_trace(
            message_id=123,
            user=types.SimpleNamespace(id="user-1"),
            db_session=object(),
        )

    assert exc.value.status_code == 404
