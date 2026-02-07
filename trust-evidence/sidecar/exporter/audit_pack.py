from __future__ import annotations

import json
import os
import uuid
import zipfile
from pathlib import Path
from typing import Any

from exporter.integrity import build_chain
from exporter.integrity import build_manifest
from store.repository import SidecarStore


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2)


def build_audit_pack(trace_id: str, store: SidecarStore, pack_id: str | None = None, packs_dir: str | None = None) -> tuple[str, Path]:
    target_dir = Path(packs_dir or os.getenv("TRUST_PACKS_DIR", ".trust_packs"))
    target_dir.mkdir(parents=True, exist_ok=True)

    pack_id = pack_id or f"pack_{trace_id}_{uuid.uuid4().hex[:10]}"
    zip_path = target_dir / f"{pack_id}.zip"

    summary = store.get_trace_summary(trace_id)
    events = store.get_events_for_trace(trace_id)

    manifest = build_manifest(events)
    chain_jsonl = build_chain(events)

    contract = {
        "trace_id": trace_id,
        "answer": "",
        "policy_summary": "",
        "evidence_status": summary.get("evidence_status", "none"),
        "warnings": ["v0.1 placeholder contract: host contract event unavailable"],
    }

    # Avoid leaking secrets: only persist event metadata + payloads already accepted by schema.
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("contract.json", _json_dumps(contract))

        evidence_lines = []
        for e in events:
            evidence_lines.append(
                json.dumps(
                    {
                        "id": e.get("id"),
                        "trace_id": e.get("trace_id"),
                        "span_id": e.get("span_id"),
                        "parent_span_id": e.get("parent_span_id"),
                        "ts": e.get("ts"),
                        "type": e.get("type"),
                        "payload": e.get("payload_json"),
                        "payload_hash": e.get("payload_hash"),
                        "schema_version": e.get("schema_version"),
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                )
            )
        zf.writestr("evidence/events.jsonl", "\n".join(evidence_lines) + ("\n" if evidence_lines else ""))

        retrieval_events = [e for e in events if e.get("type") == "retrieval_batch"]
        zf.writestr("retrieval/retrieval_events.json", _json_dumps(retrieval_events))

        tool_events = [e for e in events if e.get("type") in {"tool_call", "tool_result"}]
        zf.writestr("tools/tool_events.json", _json_dumps(tool_events))

        citations = [
            e.get("payload_json", {}).get("citations", [])
            for e in events
            if e.get("type") == "citations_resolved"
        ]
        flat_citations = [c for sub in citations for c in sub]
        zf.writestr("citations.json", _json_dumps(flat_citations))

        policy_events = [e for e in events if e.get("type") == "policy_decision"]
        zf.writestr("policy.json", _json_dumps(policy_events))

        zf.writestr("integrity/manifest.json", _json_dumps(manifest))
        zf.writestr("integrity/chain.jsonl", chain_jsonl)

    return pack_id, zip_path
