from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import Any

from trust_evidence_layer.kill_switch import activate_kill_switch

_AUTO_KILL_SWITCH_INCIDENTS = {
    "TRUST_GATE_BYPASS_ATTEMPT": {"mode": "SYSTEM_HALT", "reason": "auto halt due to bypass attempt"},
}


def classify_incidents(
    *,
    trace_id: str,
    failure_modes: list[str],
    metrics: dict[str, Any],
    replay_consistent: bool,
) -> list[dict[str, Any]]:
    incidents: list[dict[str, Any]] = []

    if "no_supporting_evidence_found" in failure_modes:
        incidents.append(_event(trace_id, "EVIDENCE_FAILURE", "MEDIUM"))

    pct = float(metrics.get("pct_suppressed", 0.0) or 0.0)
    if pct >= 0.5:
        incidents.append(_event(trace_id, "HALLUCINATION_SPIKE", "HIGH"))

    if any("TRUST_GATE_BYPASS_ATTEMPT" in mode for mode in failure_modes):
        incidents.append(_event(trace_id, "TRUST_GATE_BYPASS_ATTEMPT", "CRITICAL"))

    if not replay_consistent:
        incidents.append(_event(trace_id, "REPLAY_INCONSISTENCY", "HIGH"))

    for incident in incidents:
        cfg = _AUTO_KILL_SWITCH_INCIDENTS.get(incident["incident_type"])
        if cfg:
            activate_kill_switch(cfg["mode"], reason=cfg["reason"])

    return incidents


def _event(trace_id: str, incident_type: str, severity: str) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "incident_type": incident_type,
        "severity": severity,
        "timestamp": datetime.now(UTC).isoformat(),
    }
