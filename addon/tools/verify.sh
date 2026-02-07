#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="addon:backend:${PYTHONPATH:-}"

echo "[1/4] Running addon-scoped pytest suite"
python -m pytest -q backend/tests/addon

echo "[2/4] Running minimal import checks"
python - <<'PY'
import importlib

modules = [
    "trust_evidence_addon",
    "trust_evidence_addon.api",
    "trust_evidence_addon.auth.jwt_auth",
    "trust_evidence_addon.config",
    "trust_evidence_addon.service",
    "trust_evidence_addon.store.filesystem",
    "trust_evidence_addon.store.postgres",
]
for name in modules:
    importlib.import_module(name)
print("OK: imports succeeded")
PY

echo "[3/4] Running config sanity checks (env or defaults)"
python - <<'PY'
import os
import sys
from trust_evidence_addon.config import AddonConfig

cfg = AddonConfig.from_env()
errors = []
notes = []

if cfg.store_backend not in {"filesystem", "postgres"}:
    errors.append(f"TRUST_STORE_BACKEND must be filesystem|postgres, got: {cfg.store_backend!r}")

if cfg.retention_days <= 0:
    errors.append(f"TRUST_RETENTION_DAYS must be > 0, got: {cfg.retention_days}")

if cfg.store_backend == "postgres" and not cfg.postgres_dsn:
    errors.append("TRUST_STORE_POSTGRES_DSN must be set when TRUST_STORE_BACKEND=postgres")

if cfg.store_backend == "filesystem" and not cfg.filesystem_dir:
    errors.append("TRUST_STORE_FILESYSTEM_DIR resolved to empty value")

if not cfg.jwt_issuer:
    errors.append("TRUST_JWT_ISSUER resolved to empty value")
if not cfg.jwt_audience:
    errors.append("TRUST_JWT_AUDIENCE resolved to empty value")
if not cfg.jwt_hs256_secret:
    notes.append("TRUST_JWT_HS256_SECRET is not set (required for authenticated runtime requests)")

if cfg.jwks_url:
    notes.append(f"TRUST_JWKS_URL configured: {cfg.jwks_url}")

print("Resolved config:")
print(f"- store_backend={cfg.store_backend}")
print(f"- retention_days={cfg.retention_days}")
print(f"- filesystem_dir={cfg.filesystem_dir}")
print(f"- postgres_dsn_set={bool(cfg.postgres_dsn)}")
print(f"- jwt_issuer={cfg.jwt_issuer}")
print(f"- jwt_audience={cfg.jwt_audience}")
print(f"- jwt_hs256_secret_set={bool(cfg.jwt_hs256_secret)}")
print(f"- jwks_url_set={bool(cfg.jwks_url)}")

for n in notes:
    print(f"NOTE: {n}")

if errors:
    for e in errors:
        print(f"ERROR: {e}")
    sys.exit(1)

print("OK: config sanity checks passed")
PY

echo "[4/4] Portable no-EE reference check (no ripgrep required)"
python - <<'PY'
from pathlib import Path

roots = [
    Path("addon/trust_evidence_addon"),
    Path("addon/patches"),
    Path("addon/docs"),
    Path("addon/deploy"),
    Path("addon/READY_TO_SELL_CHECKLIST.md"),
    Path("addon/pyproject.toml"),
]
patterns = ("backend/ee/", "web/.*/ee/")
violations = []

for root in roots:
    files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "backend/ee/" in text or "web/.*/ee/" in text:
            violations.append(str(f))

if violations:
    print("ERROR: EE content reference detected in addon artifacts:")
    for v in violations:
        print(f"- {v}")
    raise SystemExit(1)

print("OK: no EE content references detected in addon/")
PY

echo "verify.sh completed successfully"
