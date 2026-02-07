# Trust & Evidence Layer Ship Gate v0.1 Plan

## Checklist
- [x] Non-stream gated endpoint: `/trust/send-chat-message`
- [x] Stream gated endpoint: `/trust/stream-chat-message` (safe-mode processing + final gated packet)
- [x] Versioned response contract fields added
- [x] Policy bundle schema + CLI validation/dry-run
- [x] Audit pack retrieval endpoint with RBAC header guard
- [x] Unit + integration tests for policy and endpoints
- [x] Golden fixtures for request/response

## Commands
- Unit tests:
  - `pytest -q backend/trust_evidence_layer/tests/test_policy_bundle_cli.py`
  - `pytest -q backend/trust_evidence_layer/tests/test_serialization_order.py backend/trust_evidence_layer/tests/test_error_contract_shape.py`
- Integration-ish endpoint tests:
  - `pytest -q backend/trust_evidence_layer/tests/test_trust_endpoints.py`
- Demo CLI:
  - `python -m trust_evidence_layer.cli validate-policy backend/trust_evidence_layer/fixtures/policy_bundle.json`
  - `python -m trust_evidence_layer.cli dry-run --input backend/trust_evidence_layer/fixtures/dry_run_input.json --policy backend/trust_evidence_layer/fixtures/policy_bundle.json`
- Demo curl (assuming API prefix `/api`):
  - `curl -X POST http://localhost:8080/api/trust/send-chat-message -H 'Content-Type: application/json' -d @backend/trust_evidence_layer/fixtures/request_non_stream.json`
  - `curl -N -X POST http://localhost:8080/api/trust/stream-chat-message -H 'Content-Type: application/json' -d '{"message":"hi","stream":true}'`
