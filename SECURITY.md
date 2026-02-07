# Security Summary

## Threat Model (v0.1)
- Gate bypass attempts are treated as failures and forced into contract-safe error responses.
- No raw output can be returned from trust endpoints.

## Integrity
- Trace records are hash-bound for response/context/replay inputs.
- Audit packs include artifact hashes and manifest.

## Access Control
- Audit retrieval endpoint requires `X-Trust-Role: trust_auditor|trust_admin`.
- Header-based role check is a temporary replaceable stub for environments without auth context mapping.

## Key Handling
- Signing/attestation artifacts are optional; stronger key management is deferred to a later release.
