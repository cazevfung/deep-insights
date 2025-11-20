# Right-Column Chat Restoration & Enhancement Plan

**Owner:** GPT-5.1 Codex  
**Date:** 2025-11-18  
**Scope:** Restore and upgrade the right-column “Chat” experience so that it reliably streams replies from the `qwen-plus` model (thinking disabled, streaming enabled), threads conversation context with the active session/batch, and remains usable when browsing historical sessions.

---

## 1. Problem Statement

- Users receive `500 Internal Server Error` responses when the UI calls `POST /api/research/conversation`, surfacing as `AxiosError` from `PhaseInteractionPanel.tsx`.
- Chat requests are expected to include:
  - The current session/batch context (active stream, goals, plan, procedural prompts).
  - The full chat history so the AI can reference prior messages.
- Requirement refresh from product:
  - Always run chat on `qwen-plus`, `enable_thinking=false`, `stream=true`.
  - Support chat within active runs _and_ when viewing batch/session history.
  - Persist chat history alongside session history so re-opening a session preserves context.
- Current backend (`ConversationContextService`) already captures most context but still routes to `QwenStreamingClient` with default model selection and no streaming to the UI. History persistence across sessions is incomplete.

---

## 2. Goals & Success Criteria

1. **Stability:** `POST /research/conversation` never 500s for valid requests; failures surface descriptive 4xx/5xx with actionable messages.
2. **Model Guarantees:** Every chat request reaches `qwen-plus` with `think=false`, streamed tokens forwarded to the UI as they arrive.
3. **Session Awareness:** Chat payload automatically includes conversation + research context for the selected session/batch (live or historical).
4. **History Continuity:** Chat history saves with the session so reopening the same history view restores prior exchanges and can continue the thread.
5. **Telemetry:** Structured logs/metrics exist for chat latency, queueing (when procedural prompts block), and LLM failures.

---

## 3. Current Architecture Snapshot

- **Frontend:** `PhaseInteractionPanel` owns the right-column UI; submits free-form messages through `apiService.sendConversationMessage`.
- **Stores:** `workflowStore` tracks active `batchId`/`sessionId`, but history pages may bypass store hydration.
- **Backend:** `ConversationContextService` buffers context snapshots (phase, plan, goals, streams), formats prompts, and defers messages while procedural prompts block. It depends on `research.client.QwenStreamingClient` to call Qwen. Responses feed the websocket manager for downstream UI updates.
- **Gaps Identified:**
  1. API handler does not enforce the qwen-plus/thinking=false/stream=true configuration.
  2. Streaming path stops at backend; UI only receives completion payload (no incremental tokens).
  3. Session history route (`/history/:batchId`) does not hydrate chat state or expose saved conversation logs.
  4. Conversation logs appear memory-only; no persistence layer.

---

## 4. Execution Plan

### Phase A – Verification & Instrumentation
1. **Reproduce Failure:** Use dev server to trigger `/research/conversation` with known-good `batch_id`/`session_id`, confirm 500 stack trace in backend logs.
2. **Add structured logging:** Log request metadata, session linkage, and Qwen client parameters (model, thinking, stream). Mask user content.
3. **Write diagnostic script:** Minimal CLI to call the endpoint and dump response for regression testing.

### Phase B – Backend Model & Streaming Contract
1. **Qwen Client Update:**
   - Extend `QwenStreamingClient` (or wrapper) to accept `model`, `enable_thinking`, `stream`.
   - Hardcode `model='qwen-plus'`, `enable_thinking=False`, `stream=True` for conversation usage.
   - Ensure stream iterator yields incremental chunks and exposes token metadata (timestamps, usage).
2. **Conversation Service Streaming:**
   - Replace `_invoke()` inside `_process_message` with a streaming-aware coroutine that forwards tokens via websocket events (`type: conversation:delta`) before final completion.
   - Maintain final aggregated text for persistence and REST response.
