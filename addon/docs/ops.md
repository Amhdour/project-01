# Operations

## Key env vars
- `TRUST_STORE_BACKEND=filesystem|postgres`
- `TRUST_STORE_FILESYSTEM_DIR`
- `TRUST_STORE_POSTGRES_DSN`
- `TRUST_RETENTION_DAYS`
- `TRUST_ENCRYPTION_KEY`
- `TRUST_JWT_ISSUER`, `TRUST_JWT_AUDIENCE`, `TRUST_JWT_HS256_SECRET`, `TRUST_JWKS_URL`

## Incident mode
- Set `TRUST_EVIDENCE_MODE=observe` to avoid response mutation while preserving audit.
