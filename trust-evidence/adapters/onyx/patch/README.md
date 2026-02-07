# Onyx patch scaffolding

## Minimal patch implementation (v0.1)

This repo patch emits trust evidence events from the real chat request path with minimal, isolated edits.

### Files touched
- `backend/onyx/server/query_and_chat/trust_sidecar.py`
  - tiny helper wrapper around `trust-evidence/adapters/onyx/adapter.py`
  - creates trace id, maps packet events, and emits sidecar events
  - applies fail-open/fail-closed behavior
- `backend/onyx/server/query_and_chat/chat_backend.py`
  - injects emitter on `/chat/send-message` and `/chat/send-chat-message`
  - wraps packet iterator to emit retrieval/tool/citation events
  - attaches `trace_id` to final response payload

### Emission control points
- `turn_start`: emitted at request entry before chat processing
- `retrieval_batch`: emitted on `search_tool_documents_delta` packets
- `tool_call`: emitted on tool start packets
- `tool_result`: emitted on tool result packets
- `citations_resolved`: emitted after gather completes from `citation_info`
- `turn_final`: emitted after final response object is assembled

### Config
- Sidecar endpoint/auth are adapter-driven (`TRUST_SIDECAR_URL`, `TRUST_INGEST_TOKEN` or `TRUST_JWT_SECRET`)
- Failure behavior:
  - `FAIL_OPEN=true` (default): log warning on sidecar failures, do not break chat response
  - `FAIL_OPEN=false`: raise emission errors (fail-closed)

### Compatibility statement format
Use this format in patch PR/release notes:

```text
Compatibility Statement:
- Onyx baseline: <git tag or commit>
- Adapter version: <version>
- Status: compatible | requires adjustment
- Notes: <breaking symbols/paths and mitigation>
```
