# Trust & Evidence Architecture Layer

Strict user-facing contract (unchanged):

```json
{
  "answer_text": "...",
  "evidence_bundle_user": {...},
  "decision_record": {...},
  "trace_id": "..."
}
```

## Regulated-industry guarantees
- Fail-closed enforcement for unsupported, non-compliant, and sovereignty-violating claims.
- Deterministic jurisdiction filtering with refusal semantics.
- Deterministic PII redaction for user-visible outputs and narratives.
- Policy-in-code with versioned evaluation traces.
- Residual risk binding and audit snapshots.
- Kill-switch refusal semantics (system/domain/claim-type halt).
- Independent evaluator hooks and attestation artifacts.

## Jurisdiction & data boundary enforcement
- `EvidenceSource` now includes:
  - `jurisdiction` (`EU|US|UK|CA|UNKNOWN`)
  - `data_classification` (`PUBLIC|INTERNAL|CONFIDENTIAL|REGULATED`)
  - `allowed_scopes` (`list[str]`)
- Evidence outside allowed jurisdictions/scope is rejected from claim support.
- Any jurisdiction violation causes explicit `REFUSE` with auditable reason.
- Audit packs include `jurisdiction_compliance.json` and narrative section "Jurisdiction Compliance".

## Risk acceptance & kill-switch semantics
- Residual risks are explicit in `risk_registry.py` and bound into `decision_record.risk_references`.
- Audit packs include `risk_register_snapshot.json`.
- Kill-switch modes:
  - `SYSTEM_HALT`
  - `DOMAIN_HALT`
  - `CLAIM_TYPE_HALT`
- Active kill-switch forces explicit refusal and is persisted in trace context.
- Configured incidents can auto-trigger kill-switch (e.g., bypass attempt).

## Independent evaluation model
- Read-only evaluator hooks:
  - replay(trace_id)
  - audit pack export
  - policy registry snapshot
  - system claims snapshot
- Attestation artifact includes:
  - system claims
  - policy registry + version change log
  - risk register
  - tests executed
  - evaluation timestamp
- Audit packs include `attestation_artifact.json`.

## Core modules
- `gate.py`: orchestration and fail-closed output enforcement.
- `sovereignty.py`: jurisdiction and scope enforcement.
- `redaction.py`: deterministic PII detection/redaction.
- `policy_registry.py`: versioned policy definitions.
- `risk_registry.py`: residual risk register and binding.
- `kill_switch.py`: halt semantics.
- `incidents.py`: incident classification + optional auto-halt trigger.
- `replay.py`: decision-equivalent replay.
- `audit_pack.py`: regulator-ready audit artifacts and chain-of-custody narrative.
- `attestation.py` / `evaluator.py`: independent attestation and read-only evaluation hooks.
