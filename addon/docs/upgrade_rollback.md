# Upgrade / Rollback

## Upgrade
1. Backup store.
2. Deploy new add-on package.
3. Run `trust-addon compat`.
4. Switch traffic.

## Rollback
1. Reinstall previous package.
2. Reapply previous patch set.
3. Validate retrieval + authz.
