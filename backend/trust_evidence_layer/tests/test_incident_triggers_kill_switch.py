from trust_evidence_layer.incidents import classify_incidents
from trust_evidence_layer.kill_switch import clear_kill_switch
from trust_evidence_layer.kill_switch import current_kill_switch_state


def test_incident_triggers_kill_switch() -> None:
    clear_kill_switch()
    classify_incidents(
        trace_id="t",
        failure_modes=["TRUST_GATE_BYPASS_ATTEMPT"],
        metrics={"pct_suppressed": 0.0},
        replay_consistent=True,
    )
    state = current_kill_switch_state()
    assert state["mode"] == "SYSTEM_HALT"
    clear_kill_switch()
