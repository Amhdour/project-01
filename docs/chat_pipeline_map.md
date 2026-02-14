# Chat Pipeline Execution Path (Onyx backend)

This document maps the **actual production chat request path** from the FastAPI route to retrieval, LLM generation, and response assembly.

## Primary vs legacy routes

- **Primary production route**: `POST /chat/send-chat-message` → `handle_send_chat_message(...)` in `backend/onyx/server/query_and_chat/chat_backend.py`.
- **Legacy/deprecated route**: `POST /chat/send-message` → `handle_new_chat_message(...)` (marked deprecated in code comments).

> Note: route registration in `backend/onyx/main.py` prepends optional `APP_API_PREFIX`, so the deployed path is effectively `/{API_PREFIX}/chat/send-chat-message` when `API_PREFIX` is set.

---

## Minimal call graph (primary production path)

```text
main.py:get_application
  -> include_router_with_global_prefix_prepended(..., chat_router)

chat_backend.py:handle_send_chat_message  [POST /chat/send-chat-message]
  -> process_message.py:handle_stream_message_objects(...) -> AnswerStream
    -> (build tools) tool_constructor.py:construct_tools(...)
      -> SearchTool instantiated when internal search is available
    -> chat_state.py:run_chat_loop_with_state_containers(
         run_llm_loop, llm_loop_completion_callback, ...)
      -> llm_loop.py:run_llm_loop(...)
        -> llm_step.py:run_llm_step(...)
          -> llm_step.py:run_llm_step_pkt_generator(...)
            -> llm.stream(...)  [LLM generation stream]
        -> tool_runner.py:run_tool_calls(...)  [if LLM emits tool calls]
          -> search_tool.py:SearchTool.run(...)
            -> search_tool.py:_run_search_for_query(...)
              -> search_pipeline(... ChunkSearchRequest ...)
            -> convert/merge/select sections, return ToolResponse(SearchDocsResponse, llm_facing_response)
      -> llm_loop_completion_handle(...)  [persists final assistant turn]
  -> process_message.py:gather_stream_full(packets, state_container) -> ChatFullResponse
  -> chat_backend.py:_gate_host_response(...) -> final dict response contract
```

---

## Stage mapping

## 1) FastAPI entrypoint (primary)

- **Function**: `handle_send_chat_message`
- **Path**: `backend/onyx/server/query_and_chat/chat_backend.py`
- **Input type**: `SendMessageRequest` (`chat_message_req`), `Request`, `User | None`
- **Output type**: `dict` (Trust & Evidence enforced host response)
- **Key flow**:
  - Calls `handle_stream_message_objects(...)` to produce `AnswerStream`.
  - Calls `gather_stream_full(...)` to assemble `ChatFullResponse`.
  - Wraps with `_gate_host_response(...)`.

Snippet:
```python
@router.post("/send-chat-message", response_model=None, tags=PUBLIC_API_TAGS)
def handle_send_chat_message(
    chat_message_req: SendMessageRequest,
    request: Request,
    user: User | None = Depends(current_chat_accessible_user),
    _rate_limit_check: None = Depends(check_token_rate_limits),
    _api_key_usage_check: None = Depends(check_api_key_usage),
) -> dict:
    ...
    state_container = ChatStateContainer()
    packets = handle_stream_message_objects(...)
    result = gather_stream_full(packets, state_container)

    host_context = {
        "chat_result": result,
        "chat_message_req": chat_message_req,
    }
    return _gate_host_response(host_context)
```

## 2) Chat orchestration + loop launch

- **Function**: `handle_stream_message_objects`
- **Path**: `backend/onyx/chat/process_message.py`
- **Input type**: `SendMessageRequest`, `User | None`, `Session`, headers and options
- **Output type**: `AnswerStream` (generator of packets/errors/ids)
- **Key flow**:
  - Creates/loads session and user message.
  - Builds tools via `construct_tools(...)`.
  - Starts loop via `run_chat_loop_with_state_containers(run_llm_loop, ...)` for normal path.

Snippet:
```python
def handle_stream_message_objects(
    new_msg_req: SendMessageRequest,
    user: User | None,
    db_session: Session,
    ...
) -> AnswerStream:
    ...
    tool_dict = construct_tools(...)
    tools: list[Tool] = []
    for tool_list in tool_dict.values():
        tools.extend(tool_list)
    ...
    yield from run_chat_loop_with_state_containers(
        run_llm_loop,
        llm_loop_completion_callback,
        ...
        tools=tools,
        ...
    )
```

## 3) Retrieval / search stage (invoked by tool calls)

- **Function**: `SearchTool.run`
- **Path**: `backend/onyx/tools/tool_implementations/search/search_tool.py`
- **Input type**:
  - `placement: Placement`
  - `override_kwargs: SearchToolOverrideKwargs` (contains `original_query`, `num_hits`, `max_llm_chunks`, etc.)
  - `llm_kwargs` with key `queries` (list of LLM-generated search queries)
