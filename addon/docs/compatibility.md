# Compatibility Matrix

This add-on line (`trust_evidence_addon` v0.1.x) is validated against the host wiring in this repository.

## Supported host range (tested)

| Add-on Version | Supported Onyx Host Commits | Version Label(s) | Adapter |
|---|---|---|---|
| 0.1.x | `cc467ab` .. `c445920` (inclusive, short SHA) | `Development` (source checkout builds) | onyx host adapter v0.1 |

Notes:
- Commit-based checks are preferred when `ONYX_GIT_COMMIT` / `GIT_COMMIT` is available.
- In source-tree deployments where `onyx.__version__ == "Development"`, v0.1 treats this label as supported.

## Known-breaking change indicators and detection

The add-on depends on specific host modules/symbols. Compatibility is considered broken if any are missing:

- `onyx.server.query_and_chat.chat_backend._gate_host_response`
- `onyx.server.query_and_chat.chat_backend._build_contract_error_response`
- `onyx.server.query_and_chat.chat_backend.extract_headers`
- `onyx.server.query_and_chat.chat_backend.get_custom_tool_additional_request_headers`
- `onyx.server.query_and_chat.models.SendMessageRequest`

If these symbols move/rename, runtime compatibility logs will warn loudly.

## Runtime behavior

On startup/import, the add-on logs:
- detected `onyx_version`
- detected `onyx_commit` (when available)
- whether host is supported

If unsupported, v0.1 emits a loud warning but does **not** crash in observe mode.

You can also query status manually:

```bash
trust-addon compat
```