3. **Error Handling:**
   - Map Qwen API errors to 4xx/5xx with explicit `detail`.
   - Update retry/backoff logic for transient failures; mark message as `error` and surface user-friendly notification.

### Phase C – Session & History Linkage
1. **State Persistence:**
   - Add lightweight persistence (e.g., SQLite table `conversation_messages`) keyed by `session_id`/`batch_id`.
   - Serialize `ConversationMessage` entries plus context bundle snapshot references.
2. **History API Enhancements:**
   - Extend `/history/:batchId` (and session resume endpoints) to return stored conversation history & metadata needed for the chat sidebar.
   - Include pagination & last message timestamp to limit payload size.
3. **Workflow Store Hydration:**
   - When opening a historical session, populate `workflowStore.sessionId` & new `conversationStore` from API response so the right-column UI can operate in “history mode” without starting a new workflow.

### Phase D – Frontend Chat Revamp
1. **Conversation Store:**
   - Add Zustand store to track `messages`, `isStreaming`, `activeSessionId`, and `isHistoryMode`.
   - Provide actions to hydrate from history payloads, append streaming deltas, and mark completion/error states.
2. **API Layer:**
   - Augment `sendConversationMessage` signature to include `context_messages` (chat history) + `session_context` to satisfy backend requirements, or ensure backend pulls history via `batch_id`.
   - Handle streaming via websocket events; reconcile message IDs to update UI in real time.
3. **UI Adjustments (`PhaseInteractionPanel`):**
   - On history view mount, call new hydration endpoint and render past chat messages above the composer.
   - Disable composer if no session/batch context is available; show CTA to select a session.
   - Display streaming responses token-by-token (optimistic assistant bubble).
4. **Edge Cases:**
   - If procedural prompts pause chat (status `queued`), show inline banner and auto-resume when backend notifies resolution.
   - Handle session switch by clearing draft + unsubscribing from previous websocket stream.

### Phase E – Testing & Rollout
1. **Unit Tests:**
   - Backend: conversation service streaming path, queueing, persistence serialization.
   - Frontend: store reducers, websocket event handlers, history hydration.
2. **Integration Tests:**
   - Simulate live workflow run with chat interleaved at each phase; ensure context bundle includes fresh data.
   - Resume historical session, confirm chat messages replay and new prompts append correctly.
3. **Manual QA Checklist:**
   - Latency indicator updates during streaming.
   - Switching between sessions preserves respective chats.
   - Offline or backend errors show actionable UI banners.
4. **Monitoring:**
   - Ship metrics (request count, latency, error rate) and structured logs.
   - Alert on sustained 5xx or streaming disconnects.

---

## 5. Dependencies & Risks

- **Qwen API Limits:** Need confirmation that `qwen-plus` supports long-running streaming sessions without enforced thinking. Mitigate by testing in lower env and adding circuit breakers.
- **Persistence Footprint:** Conversation history may grow quickly; consider TTL or per-session cap (e.g., 200 messages) with archival strategy.
- **Websocket Compatibility:** Ensure existing websocket protocol versioning accounts for new `conversation:delta` events so older clients fail gracefully.
- **Session Hydration:** Relying on workflow history endpoints requires consistent availability; add loading/error states to UI.

---

## 6. Deliverables

1. Backend updates (conversation service, persistence schema, API responses, telemetry).
2. Frontend store + UI changes with streaming chat UX.
3. Updated documentation (`docs/frontend/` + `docs/backend/`) describing chat data flow and configuration knobs.
4. Automated tests and manual QA script.
5. Rollout notes with monitoring dashboards & fallback plan (feature flag to disable chat if instability occurs).

---

## 7. Next Steps

1. Schedule deep-dive debugging session to capture concrete stack traces for the existing 500s.
2. Kick off Phase A instrumentation, then proceed sequentially; each phase is shippable behind a feature flag.
3. Align with product/UX on any UI refinements (chat history layout, streaming indicators) before implementation starts.


