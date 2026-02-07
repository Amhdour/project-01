from __future__ import annotations

from typing import Any

_STATE: dict[str, Any] = {
    "mode": None,  # SYSTEM_HALT | DOMAIN_HALT | CLAIM_TYPE_HALT
    "domain": None,
    "claim_type": None,
    "reason": None,
}


def activate_kill_switch(
    mode: str,
    *,
    reason: str,
    domain: str | None = None,
    claim_type: str | None = None,
) -> None:
    _STATE.update(
        {
            "mode": mode,
            "reason": reason,
            "domain": domain,
            "claim_type": claim_type,
        }
    )


def clear_kill_switch() -> None:
    _STATE.update({"mode": None, "domain": None, "claim_type": None, "reason": None})


def current_kill_switch_state() -> dict[str, Any]:
    return dict(_STATE)


def should_halt(*, domain: str | None, claim_types: list[str]) -> tuple[bool, str | None]:
    mode = _STATE.get("mode")
    reason = _STATE.get("reason")
    if mode == "SYSTEM_HALT":
        return True, reason or "system halt active"
    if mode == "DOMAIN_HALT" and _STATE.get("domain") and domain == _STATE.get("domain"):
        return True, reason or "domain halt active"
    if mode == "CLAIM_TYPE_HALT" and _STATE.get("claim_type") in claim_types:
        return True, reason or "claim type halt active"
    return False, None
