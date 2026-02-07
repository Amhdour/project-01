# Trust Layer Add-on (v0.1)

Provides gated chat responses with evidence attribution, policy trace, and audit-pack references.

## Guarantees
- No raw model output is returned by trust endpoints.
- Stable response contract (`contract_version=1.0`).
- Audit references included in every response.

## Limitations
- Streaming endpoint runs in safe mode (processing events + final gated payload).
- RBAC is header-stub based (`X-Trust-Role`) for v0.1.

## Runtime Integration Controls
- `TRUST_EVIDENCE_ENABLED` (default: `false`)
- `TRUST_EVIDENCE_MODE` (default: `off`) with values:
  - `off`: trust gate is not called; Onyx host response is returned unchanged.
  - `observe`: trust gate runs for trust/audit artifact generation, but client response remains unchanged.
  - `enforce`: trust gate result is returned as a 4-key contract: `{final_answer, citations, trust, audit_pack_id}`.


## Streaming Compatibility Strategy
- `TRUST_EVIDENCE_ENFORCE_ON_STREAMING` (default: `false`).
- When `TRUST_EVIDENCE_MODE=enforce` and a streaming request is detected:
  - if this flag is `false`, behavior is downgraded to observe-only for compatibility: host/stream response remains unchanged, and trust/audit artifacts are still generated.
  - trust metadata records `streaming_enforcement_bypassed` and reason `streaming_enforce_disabled`.
  - if this flag is `true`, enforce behavior is applied.

## Evidence Metadata Provenance Policy
- Required provenance fields for audit-grade evidence: `connector_id`, `source_identifier`, `jurisdiction`, `data_classification`.
- The Onyx host adapter extracts these strictly from document/tool metadata when available.
- When missing, evidence records include `provenance.missing_fields` and deterministic fallback IDs (`derived:<hash>`).
- In enforce mode, missing critical provenance triggers trust refusal (`critical_provenance_missing`); observe mode records incomplete provenance without altering host responses.
