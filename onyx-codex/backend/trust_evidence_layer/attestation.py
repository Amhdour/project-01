from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from trust_evidence_layer.registry import get_policy_change_log
from trust_evidence_layer.registry import get_policy_registry
from trust_evidence_layer.registry import get_system_behavior_claims
from trust_evidence_layer.risk_registry import as_dicts
from trust_evidence_layer.risk_registry import get_active_risks
from trust_evidence_layer.system_claims import as_dicts as system_claims_as_dicts


def generate_attestation_artifact(
    *,
    output_dir: str | Path,
    tests_executed: list[str],
) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "attestation_artifact.json"

    payload: dict[str, Any] = {
        "system_claims": system_claims_as_dicts(get_system_behavior_claims()),
        "policies": {
            policy_id: {
                "policy_id": definition.policy_id,
                "description": definition.description,
                "scope": definition.scope,
                "enforced_by": definition.enforced_by,
                "acceptance_tests": definition.acceptance_tests,
                "version": definition.version,
            }
            for policy_id, definition in get_policy_registry().items()
        },
        "policy_change_log": get_policy_change_log(),
        "risk_register": as_dicts(get_active_risks()),
        "tests_executed": tests_executed,
        "last_evaluation_timestamp": datetime.now(UTC).isoformat(),
    }

    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return target
