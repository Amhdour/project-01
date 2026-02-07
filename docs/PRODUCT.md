# Trust & Evidence Sidecar + Onyx Adapter (v0.1 Skeleton)

## Product Summary
Trust & Evidence ships as:
- **Sidecar service**: receives trace events, stores evidence, and produces audit packs.
- **Onyx adapter**: host integration layer that forwards structured trace events and contract-safe outputs.

## v0.1 Scope Checklist
- [x] Sidecar/adapter architecture documented.
- [x] Trace model includes stable `trace_id` per request lifecycle.
- [x] Audit pack concept defined (portable zip artifact with manifest + events).
- [x] Auth scopes defined for retrieval and write operations.
- [ ] Business logic implementation (deferred beyond skeleton).

## Core Concepts
- **trace_id guarantee**: every audited interaction has a unique `trace_id`, propagated from adapter to sidecar and used as the immutable join key for exports.
- **Audit pack**: tamper-evident bundle for compliance/review including manifest, events, and metadata snapshots.
- **Auth scopes**:
  - `trust:gate:write` for event/trace write operations.
  - `trust:audit:read` for audit pack retrieval.
