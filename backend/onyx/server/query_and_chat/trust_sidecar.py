from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from onyx.utils.logger import setup_logger

logger = setup_logger()


@dataclass
class TrustEventEmitter:
    trace_id: str
    session_id: str | None
    user_id: str | None
    _adapter: Any
    _span_counter: int = 0

    @classmethod
    def create(cls, session_id: str | None, user_id: str | None) -> "TrustEventEmitter":
        adapter = _load_adapter_module()
        trace_id = adapter.create_trace_id()
        return cls(trace_id=trace_id, session_id=session_id, user_id=user_id, _adapter=adapter)

    def emit_turn_start(self, message: str, turn_index: int = 0) -> None:
        self._emit(
            "turn_start",
            {
                "turn_index": turn_index,
                "query": message,
                "conversation_id": self.session_id,
            },
        )

    def on_packet(self, packet: Any) -> None:
        packet_type = getattr(packet.obj, "type", "")
        if packet_type == "search_tool_documents_delta":
            docs = []
            for d in getattr(packet.obj, "documents", []) or []:
                docs.append(
                    {
                        "doc_id": getattr(d, "document_id", None) or getattr(d, "id", ""),
                        "uri": getattr(d, "semantic_identifier", ""),
                        "score": getattr(d, "score", None),
                    }
                )
            self._emit("retrieval_batch", {"batch_id": f"rb_{self._span_counter}", "documents": docs})
            return

        if packet_type in {
            "search_tool_start",
            "open_url_start",
            "python_tool_start",
            "custom_tool_start",
            "image_generation_start",
        }:
            self._emit(
                "tool_call",
                {
                    "tool_name": _tool_name(packet.obj),
                    "arguments": _tool_arguments(packet.obj),
                    "call_id": f"call_{self._span_counter}",
                },
            )
            return

        if packet_type in {
            "open_url_documents",
            "python_tool_delta",
            "custom_tool_delta",
            "image_generation_final",
        }:
            self._emit(
                "tool_result",
                {
                    "tool_name": _tool_name(packet.obj),
                    "call_id": f"call_{self._span_counter}",
                    "status": "ok",
                    "output": _tool_result(packet.obj),
                },
            )

    def emit_citations_resolved(self, citations: list[Any]) -> None:
        citation_payload = []
        for idx, c in enumerate(citations, start=1):
            citation_payload.append(
                {
                    "citation_id": getattr(c, "citation_number", idx),
                    "doc_id": getattr(c, "document_id", ""),
                }
            )
        self._emit("citations_resolved", {"citations": citation_payload})

    def emit_turn_final(self, result: Any) -> None:
        self._emit(
            "turn_final",
            {
                "response_id": getattr(result, "message_id", None),
                "latency_ms": None,
                "token_usage": {},
                "finish_reason": "stop" if not getattr(result, "error_msg", None) else "error",
            },
        )
        self.flush()

    def flush(self) -> None:
        _safe_emit(self._adapter.flush_events)

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        self._span_counter += 1
        _safe_emit(
            self._adapter.emit_event,
            event_type,
            {
                "trace_id": self.trace_id,
                "span_id": f"sp_{self._span_counter}",
                "parent_span_id": None,
                "ts": datetime.utcnow().isoformat() + "Z",
                "host": "onyx",
                "host_version": os.getenv("ONYX_HOST_VERSION", os.getenv("GIT_COMMIT_SHA", "dev")),
                "session_id": self.session_id or "",
                "user_id": self.user_id or "anonymous",
            },
            payload,
        )


def _tool_name(packet_obj: Any) -> str:
    return getattr(packet_obj, "tool_name", None) or getattr(packet_obj, "type", "tool")


def _tool_arguments(packet_obj: Any) -> dict[str, Any]:
    if hasattr(packet_obj, "code"):
        return {"code": getattr(packet_obj, "code")}
    return {}


def _tool_result(packet_obj: Any) -> dict[str, Any] | str:
    if hasattr(packet_obj, "data"):
        return {"data": getattr(packet_obj, "data", None)}
    if hasattr(packet_obj, "stdout") or hasattr(packet_obj, "stderr"):
        return {
            "stdout": getattr(packet_obj, "stdout", ""),
            "stderr": getattr(packet_obj, "stderr", ""),
        }
    if hasattr(packet_obj, "documents"):
        return {"document_count": len(getattr(packet_obj, "documents") or [])}
    if hasattr(packet_obj, "images"):
        return {"image_count": len(getattr(packet_obj, "images") or [])}
    return "ok"


def _load_adapter_module() -> Any:
    repo_root = Path(__file__).resolve().parents[4]
    adapter_path = repo_root / "trust-evidence" / "adapters" / "onyx" / "adapter.py"
    spec = importlib.util.spec_from_file_location("trust_onyx_adapter", adapter_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load adapter from {adapter_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _safe_emit(func: Any, *args: Any, **kwargs: Any) -> Any:
    fail_open_raw = os.getenv("FAIL_OPEN", "true").lower()
    fail_open = fail_open_raw in {"1", "true", "yes", "on"}
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if fail_open:
            logger.warning(f"Trust sidecar emission failed (fail-open): {e}")
            return None
        raise
