# Security

- Authz is claim-based JWT (`trust:audit:read`, `trust:gate:write`).
- Header role stubs are not used by add-on endpoints.
- Optional encryption-at-rest for stored blobs/events via `TRUST_ENCRYPTION_KEY`.
- Retention enforced with `TRUST_RETENTION_DAYS` and `trust-addon gc`.
