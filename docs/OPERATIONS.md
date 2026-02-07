# Operations (v0.1 Skeleton)

## Runtime Components
- `trust-evidence/sidecar/*`: sidecar service workspace.
- `trust-evidence/adapters/onyx/*`: host adapter patch workspace.
- `trust-evidence/deploy/*`: sidecar deployment assets.

## Operational Checklist
- [x] Environment template present (`deploy/.env.example`).
- [x] Verification entrypoint available (`make verify`).
- [x] Compatibility command/runtime warnings planned in adapter.
- [x] Retention + legal hold controls documented.
- [ ] SLO dashboards and alert routing (future).

## Standard Runbook (Placeholder)
1. Populate environment from `deploy/.env.example`.
2. Run `make verify` before deployment promotion.
3. Deploy adapter + sidecar together.
4. Validate audit pack retrieval and trace_id correlation.

## Retention & Legal Hold
- Runtime retention fields:
  - `traces.retention_until` (nullable)
  - `traces.legal_hold` (bool)
  - `audit_packs.retention_until` (nullable)
  - `audit_packs.legal_hold` (bool)
- Retention job:
  - Python entrypoint: `python -m app.retention --retention-days 30`
  - Deletes expired traces/packs unless legal hold is active or `retention_until` is in the future.
- Admin legal hold controls (scope: `trust:admin`):
  - `POST /v1/admin/traces/{trace_id}/legal-hold`
  - `DELETE /v1/admin/traces/{trace_id}/legal-hold`
- Admin retention trigger (scope: `trust:admin`):
  - `POST /v1/admin/retention/run`
