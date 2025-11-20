# Right-Column Chat Context Handoff Plan

## 1. Background & Goals

- **Problem**: The chat service currently auto-bundles large context snapshots before every LLM turn. When the model actually needs specific artifacts (e.g., Phase 3 findings), it manually asks within the reply, resulting in redundant tokens and hallucinated assumptions.
- **Goal**: Mirror the Phase 3 “request → provide → continue” handshake inside the general chat so that the LLM explicitly asks for missing datasets, receives precise payloads, and then crafts the final response. Avoid implementing now; plan the work.

## 2. Proposed Flow (High-Level)

1. **User message arrives** at `/research/conversation`.
2. **Conversation service evaluates** whether required artifacts are already cached. If not, it creates a “context request” instruction instead of immediately calling the LLM.
3. **Backend emits request** over websocket (`conversation:context_request`) and returns `status="context_required"` to the REST caller.
4. **UI surfaces prompt** (similar to Phase 3 request cards) showing what the assistant needs (phase, files, excerpts, etc.).
5. **System/analyst attaches data** (selected snippets from session JSON, uploads, or manual text) via a new endpoint (e.g., `POST /research/conversation/context-supply`).
6. **Conversation service stores payload**, rebuilds bundle, and resumes the deferred LLM call to produce the final chat answer.

## 3. Feature Scope

- **Scope In**: Right-column chat, context gathering for phases 0–4, websocket protocol additions, minimal state persistence.
- **Scope Out**: Changes to Phase 3 execution workflow itself, ingestion/backfill pipeline, or LLM prompt tuning beyond the new handshake.

## 4. Detailed Plan

### 4.1 Backend: Conversation Context Service

1. **State Model**
   - Extend `BatchConversationState` with:
     - `pending_context_requests: Deque[ContextRequest]`
     - `awaiting_context_for_message: Dict[str, ContextRequest]`
     - `context_sources: Dict[str, List[ProvidedContext]]` to track what has been supplied.
2. **Context Request Detection**
   - Before `_process_message`, call a policy function `ContextNeedsAnalyzer`. Inputs:
     - Active phase, known goals/plan, user message classification (question vs. action), missing artifacts flagged in state, optional heuristics (e.g., no Phase 3 summaries loaded).
   - Output: `None` (continue normal flow) or `ContextRequest` describing required slots (`phase`, `artifact_type`, `key_path`, `size_limit`, `urgency`).
3. **Deferred Processing**
   - If a request is generated, mark the user message as `status="waiting_context"` and persist the request.
   - Return a specialized REST response: `{ status: "context_required", user_message_id, request_id, required: [...] }`.
   - Broadcast websocket event `conversation:context_request`.
4. **Context Supply Endpoint**
   - New route `POST /research/conversation/context-supply` accepting `request_id`, `batch_id`, `payloads`.
   - Validate payload (size, type), store under `context_sources`, log provenance (who supplied, timestamp).
   - When the request’s quotas are satisfied, resume `_process_message` with an augmented `context_bundle` that includes the supplied snippets under `external_context`.
5. **Prompt Rendering Updates**
   - `_render_context_for_prompt` becomes modular:
     - Append a new section “## Supplied Context Attachments” listing each payload reference (phase, description, truncated body).
     - Provide metadata linking attachments to the user message ID.
   - **Baseline inclusions before any request**: every chat turn must inject, in order:
     1. Latest user input.
     2. Chat history
     3. Style fragment `styles/style_{writing_style}_cn.md`.
     4. `{data_abstract}`, `{user_guidance}`, `{system_role_description}。{research_role_rationale}`.
     5. Current `synthesized_goal`.
     6. Phase 3 outputs (`summary`, `points_of_interest`) when available.
   - These fields should be pulled from session metadata/cache and merged into the context bundle automatically so the LLM already has default research scaffolding before deciding whether to request more artifacts.
   - Introduce **prompt sheet files** (per phase / per interaction mode) that define the ordering and wording of each section. The backend should render context by filling these templates rather than hardcoding strings so PMs can tweak content without code changes.
