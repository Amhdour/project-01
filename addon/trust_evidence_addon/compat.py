from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_ONYX_RANGE = ">=0.0.0,<2.0.0"  # v0.1 placeholder range


@dataclass(frozen=True)
class CompatStatus:
    onyx_version: str | None
    supported: bool
    reason: str


def get_onyx_version() -> str | None:
    try:
        from onyx import __version__  # type: ignore

        return str(__version__)
    except Exception:
        return None


def check_compat() -> CompatStatus:
    v = get_onyx_version()
    if v is None:
        return CompatStatus(None, False, "Onyx version unavailable")

    major = int(v.split(".")[0]) if v.split(".")[0].isdigit() else 999
    if major >= 2:
        return CompatStatus(v, False, "Unsupported Onyx major version")
    return CompatStatus(v, True, "Supported")
