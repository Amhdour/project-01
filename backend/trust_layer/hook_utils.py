from __future__ import annotations

from typing import Any

from trust_layer.events import TrustContext
from trust_layer.events import TrustEvent
from trust_layer.interface import TrustLayer


def run_trust_hook_safe(
    *,
    layer: TrustLayer | None,
    event: TrustEvent,
    ctx: TrustContext,
    payload: Any,
    logger: Any | None = None,
) -> Any:
    if layer is None:
        return payload

    try:
        return layer.hook(event=event, ctx=ctx, payload=payload)
    except Exception:
        if logger is not None:
            logger.exception(f"Trust hook failed for event={event}; continuing fail-open")
        return payload
