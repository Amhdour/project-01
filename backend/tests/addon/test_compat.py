from __future__ import annotations

from trust_evidence_addon.compat import check_compat


def test_compat_returns_status() -> None:
    status = check_compat()
    assert isinstance(status.supported, bool)
    assert isinstance(status.reason, str)
