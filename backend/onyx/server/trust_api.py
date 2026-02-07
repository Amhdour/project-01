from __future__ import annotations

import json
import os
from types import SimpleNamespace

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse

from onyx.auth.users import current_chat_accessible_user
from onyx.chat.chat_state import ChatStateContainer
from onyx.chat.process_message import gather_stream_full
from onyx.chat.process_message import handle_stream_message_objects
from onyx.configs.constants import PUBLIC_API_TAGS
from onyx.configs.model_configs import LITELLM_PASS_THROUGH_HEADERS
from onyx.db.engine.sql_engine import get_session_with_current_tenant
from onyx.db.models import User
from onyx.server.api_key_usage import check_api_key_usage
from onyx.server.query_and_chat.chat_backend import _build_contract_error_response
from onyx.server.query_and_chat.chat_backend import _gate_host_response
from onyx.server.query_and_chat.chat_backend import extract_headers
from onyx.server.query_and_chat.chat_backend import get_custom_tool_additional_request_headers
from onyx.server.query_and_chat.models import SendMessageRequest
from onyx.server.query_and_chat.streaming_models import AgentResponseDelta
from onyx.server.query_and_chat.streaming_models import Packet
from onyx.server.query_and_chat.token_limit import check_token_rate_limits
from trust_evidence_layer.audit_pack import AuditPackExporter
from trust_evidence_layer.auth import REQUIRED_AUDIT_SCOPE
from trust_evidence_layer.auth import REQUIRED_GATE_SCOPE
from trust_evidence_layer.auth import claims_from_authorization_header
from trust_evidence_layer.auth import require_scope
from trust_evidence_layer.registry import get_default_store

router = APIRouter(prefix="/trust")


def _require_claim(
    required_scope: str,
    claims: dict,
) -> None:
    require_scope(claims, required_scope)


@router.post("/send-chat-message", response_model=None, tags=PUBLIC_API_TAGS)
def trust_send_chat_message(
    chat_message_req: SendMessageRequest,
    request: Request,
    user: User | None = Depends(current_chat_accessible_user),
    _rate_limit_check: None = Depends(check_token_rate_limits),
    _api_key_usage_check: None = Depends(check_api_key_usage),
    claims: dict = Depends(claims_from_authorization_header),
) -> dict:
    _require_claim(REQUIRED_GATE_SCOPE, claims)
    try:
        with get_session_with_current_tenant() as db_session:
            state_container = ChatStateContainer()
            packets = handle_stream_message_objects(
                new_msg_req=chat_message_req,
                user=user,
                db_session=db_session,
                litellm_additional_headers=extract_headers(
                    request.headers, LITELLM_PASS_THROUGH_HEADERS
                ),
                custom_tool_additional_headers=get_custom_tool_additional_request_headers(
                    request.headers
                ),
                mcp_headers=chat_message_req.mcp_headers,
                external_state_container=state_container,
            )
            result = gather_stream_full(packets, state_container)
            return _gate_host_response({"chat_result": result, "chat_message_req": chat_message_req})
    except Exception as e:
        return _build_contract_error_response(
            request=request,
            chat_session_id=str(chat_message_req.chat_session_id) if chat_message_req.chat_session_id else None,
            origin=chat_message_req.origin,
            failure_mode="TRUST_GATE_BYPASS_ATTEMPT" if "TRUST_GATE_BYPASS_ATTEMPT" in str(e) else "endpoint_error",
            error_message=f"Request failed: {str(e)}",
        )


@router.post("/stream-chat-message", response_model=None, tags=PUBLIC_API_TAGS)
def trust_stream_chat_message(
    chat_message_req: SendMessageRequest,
    request: Request,
    user: User | None = Depends(current_chat_accessible_user),
    _rate_limit_check: None = Depends(check_token_rate_limits),
    _api_key_usage_check: None = Depends(check_api_key_usage),
    claims: dict = Depends(claims_from_authorization_header),
) -> StreamingResponse:
    _require_claim(REQUIRED_GATE_SCOPE, claims)

    def event_stream():
        yield "data: " + json.dumps({"type": "processing", "status": "running"}) + "\n\n"
        try:
            with get_session_with_current_tenant() as db_session:
                state_container = ChatStateContainer()
                packets = handle_stream_message_objects(
                    new_msg_req=chat_message_req,
                    user=user,
                    db_session=db_session,
                    litellm_additional_headers=extract_headers(
                        request.headers, LITELLM_PASS_THROUGH_HEADERS
                    ),
                    custom_tool_additional_headers=get_custom_tool_additional_request_headers(
                        request.headers
                    ),
                    mcp_headers=chat_message_req.mcp_headers,
                    external_state_container=state_container,
                )
                raw_seen = False
                buffered = []
                for packet in packets:
                    buffered.append(packet)
                    if isinstance(packet, Packet) and isinstance(packet.obj, AgentResponseDelta) and packet.obj.content:
                        raw_seen = True
                if not raw_seen:
                    pass

                result = gather_stream_full(iter(buffered), state_container)
                payload = _gate_host_response({"chat_result": result, "chat_message_req": SimpleNamespace(stream=False, origin=chat_message_req.origin)})
                yield "data: " + json.dumps({"type": "final", "payload": payload}) + "\n\n"
                yield "data: " + json.dumps({"type": "done"}) + "\n\n"
        except Exception as e:
            payload = _build_contract_error_response(
                request=request,
                chat_session_id=str(chat_message_req.chat_session_id) if chat_message_req.chat_session_id else None,
                origin=chat_message_req.origin,
                failure_mode="TRUST_GATE_BYPASS_ATTEMPT" if "TRUST_GATE_BYPASS_ATTEMPT" in str(e) else "endpoint_error",
                error_message=f"Request failed: {str(e)}",
            )
            yield "data: " + json.dumps({"type": "final", "payload": payload}) + "\n\n"
            yield "data: " + json.dumps({"type": "done"}) + "\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/audit-packs/{trace_id}", tags=PUBLIC_API_TAGS)
def get_audit_pack(
    trace_id: str,
    claims: dict = Depends(claims_from_authorization_header),
) -> FileResponse:
    _require_claim(REQUIRED_AUDIT_SCOPE, claims)
    exporter = AuditPackExporter(get_default_store())
    output_dir = os.getenv("TRUST_EVIDENCE_AUDIT_OUTPUT_DIR")
    zip_path = exporter.export_audit_pack(trace_id, output_dir=output_dir)
    download_name = f"audit_pack_{trace_id}.zip"
    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=download_name,
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )
