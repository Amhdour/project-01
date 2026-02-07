from __future__ import annotations

import importlib
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Verified host window for this add-on line (v0.1.x):
# - lower bound: first integration commit in this repo for add-on host wiring
# - upper bound: latest validated commit when compatibility metadata was refreshed
SUPPORTED_ONYX_COMMIT_MIN = "cc467ab"
SUPPORTED_ONYX_COMMIT_MAX = "c445920"
SUPPORTED_ONYX_VERSION_LABELS = {"Development"}

# Runtime symbols relied on by v0.1 integration
REQUIRED_SYMBOLS = {
    "onyx.server.query_and_chat.chat_backend": [
        "_gate_host_response",
        "_build_contract_error_response",
        "extract_headers",
        "get_custom_tool_additional_request_headers",
    ],
    "onyx.server.query_and_chat.models": ["SendMessageRequest"],
}


@dataclass(frozen=True)
class CompatStatus:
    onyx_version: str | None
    onyx_commit: str | None
    supported: bool
    reason: str
    mode: str


def _git_short_commit(cwd: str | Path = ".") -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(cwd),
        )
        return proc.stdout.strip() or None
    except Exception:
        return None


def _hex_commit(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value.lower()[:7], 16)
    except Exception:
        return None


def get_onyx_version() -> str | None:
    try:
        from onyx import __version__  # type: ignore

        return str(__version__)
    except Exception:
        return None


def get_onyx_commit() -> str | None:
    # Prefer explicit runtime env when available
    env_commit = os.getenv("ONYX_GIT_COMMIT") or os.getenv("GIT_COMMIT")
    if env_commit:
        return env_commit[:7]

    # Fall back to local git checkout when running in source tree
    commit = _git_short_commit(Path(__file__).resolve().parents[2])
    if commit:
        return commit

    # Optional module metadata if set by host build
    try:
        import onyx  # type: ignore

        module_commit = getattr(onyx, "__commit__", None)
        if module_commit:
            return str(module_commit)[:7]
    except Exception:
        pass

    return None


def _required_symbols_present() -> tuple[bool, str]:
    for module_name, attrs in REQUIRED_SYMBOLS.items():
        try:
            module = importlib.import_module(module_name)
        except Exception as e:
            return False, f"Missing required module: {module_name} ({e})"
        for attr in attrs:
            if not hasattr(module, attr):
                return False, f"Missing required symbol: {module_name}.{attr}"
    return True, "Required runtime symbols present"


def check_compat() -> CompatStatus:
    version = get_onyx_version()
    commit = get_onyx_commit()
    mode = os.getenv("TRUST_EVIDENCE_MODE", "enforce").strip().lower() or "enforce"

    symbols_ok, symbols_reason = _required_symbols_present()
    if not symbols_ok:
        supported = False
        reason = symbols_reason
    else:
        min_hex = _hex_commit(SUPPORTED_ONYX_COMMIT_MIN)
        max_hex = _hex_commit(SUPPORTED_ONYX_COMMIT_MAX)
        cur_hex = _hex_commit(commit)

        commit_ok = cur_hex is not None and min_hex is not None and max_hex is not None and min_hex <= cur_hex <= max_hex
        version_ok = (version in SUPPORTED_ONYX_VERSION_LABELS) if version is not None else False

        if commit_ok:
            supported = True
            reason = f"Commit {commit} is within supported range {SUPPORTED_ONYX_COMMIT_MIN}..{SUPPORTED_ONYX_COMMIT_MAX}"
        elif version_ok:
            supported = True
            reason = f"Version label {version!r} is explicitly supported for source deployments"
        elif commit is None and version is None:
            supported = False
            reason = "Onyx version/commit unavailable"
        else:
            supported = False
            reason = (
                f"Host outside supported range: version={version or 'unknown'} commit={commit or 'unknown'} "
                f"expected commits {SUPPORTED_ONYX_COMMIT_MIN}..{SUPPORTED_ONYX_COMMIT_MAX}"
            )

    return CompatStatus(
        onyx_version=version,
        onyx_commit=commit,
        supported=supported,
        reason=reason,
        mode=mode,
    )


def log_runtime_compatibility(logger: logging.Logger | None = None) -> CompatStatus:
    logger = logger or logging.getLogger("trust_evidence_addon.compat")
    status = check_compat()

    logger.info(
        "Trust add-on host detection: onyx_version=%s onyx_commit=%s mode=%s",
        status.onyx_version or "unknown",
        status.onyx_commit or "unknown",
        status.mode,
    )

    if status.supported:
        logger.info("Trust add-on compatibility: supported (%s)", status.reason)
    else:
        logger.warning(
            "COMPATIBILITY WARNING: Trust add-on host appears unsupported (%s). "
            "In v0.1 observe mode this is non-fatal; verify patch compatibility before production use.",
            status.reason,
        )
    return status
