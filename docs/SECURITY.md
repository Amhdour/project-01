# Security (v0.1 Skeleton)

## Security Goals
- Ensure only authorized principals can write trust events and read audit packs.
- Maintain trace integrity and evidence provenance across adapter and sidecar.

## Security Checklist
- [x] JWT/Bearer auth model with explicit scopes.
- [x] Principle of least privilege (`trust:gate:write`, `trust:audit:read`).
- [x] Tamper-evidence target for stored/exported events.
- [x] No raw filesystem path exposure in download APIs.
- [ ] Key rotation + KMS integration (future).

## Scope Definitions
- `trust:gate:write`: create/update trace records and append sidecar events.
- `trust:audit:read`: download/export audit artifacts.

## Threat Notes
- Breaking adapter/host symbols should trigger runtime compatibility warnings.
- Unsupported host versions must warn loudly in observe mode (non-fatal for v0.1).
