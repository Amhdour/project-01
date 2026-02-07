# Upgrade

1. Backup store.
2. Deploy new add-on package.
3. Run compatibility + verification checks:
   - `trust-addon compat`
   - `./addon/tools/verify.sh` (or `make verify`)
4. Switch traffic.

## Rollback quick note
If rollback is required, reinstall the previous package and previous patch set, then run `./addon/tools/verify.sh` to confirm a healthy state.

See also: `addon/docs/upgrade_rollback.md`.
