from __future__ import annotations

from pathlib import Path
from typing import Any

from trust_evidence_layer.registry import get_default_exporter
from trust_evidence_layer.registry import get_default_store
from trust_evidence_layer.registry import get_policy_registry
from trust_evidence_layer.registry import get_system_behavior_claims
from trust_evidence_layer.replay import replay
from trust_evidence_layer.system_claims import as_dicts


def evaluator_replay(trace_id: str) -> dict[str, Any]:
    return replay(trace_id, get_default_store())


def evaluator_export_audit_pack(trace_id: str, output_dir: str | Path | None = None) -> Path:
    return get_default_exporter().export_audit_pack(trace_id=trace_id, output_dir=output_dir)


def evaluator_policy_registry() -> dict[str, Any]:
    return {
        key: {
            "policy_id": val.policy_id,
            "description": val.description,
            "scope": val.scope,
            "version": val.version,
            "acceptance_tests": val.acceptance_tests,
            "enforced_by": val.enforced_by,
        }
        for key, val in get_policy_registry().items()
    }


def evaluator_system_claims() -> list[dict[str, Any]]:
    return as_dicts(get_system_behavior_claims())
