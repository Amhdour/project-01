# Trust & Evidence Layer Reconnaissance (Onyx)

## Scope and method
- Scope inspected: chat request handling and LLM orchestration path under `backend/onyx/server/query_and_chat` and `backend/onyx/chat`.
- No business logic changes made; this is code-path reconnaissance only.

## 1) Exact request → retrieval → LLM → response flow

### Primary endpoint flow (`POST /chat/send-chat-message`)
1. HTTP request enters `handle_send_chat_message(...)` in `chat_backend.py`.
2. Endpoint chooses non-streaming (`stream=False`) or streaming (`stream=True`) behavior.
3. Both modes call `handle_stream_message_objects(...)` in `process_message.py`.
4. `handle_stream_message_objects(...)` resolves/creates chat session, persists user message (unless regeneration), constructs tools and context.
5. It builds simplified chat history and invokes `run_chat_loop_with_state_containers(...)` with either:
   - `run_llm_loop(...)` (standard chat), or
   - `run_deep_research_llm_loop(...)` (deep research mode).
6. In standard mode, `run_llm_loop(...)` repeatedly:
   - builds system/reminder prompts,
   - truncates/finalizes message history (`construct_message_history(...)`),
   - executes one model step via `run_llm_step(...)`,
   - executes any model-selected tools via `run_tool_calls(...)`.
7. `run_llm_step(...)` wraps `run_llm_step_pkt_generator(...)`, which calls `llm.stream(...)` with finalized prompt/history and tools.
8. Stream packets (`AgentResponseStart`, `AgentResponseDelta`, `CitationInfo`, tool packets, etc.) are emitted.
9. Completion callback `llm_loop_completion_handle(...)` persists final assistant message + citations via `save_chat_turn(...)`.
10. Return to client:
    - Streaming path: packets JSON-serialized and emitted in SSE.
    - Non-stream path: `gather_stream_full(...)` aggregates packets + state into `ChatFullResponse` and returns JSON response body.

### Retrieval/tool involvement in flow
- Retrieval is tool-driven through constructed tools in `construct_tools(...)` and executed in `run_tool_calls(...)` from `run_llm_loop(...)`.
- Search docs are surfaced as:
  - `final_documents` on `AgentResponseStart`,
  - `CitationInfo` packets with `citation_number` + `document_id`,
  - `ToolCallResponse.search_docs` in non-stream `ChatFullResponse`.

## 2) Requested locations in code

### A) Where user input is finalized before model invocation
- `run_llm_loop(...)` finalizes `truncated_message_history = construct_message_history(...)` before each LLM step.
- `run_llm_step_pkt_generator(...)` converts this to provider format via `translate_history_to_llm_format(...)` and calls `llm.stream(prompt=llm_msg_history, ...)`.

### B) Where retrieved documents/snippets are available
- `run_llm_loop(...)` tracks `gathered_documents` and passes them as `final_documents` into `run_llm_step(...)`.
- `run_llm_step_pkt_generator(...)` emits `AgentResponseStart(final_documents=...)`.
- Citation mapping is maintained in `DynamicCitationProcessor` and copied to `state_container` with `state_container.set_citation_mapping(...)`.
- Tool responses include search docs and are appended to state as `ToolCallInfo`, later transformed to response model.

### C) Where draft model answer is assembled
- `run_llm_step_pkt_generator(...)` accumulates `accumulated_answer` from `delta.content` (post citation processing) and writes incrementally to `state_container.set_answer_tokens(...)`.
- `gather_stream_full(...)` reconstructs final text via `state_container.get_answer_tokens() or answer`.

### D) Where final response object is returned
- Non-streaming: `handle_send_chat_message(...)` returns `result = gather_stream_full(...)` (`ChatFullResponse`).
- Streaming: `handle_send_chat_message(...)` yields `get_json_line(obj.model_dump())` through `StreamingResponse`.

## 3) Existing schemas, citation fields, middleware/hooks

### Response schemas/dicts currently returned
- Non-streaming response schema: `ChatFullResponse` with
  - `answer`, `answer_citationless`, `pre_answer_reasoning`, `tool_calls`,
  - `top_documents`, `citation_info`,
  - `message_id`, `chat_session_id`, `error_msg`.
- Streaming payload shape: serialized `Packet` objects (`obj.type` discriminators) and occasional raw `{"error": ...}` dict from endpoint exception handling.
- Legacy endpoint `/chat/send-message` streams only (deprecated).

### Existing citation/source fields
- `CitationInfo`: `citation_number`, `document_id`.
- `AgentResponseStart.final_documents: list[SearchDoc] | None`.
- `ChatFullResponse.top_documents: list[SearchDoc]`.
- `ToolCallResponse.search_docs: list[SearchDoc] | None`.
- Database save path builds `CitationDocInfo(search_doc, citation_number)` before `save_chat_turn(...)`.

### Middleware/hooks/extension points observed
- FastAPI app-level middleware: CORS, optional latency middleware, request-id middleware.
- Dependency hooks on chat endpoint: token rate limits, API key usage checks.
- Callback hook: `run_chat_loop_with_state_containers(..., completion_callback=...)`.
- Emission boundary: `Emitter.emit(Packet(...))` path in LLM loop and tool execution.
- Versioned fallback hook usage exists in telemetry via `fetch_versioned_implementation_with_fallback(...)` (not core response assembly).

