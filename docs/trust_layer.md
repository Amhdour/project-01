# Trust Layer: Portfolio Proof and Runbook

This document captures the trust/evidence additions in this repository with concrete code anchors, run commands, and verification requests.

## What was added

### 1) Pipeline interception hooks (4 points)
Hooks are integrated into the primary chat execution loop at:
- `BEFORE_RETRIEVAL`
- `AFTER_RETRIEVAL`
- `BEFORE_GENERATION`
- `AFTER_GENERATION`

Core contract and hook primitives:
- Portable contract types: `backend/trust_layer/types.py`
- Hook events/context: `backend/trust_layer/events.py`
- Trust interface: `backend/trust_layer/interface.py`
- Fail-open hook execution helper: `backend/trust_layer/hook_utils.py`

Primary pipeline wiring:
- `backend/onyx/chat/llm_loop.py`
- `backend/onyx/chat/trust_layer_utils.py`

Feature/config toggles:
- `TRUST_LAYER_HOOKS_ENABLED`
- `TRUST_LAYER_IMPL`
- `CITATION_ATTRIBUTION_ENABLED`

Defined in:
- `backend/onyx/configs/app_configs.py`

### 2) Evidence persistence
Added persistent storage for retrieval evidence and citation attribution.

DB models:
- `EvidenceRecord` in `backend/onyx/db/models.py` (`evidence_records`)
- `CitationEvidenceMap` in `backend/onyx/db/models.py` (`citation_evidence_map`)

DB helpers:
- `backend/onyx/db/evidence.py`
  - `persist_evidence_records(...)`
  - `get_evidence_records_by_message_id(...)`
  - citation mapping persistence/read helpers

Migrations:
- `backend/alembic/versions/9b31c2f4a7d1_add_evidence_records_table.py`
- `backend/alembic/versions/0c4e6f2d1a99_add_citation_evidence_map_table.py`

### 3) Citation attribution in chat response
Extended chat response (backward-compatible optional fields) to include attribution metadata and trust warnings/flags.

Response model and assembly:
- `backend/onyx/chat/models.py`
- `backend/onyx/chat/process_message.py`
- `backend/onyx/chat/chat_state.py`

### 4) Evidence trace export endpoint
Added endpoint:
- `GET /trust/evidence-trace?message_id=<UUID>`

Router/handler:
- `backend/onyx/server/query_and_chat/trust_backend.py`

Router registration:
- `backend/onyx/main.py`

Auth + tenant/user scoping follows existing chat-access patterns via current user + message ownership checks.

## How to run

From repository root:

```bash
# 1) Backend dependencies (example using existing environment conventions)
cd backend

# 2) Apply DB migrations
alembic upgrade head

# 3) Start backend service
python -m onyx.main
```

Optional trust-related environment flags:

```bash
export TRUST_LAYER_HOOKS_ENABLED=true
export TRUST_LAYER_IMPL=""  # leave empty for no-op default
export CITATION_ATTRIBUTION_ENABLED=true
```

## How to verify

> Note: if `API_PREFIX` is set, prepend it to all paths below.

### A) Send a chat message on primary route

```bash
curl -X POST "http://localhost:8080/chat/send-chat-message" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "chat_session_id": "<CHAT_SESSION_UUID>",
    "message": "Summarize policy X and cite sources"
  }'
```

Look for response fields (when enabled/available):
- `citations` (existing)
- `citation_attributions` (new optional)
- `hallucination_risk_flags` (new optional)
- `trust_warnings` (new optional)

Example JSON fragment:

```json
{
  "citations": [{"citation_num": 1}],
  "citation_attributions": [
    {
      "citation_number": 1,
      "evidence_record_id": 42,
      "source_title": "Policy Handbook",
      "source_url": "https://example.internal/policy",
      "snippet": "...relevant excerpt...",
      "score": 0.83
    }
  ],
  "hallucination_risk_flags": ["LOW_RETRIEVAL_SCORE"],
  "trust_warnings": ["Average retrieval score below threshold"]
}
```

### B) Export full evidence trace for a message

```bash
curl "http://localhost:8080/trust/evidence-trace?message_id=<MESSAGE_UUID>" \
  -H "Authorization: Bearer <TOKEN>"
```

Expected top-level JSON keys:
- `context`
- `retrieval_trace`
- `evidence_items`
- `citation_map`
- `trust_warnings`

Example JSON fragment:

```json
{
  "context": {
    "tenant_id": "<TENANT_UUID>",
    "user_id": "<USER_UUID>",
    "chat_session_id": "<CHAT_SESSION_UUID>",
    "message_id": "<MESSAGE_UUID>"
  },
  "retrieval_trace": {
    "query": "Summarize policy X",
    "top_k": 10
  },
  "evidence_items": [
    {
      "id": "ev-1",
      "source": "document",
      "uri": "https://example.internal/policy",
      "chunk_id": "chunk-17",
      "score": 0.83
    }
  ],
  "citation_map": {
    "1": 42
  },
  "trust_warnings": []
}
```

### C) Minimal automated checks

```bash
pytest -q backend/tests/unit/trust_layer/test_contract.py \
  backend/tests/unit/trust_layer/test_hooks_and_adapter.py \
  backend/tests/unit/trust_layer/test_risk.py \
  backend/tests/unit/trust_layer/test_evidence_trace_endpoint.py
```

## Files to read first (anchors)

1. `backend/onyx/chat/llm_loop.py`
   - Hook insertion points in the primary generation/retrieval loop.
2. `backend/onyx/db/evidence.py`
   - Evidence write/read + citation mapping persistence.
3. `backend/onyx/db/models.py`
   - `EvidenceRecord`, `CitationEvidenceMap` schema.
4. `backend/onyx/server/query_and_chat/trust_backend.py`
   - `GET /trust/evidence-trace` handler and response assembly.
5. `backend/onyx/chat/models.py`
   - Optional attribution/risk fields in chat response schema.
6. `backend/trust_layer/types.py`, `events.py`, `interface.py`, `risk.py`
   - Host-agnostic trust contract and risk heuristics.
7. `backend/alembic/versions/9b31c2f4a7d1_add_evidence_records_table.py`
   and `backend/alembic/versions/0c4e6f2d1a99_add_citation_evidence_map_table.py`
   - DB migration proof.
