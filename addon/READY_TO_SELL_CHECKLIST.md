# READY TO SELL v0.1 Checklist

- [ ] Run `addon/tools/verify_no_ee.sh`
- [ ] JWT authz validated for `trust:audit:read`
- [ ] Storage backend configured (filesystem or postgres)
- [ ] Retention enabled (`TRUST_RETENTION_DAYS`) and `trust-addon gc` tested
- [ ] Audit pack retrieval secured by claim-based authz
- [ ] Compatibility documented (`addon/docs/compatibility.md`)
- [ ] Deployment overlay validated (compose/helm skeleton)