## 4) Candidate response boundaries (BEST → WORST)

### 1. `gather_stream_full(...)` (BEST for non-stream enforcement)
**Why here (observed):**
- Has finalized answer text, reasoning, tool calls, top docs, citation list, message id, optional chat session id.
- Single deterministic object assembly point for non-stream mode.

**Pros**
- Complete response context in one place.
- Minimal ambiguity in field semantics.
- Easy to enforce against final payload before return.

**Cons**
- Only covers `stream=False` path.
- Streaming clients bypass this boundary.

### 2. `run_llm_step_pkt_generator(...)` during `AgentResponseDelta`/`CitationInfo` emission
**Why here:**
- Earliest point with draft answer tokens and inline citation events.
- Access to `final_documents` at `AgentResponseStart`.

**Pros**
- Works for streaming and non-streaming (shared generation core).
- Can observe token-level draft assembly.

**Cons**
- Stateful/token-level complexity.
- Tool results and full final context may not yet be complete at early deltas.

### 3. `handle_stream_message_objects(...)` around `run_chat_loop_with_state_containers(...)`
**Why here:**
- Has request/session metadata, selected tools, constructed history, and outbound packet stream.

**Pros**
- Unified entry for both streaming and non-streaming.
- Access to request metadata + session/user context.

**Cons**
- Final answer not guaranteed until stream completion.
- Requires packet accumulation logic for strict response-level enforcement.

### 4. Endpoint layer `handle_send_chat_message(...)` (SSE generator / return object)
**Why here:**
- Last API boundary before network response.

**Pros**
- Guaranteed interception of outbound payload to client.
- Can enforce transport-level shape.

**Cons**
- Streaming path receives already-materialized packets as serialized JSON lines (less semantic context unless rehydrated).
- Lower-fidelity access to internal citation mappings/tool internals.

### 5. App middleware (`main.py`) (WORST for evidence-aware enforcement)
**Why here:**
- Generic HTTP middleware sees raw request/response, not semantic chat state.

**Pros**
- Broad coverage.

**Cons**
- Lacks model/tool/citation internals.
- Not practical for evidence-grounded policy without deep response parsing.

## 5) Minimal data available at each boundary

### Boundary 1: `gather_stream_full(...)`
- Draft/final answer text: **Yes** (`final_answer`).
- Retrieved evidence: **Yes** (`top_documents`, `citation_info`, `tool_calls[].search_docs`).
- Request metadata: **Partial** (`message_id`, `chat_session_id`; no raw request headers/body).

### Boundary 2: `run_llm_step_pkt_generator(...)`
- Draft answer text: **Yes** (token deltas + `accumulated_answer`).
- Retrieved evidence: **Partial/Yes** (`final_documents`, `CitationInfo` as they appear).
- Request metadata: **Partial** (via `user_identity`, turn placement; no full HTTP context).

### Boundary 3: `handle_stream_message_objects(...)`
- Draft answer text: **Eventually** (through streamed packets/state container).
- Retrieved evidence: **Yes** (tool outputs, citation mapping in state container).
- Request metadata: **Yes** (chat session/user, req options, tool settings, project/persona context).

### Boundary 4: `handle_send_chat_message(...)`
- Draft answer text: **Streaming chunks or final object** (mode-dependent).
- Retrieved evidence: **Mode-dependent** (full in non-stream result; packetized in stream).
- Request metadata: **Yes** (request headers, auth dependencies, tenant telemetry context).

### Boundary 5: app middleware
- Draft answer text: **No semantic guarantee** (serialized response only).
- Retrieved evidence: **No semantic guarantee**.
- Request metadata: **Yes** (HTTP-level only).

## 6) Missing data / gaps by boundary

### Boundary 1: `gather_stream_full(...)`
- Missing original raw request context (headers, auth method, origin IP).
- Missing explicit per-citation evidence text spans (only ids + docs objects).
- Streaming path not covered.

### Boundary 2: `run_llm_step_pkt_generator(...)`
- Missing stable “final response object” in-stream until completion.
- Missing full tool execution outcomes before they run (pre-tool stage).
- Limited direct HTTP/auth metadata.

### Boundary 3: `handle_stream_message_objects(...)`
- Missing already-normalized final response schema in streaming mode unless aggregated.
- Requires synchronization with asynchronous packet emission/completion callback.

### Boundary 4: endpoint layer
- Streaming path lacks rich internal state unless the endpoint tracks/accumulates it.
- Existing generic `{"error": ...}` fallback shape can diverge from typed packet models.

### Boundary 5: middleware
- Missing all semantic internals (citations mapping, tool docs, model step state).
- High parsing burden with low reliability.

## Recommended boundary (reconnaissance conclusion)
- **Recommended primary boundary:** `handle_stream_message_objects(...)` (shared core for both streaming and non-streaming), with `gather_stream_full(...)` as the strongest concrete response object boundary for non-stream mode.

**Why (from existing code only):**
- `handle_stream_message_objects(...)` is the narrowest shared orchestration layer where request metadata, retrieval/tool context, and generation stream converge.
- `gather_stream_full(...)` provides the richest finalized object currently present, but only when `stream=False`.
- Therefore, for full-mode coverage, the shared handler is the highest-leverage boundary observed in-repo.
