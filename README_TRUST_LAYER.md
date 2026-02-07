# Trust Layer Add-on (v0.1)

Provides gated chat responses with evidence attribution, policy trace, and audit-pack references.

## Guarantees
- No raw model output is returned by trust endpoints.
- Stable response contract (`contract_version=1.0`).
- Audit references included in every response.

## Limitations
- Streaming endpoint runs in safe mode (processing events + final gated payload).
- RBAC is header-stub based (`X-Trust-Role`) for v0.1.
