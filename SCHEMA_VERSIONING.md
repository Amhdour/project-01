# Schema Versioning Policy (v0.1)

## Principles
- Every externally consumed schema has an explicit `schema_version`.
- `trace_id` semantics are stable across minor revisions.
- Backward-incompatible changes require a major schema version bump.

## Checklist
- [x] Versioning policy documented.
- [x] Contract changes must update changelog and compatibility docs.
- [ ] Automated schema compatibility tests (future).

## Change Types
- **Patch**: clarifications/non-structural metadata additions.
- **Minor**: backward-compatible fields.
- **Major**: removed/renamed fields or semantic breaking behavior.
