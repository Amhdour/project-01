# Install Onyx Trust Add-on

## Enable
Routes are included in API server startup from `onyx.main`.

## Env vars
- `TRUST_EVIDENCE_STORE_DIR` (default: `.trust_evidence`)
- `TRUST_EVIDENCE_AUDIT_OUTPUT_DIR` (optional audit export directory)

## Example policy bundle
Use `backend/trust_evidence_layer/fixtures/policy_bundle.json`.

## CLI
- `python -m trust_evidence_layer.cli validate-policy <bundle.json>`
- `python -m trust_evidence_layer.cli dry-run --input <fixture.json> --policy <bundle.json>`