6. **Error/Timeout Handling**
   - If context is not provided within a configurable SLA (e.g., 5 minutes), send a reminder websocket event or auto-cancel with an apology message.
   - Allow manual override to force-run without context (UI button).

### 4.2 Backend: Session Data Access Helpers

1. **Artifact Extractors**
   - Provide helper functions to slice Phase 0–4 data from `session_<id>.json` by key path (e.g., `phase_artifacts.phase3.steps[step_id]`).
   - Sanitize output (size limits, redactions).
2. **Auto-Suggestions**
   - When generating a context request, pre-fill recommended snippets with file offsets so analysts can click-to-attach.

### 4.3 Frontend Updates

1. **State Store**
   - Extend `workflowStore` (or a dedicated `conversationStore`) with:
     - `contextRequests[]`, `pendingSupplies`, `selectedArtifacts`.
2. **UI Components**
   - Right-column panel shows request cards with:
     - Summary text (“Need Phase 3 Step 7 evidence”)
     - Quick actions: “Attach plan excerpt”, “Attach manual note”, “Skip”.
   - Modal or drawer listing available artifacts (read from session export via existing APIs or new `/sessions/:id/artifacts` endpoint).
3. **Submission Flow**
   - New form to paste/attach context; calls the backend supply endpoint.
   - Show delivery status, allow retries, and update timeline.
4. **Notifications**
   - Toasts or inline banners when requests arrive/expire.
5. **Historical Sessions**
   - When loading history, also hydrate saved requests/supplies so analysts can review how answers were produced.

### 4.4 API & Protocol Changes

| Aspect | Current | Proposed |
| --- | --- | --- |
| REST `POST /research/conversation` | Always returns `status="ok"/"queued"` | Add `status="context_required"` payload |
| Websocket events | `conversation:message` / `conversation:delta` | Add `conversation:context_request`, `conversation:context_update`, `conversation:context_resolved` |
| Persisted data | conversation log only | Include `context_requests` and `attachments` per batch |

## 5. Migration & Rollout Steps

1. **Phase 1 – Detection Skeleton**
   - Implement analyzer stub returning “no request” to ensure plumbing doesn’t break.
2. **Phase 2 – Protocol & UI**
   - Introduce new REST/websocket shapes, front-end request cards, manual supply UI (without automation).
3. **Phase 3 – Artifact Helpers**
   - Expose session artifacts via backend endpoints; add quick-attach UX.
4. **Phase 4 – Policy Enhancements**
   - Refine analyzer heuristics, integrate with Phase 3 semantics (e.g., map each chat question to relevant steps).
5. **Phase 5 – Telemetry & Safeguards**
   - Track request frequency, fulfillment time, and fallback rates.

## 6. Risks & Mitigations

- **User Friction**: Too many requests could stall conversations. Mitigate with smart heuristics and allow overriding.
- **Latency**: Waiting on supplies introduces delays. Provide timers, reminders, and default cached snippets.
- **Data Leaks**: Attaching raw artifacts risks exposing sensitive data. Enforce sanitization and role-based permissions.
- **Complexity**: Additional protocol paths can drift from backend/frontend parity. Maintain shared TypeScript definitions for events and keep JSON schemas in `/docs/contracts`.

## 7. Open Questions

1. **Context suppliers**: automated system hooks (reuse baseline inclusions + analyzer). Human analysts only intervene on exception flows; no separate analyst queue required.
2. **Attachment persistence**: continue storing alongside batch JSON in `data/research/conversations/<batch>.json` to avoid schema churn. Revisit DB-backed storage only if concurrency/scaling becomes an issue.
3. **RAG integration**: treat supplied snippets as optional future embeddings but do not change current pipeline; simply log each payload with metadata so we can batch-index later without altering chat flow now.
4. **SLA / partial supplies**: mirror Phase 3 behavior—default timeout equal to Phase 3 request window, allow resuming when minimum required fields are satisfied, and auto-fallback after timeout with a warning message.

---
**Next Action**: Review and iterate on this plan with stakeholders before touching code.

