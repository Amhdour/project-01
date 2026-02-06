from __future__ import annotations

import uuid


def generate_trace_id() -> str:
    return str(uuid.uuid4())
