#!/usr/bin/env bash
set -euo pipefail

TARGETS=(addon/trust_evidence_addon addon/patches addon/docs addon/deploy addon/READY_TO_SELL_CHECKLIST.md addon/pyproject.toml)
if rg -n "backend/ee/|web/.*/ee/" "${TARGETS[@]}" >/dev/null; then
  echo "ERROR: EE content reference detected in addon artifacts"
  exit 1
fi

echo "OK: no EE content references detected in addon/"
