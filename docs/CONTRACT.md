# Contract (v0.1 Skeleton)

## API Surface (Planned)
- Sidecar ingest endpoint(s) for trace events and trace finalization.
- Sidecar export endpoint(s) for audit pack download by `trace_id`.
- Onyx adapter boundary for mapping host request/response events to sidecar event schema.

## Contract Checklist
- [x] Trace correlation key: `trace_id`.
- [x] Event model fields include type, timestamp, payload, and ordering metadata.
- [x] Export contract includes manifest + event stream + artifact hashes.
- [x] Scope-based authorization model documented.
- [ ] Versioned API schemas enforced in runtime (future).

## Compatibility Notes
- Adapter must preserve host-visible response contract while appending audit metadata references.
- Contract changes must be reflected in `SCHEMA_VERSIONING.md` and `CHANGELOG.md`.
