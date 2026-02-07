# Install Trust Evidence Add-on

1. Install package from source:
   - `pip install ./addon`
2. Apply Onyx CE patch files (if needed):
   - `git apply addon/patches/onyx_chat_backend.patch`
   - `git apply addon/patches/onyx_trust_api.patch`
3. Configure env vars (minimum):
   - `TRUST_STORE_BACKEND=filesystem`
   - `TRUST_STORE_FILESYSTEM_DIR=.trust_evidence_addon`
   - `TRUST_JWT_ISSUER=...`
   - `TRUST_JWT_AUDIENCE=...`
   - `TRUST_JWT_HS256_SECRET=...`
4. Run verification:
   - `./addon/tools/verify.sh`
   - or `make verify`

The verification script is portable and does **not** require `rg`/ripgrep.
