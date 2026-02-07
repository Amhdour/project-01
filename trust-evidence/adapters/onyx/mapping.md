# Onyx → Trust Evidence Sidecar Mapping

This document defines where to hook inside Onyx chat execution and what each hook emits through `adapters/onyx/adapter.py`.

## Trace propagation

1. Create a `trace_id` at request entry (first point where an incoming user query is accepted):
   - `trace_id = create_trace_id()`
2. Store the value in request context/state so nested calls (retrieval/tool/policy/finalization) can read it.
3. Reuse that same `trace_id` for **every** emitted event for the turn.
4. Include `trace_id` in downstream logs/telemetry where possible to correlate host and sidecar evidence.

## Shared/common fields

Each `emit_event(...)` call should include these `common_fields`:

- `trace_id`: stable per user turn
- `span_id`: current operation id (turn/retrieval/tool/citation/final)
- `parent_span_id`: parent operation id or `null`
- `ts`: UTC RFC3339 timestamp (`...Z`)
- `host`: `onyx`
- `host_version`: current Onyx build/version
- `session_id`: chat/session id
- `user_id`: authenticated user id (or service principal)
- `schema_version`: `1.0.0` (defaulted by adapter if omitted)

## Hook placement and payloads

## 1) Turn start
- **Hook**: right after request validation and before retrieval/planning.
- **Event type**: `turn_start`
- **Payload fields**:
  - `turn_index` (int)
  - `query` (string)
  - `conversation_id` (string)

## 2) Retrieval batch
- **Hook**: after retriever returns documents, before rerank/filter.
- **Event type**: `retrieval_batch`
- **Payload fields**:
  - `batch_id` (string)
  - `documents` (array) where each item includes:
    - `doc_id`
    - `uri`
    - `score` (optional numeric)

## 3) Tool call
- **Hook**: immediately before tool execution.
- **Event type**: `tool_call`
- **Payload fields**:
  - `tool_name`
  - `arguments` (object; redact secrets)
  - `call_id`

## 4) Tool result
- **Hook**: immediately after tool execution returns.
- **Event type**: `tool_result`
- **Payload fields**:
  - `tool_name`
  - `call_id`
  - `status` (`ok`/`error`)
  - `output` (object/string; policy-safe subset)

## 5) Citations resolved
- **Hook**: after answer grounding/citation mapping is finalized.
- **Event type**: `citations_resolved`
- **Payload fields**:
  - `citations` (array), each containing:
    - `citation_id`
    - `doc_id`
    - `span_start` / `span_end` (optional)

## 6) Turn final
- **Hook**: just before response is returned to caller.
- **Event type**: `turn_final`
- **Payload fields**:
  - `response_id`
  - `latency_ms`
  - `token_usage` (object)
  - `finish_reason`

## Notes
- Adapter computes `payload_hash` using canonical JSON with sorted keys (same as sidecar integrity rules).
- `emit_event(...)` buffers events and sends to `/v1/events` in bounded batches with bounded retries.
- Call `flush_events()` at end-of-turn and in exception/finally paths to avoid leaving buffered events unsent.
