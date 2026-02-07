# Security (v0.1 Skeleton)

## Security Goals
- Ensure only authorized principals can write trust events and read audit packs.
- Maintain trace integrity and evidence provenance across adapter and sidecar.

## Security Checklist
- [x] JWT/Bearer auth model with explicit scopes.
- [x] Principle of least privilege (`trust:ingest`, `trust:read`, `trust:export`, `trust:admin`).
- [x] Tamper-evidence target for stored/exported events.
- [x] No raw filesystem path exposure in download APIs.
- [x] Retention protected by legal hold controls.
- [ ] Key rotation + KMS integration (future).

## Scope Definitions
- `trust:ingest`: create/update traces and append sidecar events.
- `trust:read`: read trace summaries and download audit packs.
- `trust:export`: trigger audit pack exports.
- `trust:admin`: manage legal hold and run retention jobs.

## Threat Notes
- Breaking adapter/host symbols should trigger runtime compatibility warnings.
- Unsupported host versions must warn loudly in observe mode (non-fatal for v0.1).
- Retention logic must never delete records under legal hold.