- **Output type**: `ToolResponse`
  - `rich_response=SearchDocsResponse(search_docs, citation_mapping)`
  - `llm_facing_response` (string fed back to LLM)

- **Fetch/chunk retrieval invocation**:
  - `_run_search_for_query(...)` calls `search_pipeline(...)` with `ChunkSearchRequest(...)`.

Snippet A (search invocation):
```python
def _run_search_for_query(self, query: str, hybrid_alpha: float | None, num_hits: int) -> list[InferenceChunk]:
    search_db_session = self._get_thread_safe_session()
    try:
        return search_pipeline(
            db_session=search_db_session,
            chunk_search_request=ChunkSearchRequest(
                query=query,
                hybrid_alpha=hybrid_alpha,
                user_selected_filters=(self.user_selected_filters if self.project_id is None else None),
                bypass_acl=self.bypass_acl,
                limit=num_hits,
            ),
            project_id=self.project_id,
            document_index=self.document_index,
            user=self.user,
            persona=self.persona,
        )
    finally:
        search_db_session.close()
```

Snippet B (tool run and return payload):
```python
def run(self, placement: Placement, override_kwargs: SearchToolOverrideKwargs, **llm_kwargs: Any) -> ToolResponse:
    ...
    all_search_results = run_functions_tuples_in_parallel(search_functions)
    top_chunks = weighted_reciprocal_rank_fusion(...)
    top_sections = merge_individual_chunks(top_chunks)[: override_kwargs.num_hits]
    search_docs = convert_inference_sections_to_search_docs(top_sections, is_internet=False)
    ...
    selected_sections, best_doc_ids = select_sections_for_expansion(..., llm=self.llm, ...)
    ...
    return ToolResponse(
        rich_response=SearchDocsResponse(
            search_docs=search_docs, citation_mapping=citation_mapping
        ),
        llm_facing_response=docs_str,
    )
```

## 4) LLM generation stage

- **Functions**:
  - `run_llm_loop` (`backend/onyx/chat/llm_loop.py`)
  - `run_llm_step` / `run_llm_step_pkt_generator` (`backend/onyx/chat/llm_step.py`)
- **Inputs**:
  - history (`list[ChatMessageSimple]`), `tools`, prompt config, `llm`, token counter
- **Outputs**:
  - `run_llm_step(...) -> tuple[LlmStepResult, bool]`
  - stream packets emitted through `Emitter`

- **Generation invocation**:
  - `run_llm_loop` calls `run_llm_step(...)`
  - `run_llm_step_pkt_generator` calls `llm.stream(...)`

Snippet A (loop calls step):
```python
llm_step_result, has_reasoned = run_llm_step(
    emitter=emitter,
    history=truncated_message_history,
    tool_definitions=[tool.tool_definition() for tool in final_tools],
    tool_choice=tool_choice,
    llm=llm,
    placement=Placement(turn_index=llm_cycle_count + reasoning_cycles),
    citation_processor=citation_processor,
    state_container=state_container,
    final_documents=gathered_documents,
    user_identity=user_identity,
)
```

Snippet B (actual LLM streaming call):
```python
for packet in llm.stream(
    prompt=llm_msg_history,
    tools=tool_definitions,
    tool_choice=tool_choice,
    structured_response_format=None,
    max_tokens=max_tokens,
    reasoning_effort=reasoning_effort,
    user_identity=user_identity,
):
    ...
    yield Packet(...)
```

## 5) Response assembly (final non-streaming API response)

- **Function**: `gather_stream_full`
- **Path**: `backend/onyx/chat/process_message.py`
- **Input type**: `packets: AnswerStream`, `state_container: ChatStateContainer`
- **Output type**: `ChatFullResponse`
- **Assembled fields**:
  - `answer`, `answer_citationless`, `pre_answer_reasoning`, `tool_calls`, `top_documents`, `citation_info`, `message_id`, `chat_session_id`, `error_msg`

Snippet:
```python
def gather_stream_full(packets: AnswerStream, state_container: ChatStateContainer) -> ChatFullResponse:
    ...
    for packet in packets:
        ...
    final_answer = state_container.get_answer_tokens() or answer or ""
    reasoning = state_container.get_reasoning_tokens()
    tool_call_responses = [ToolCallResponse(... ) for tc in state_container.get_tool_calls()]

    return ChatFullResponse(
        answer=final_answer,
        answer_citationless=remove_answer_citations(final_answer),
        pre_answer_reasoning=reasoning,
        tool_calls=tool_call_responses,
        top_documents=top_documents,
        citation_info=citations,
        message_id=message_id,
        chat_session_id=chat_session_id,
        error_msg=error_msg,
    )
```

---

## Legacy path (deprecated)

- Route: `POST /chat/send-message`
- Handler: `handle_new_chat_message`
- Uses `stream_chat_message_objects(...)` + `gather_stream(...)` (basic response) and returns gated contract.
- Marked in code with: “WARNING: this endpoint is deprecated and will be removed soon. Use the new send-chat-message endpoint instead.”
