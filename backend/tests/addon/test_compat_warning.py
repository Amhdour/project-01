from __future__ import annotations

import logging

from trust_evidence_addon.compat import log_runtime_compatibility


def test_runtime_compatibility_logs_warning_when_unsupported(monkeypatch, caplog) -> None:
    monkeypatch.setenv("TRUST_EVIDENCE_MODE", "observe")
    monkeypatch.setattr("trust_evidence_addon.compat.get_onyx_version", lambda: "9.9.9")
    monkeypatch.setattr("trust_evidence_addon.compat.get_onyx_commit", lambda: "fffffff")
    monkeypatch.setattr(
        "trust_evidence_addon.compat._required_symbols_present",
        lambda: (True, "Required runtime symbols present"),
    )

    with caplog.at_level(logging.INFO):
        status = log_runtime_compatibility()

    assert status.supported is False
    assert "COMPATIBILITY WARNING" in caplog.text
    assert "mode=observe" in caplog.text
