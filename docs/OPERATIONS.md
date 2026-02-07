# Operations (v0.1 Skeleton)

## Runtime Components
- `trust-evidence/sidecar/*`: sidecar service workspace.
- `trust-evidence/adapters/onyx/*`: host adapter patch workspace.
- `trust-evidence/deploy/*`: sidecar deployment assets.

## Operational Checklist
- [x] Environment template present (`deploy/.env.example`).
- [x] Verification entrypoint available (`make verify`).
- [x] Compatibility command/runtime warnings planned in adapter.
- [ ] SLO dashboards and alert routing (future).

## Standard Runbook (Placeholder)
1. Populate environment from `deploy/.env.example`.
2. Run `make verify` before deployment promotion.
3. Deploy adapter + sidecar together.
4. Validate audit pack retrieval and trace_id correlation.
