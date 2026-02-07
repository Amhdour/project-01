# Security

- Authz is claim-based JWT (`trust:audit:read`, `trust:gate:write`).
- Header role stubs are not used by add-on endpoints.
- Optional encryption-at-rest for stored blobs/events via `TRUST_ENCRYPTION_KEY`.
- Retention enforced with `TRUST_RETENTION_DAYS` and `trust-addon gc`.

## JWT auth environment
- `TRUST_JWT_ISSUER`
- `TRUST_JWT_AUDIENCE`
- `TRUST_JWT_PUBLIC_KEY` (PEM public key; preferred for this v0.1 implementation)
- `TRUST_JWT_JWKS_URL` (reserved for future JWKS retrieval support)

Example scopes in token:
- `trust:audit:read` for audit retrieval
- `trust:gate:write` for trust send/stream operations
