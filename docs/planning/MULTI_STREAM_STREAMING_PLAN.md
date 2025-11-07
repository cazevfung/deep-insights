## Multi-Stream Token Streaming Enhancement Plan

### 1. Objective
- Allow the research workflow to run many concurrent LLM calls while the UI renders each response independently.
- Prevent interleaving tokens from corrupting JSON parsing or delaying feedback.
- Provide a Cursor-like experience for live streams and recently finished outputs.

### 2. Guiding Principles
- Preserve existing concurrency and batching efficiency.
- Maintain backwards compatibility where possible, with a smooth migration path.
- Keep the UX lightweight: active streams are obvious, completed streams stay accessible but unobtrusive.
- Instrument both back-end and front-end for diagnosability (stream IDs, durations, token counts).

### 3. Backend Enhancements

**3.1 Stream Identity**
- Generate a `stream_id` (UUID or ULID) for every streaming interaction.
- Include `stream_id` in `research:stream_start`, `research:stream_token`, `research:stream_end` payloads.
- Update helper methods (`notify_stream_start`, `display_stream`, `notify_stream_end`) to accept / propagate `stream_id`.
- Ensure nested components (e.g., `ContentSummarizer`, phase runner) pass the same ID through callbacks.

**3.2 API Contract & Validation**
- Update shared schema / typing to document new payload shape.
- Add logging that ties together stream_id, phase, link_id, duration, token usage.
- Emit warnings if unexpected sequences occur (token after end, missing end, duplicate IDs).

**3.3 Session Metadata**
- Store per-stream summary in session context for debugging (start timestamp, end timestamp, token totals).
- Optionally expose a debug endpoint listing active streams.

**3.4 Migration Strategy**
- Provide temporary backward compatibility: if a consumer omits `stream_id`, default to a single shared one while emitting warnings.
- Once front-end is deployed, tighten validation to require `stream_id`.
- These changes do not alter research logic; they only enrich streaming metadata and payload shape so the UI can consume partial updates safely.

### 4. Frontend Enhancements

**4.1 State Model Refactor**
- Replace `researchAgentStatus.streamBuffer` string with a dictionary keyed by `streamId`:
  ```ts
  streamBuffers: Record<string, {
    raw: string
    status: 'active' | 'completed' | 'error'
    metadata: StreamMetadata
    timestamps: { startedAt?: string; lastTokenAt?: string; endedAt?: string }
  }>
  ```
- Update store actions (`appendStreamToken`, `clearStreamBuffer`) to operate per stream.
- Introduce selectors for active stream, sorted history, pinned streams.
- Handle stream finalization by freezing buffers and trimming history (keep latest 5 by default).

**4.2 Hooks & Utilities**
- `useStreamState({ streamId? })` should return the requested stream; default to the most recent active stream.
- `useStreamParser({ streamId?, enableRepair, debounceMs })` to parse individual buffers post-completion.
- Update typing for WebSocket messages to include `stream_id` and adjust reducers accordingly.

**4.3 Components**
- `StreamDisplay` accepts `streamId` plus explicit `content` / metadata props; render a stream selector when multiple streams exist.
- `StreamStructuredView` uses `useStreamParser(streamId)`; show parsing status per stream.
- `PhaseStreamDisplay` passes phase-specific IDs and titles.
- Add a “Recent Streams” panel (collapsible history) showing last N completed streams with metadata, copy/star controls, and hover preview.
- Support split view: active live stream alongside a selected completed stream (Cursor-style dual pane).

**4.4 Experience Polish**
- Visual transition when a stream completes (slide to history, badge showing token count / duration).
- Pins for important outputs (pinned items exempt from trimming).
- Keyboard shortcuts (`Alt+[`, `Alt+]`) to navigate streams.
- Auto-scroll only for the active live stream; completed streams remain static.

**4.5 UI Blocks & Cursor-Inspired Demos**
- Stream selector (Cursor quick-switch bar)
  - Appears above bubbles; behaves like Cursor’s tab strip.
  - Active stream uses accent underline; hover shows preview tooltip.
  ```text
  Streams: ● Live | art_req1 | bili_req2 | batch_summary ☆
  ```
- Live bubble micro-interactions
  - Animated typing bar (three-dot pulse) mirroring Cursor’s streaming message animation.
  - Metadata footer within the bubble for phase + elapsed time.
  ```text
  ┌──────────────────────────────────────┐
  │ 🔴 正在生成…                         │
  │ token token token …                 │
  │ …                                   │
  │ Phase 0 • 12s • 101 tokens          │
  └──────────────────────────────────────┘
  ```
- History accordion (Cursor “conversation history” feel)
  - Completed bubbles collapse into a compact list with timestamp labels.
  - Pin/star icons follow Cursor’s left-rail style.
  ```text
  最近流 ▾
  ☆ Phase 0 • art_req1 • 19s • 45 markers
    Phase 0 • art_req2 • 6s • 23 markers
    Phase 0 • batch • 23s • comments only
  ```
- Compare panel trigger
  - “Open in side panel” button renders selection in the right column like Cursor’s split diff.
  - Multiple compare slots stack vertically.
- Ensure spacing/typography borrow from existing Cursor-like components (chip pills, muted timestamp text, subtle separators) so the UI feels cohesive with the rest of the app.

**4.6 Real-Time Structured Highlights**
- Dynamic parsing pipeline
  - Extend `useStreamParser` (or new `useIncrementalStreamParser`) to emit domain events when JSON tokens form recognizable structures (e.g., `goal`, `step`, `finding`).
  - Maintain derived stores such as `liveGoals` keyed by goal id, `livePlanSteps`, etc., so downstream views (goal list, plan cards) can react immediately.
  - Backend contract: ensure streamed JSON includes stable identifiers (`id`, `type`) to allow partial assembly without waiting for the full document.
- UI integration (outside the stream box)
  - Goal list (`ResearchGoalList`) subscribes to `liveGoals`; shows shimmering placeholder rows until data arrives, then replaces them with curated field-level content extracted from the JSON (`goal_text`, `rationale`, `uses`, `sources`) rather than the raw payload.
  - Synthesized goal panel updates progressively (e.g., comprehensive topic appears first, component questions fill in as tokens arrive), always showing human-readable strings instead of raw JSON.
  - Stream display references the same state for quick navigation but does not render the structured JSON itself.
  ```text
  研究目标
  ┌─────────────────────────────┐   Stream
  │ 1  正在生成…▒▒▒▒▒▒▒         │   ┌───────────────┐
  │ 2  目标 2 ...               │←─│ token stream… │
  │ 3  (待生成)                 │   └───────────────┘
  ```
- Interaction model
  - When a goal reaches a minimal viable structure (e.g., `goal_text` present), its card animates from skeleton to content (Cursor’s “message appears” feel).
  - Live badges (e.g., “typing” dots) appear on individual cards to show that more fields are still streaming.
  - Once the stream ends, cards lock and move into the history/pinned states with timestamps.
- Implementation notes
  - Incremental parser should dispatch `goalPartial` and `goalComplete` actions with payload granularity (per field).
  - Handle reordering by preserving original index from streamed data to avoid flicker.
  - Provide fallback to static rendering if parsing fails (card stays in “暂不可用” state with retry affordance).

**4.7 Phase-Wide Structured Streaming**
- Shared schema & type discrimination
  - Standardize streamed JSON envelopes with `{ "type": "phase0.goal", ... }`, `{ "type": "phase1.step", ... }`, `{ "type": "phase2.finding", ... }`, etc.
  - Keep payloads consistent across phases (id, status, timestamps) to support generic incremental parsing.
- Store architecture
  - Create a unified `streamEntities` slice keyed by `type` and `id`, with helpers `selectGoals`, `selectPhase1Steps`, `selectPhase2Findings`, `selectPhase3Evidence`, `selectPhase4Report`.
  - Provide per-phase selectors for view components (e.g., `usePhase1Steps(streamId?)`, `usePhase2Insights`).
- UI mapping by phase
  - **Phase 0 (Data prep)**: `ResearchGoalList`, synthesized abstract panels, summarization progress bars consume `phase0.goal` and `phase0.abstract` events.
  - **Phase 0.5 (Role generation)**: Role profile card listens for `phase0_5.role` partial updates (persona name, tone, duties) and reveals fields as they stream.
  - **Phase 1 (Discover goals)**: Step list / outline receives `phase1.step` events (goal text, required data) and updates cards with typing indicators until each step locks.
  - **Phase 2 (Synthesize)**: Insight board listens for `phase2.finding` and `phase2.cluster` events to populate tiles, highlight new evidence, and show streaming citations.
  - **Phase 3 (Execute)**: Execution timeline consumes `phase3.action`, `phase3.evidence`, `phase3.status` to update progress bars, result tables, and embedded summaries.
  - **Phase 4 (Final synthesis)**: Final report view subscribes to `phase4.section`, `phase4.chart`, `phase4.answer` tokens, rendering the narrative and supporting visuals progressively.
- Navigation & continuity
  - Maintain a global “phase stream index” mapping active `stream_id` to phase components so the UI can jump to the correct tab/section when new content appears.
  - Provide breadcrumbs / notifications (e.g., “Phase 2: New insight 3 ready”) triggered by entity completion events.
- Error handling & retries
  - If a phase emits malformed JSON, mark affected entities with a “解析失败” state and allow manual retry once the stream finishes.
  - Capture metrics per phase (time to first entity, total entities streamed) for diagnostics.

### 5. Data & Persistence
- Ensure state resets cleanly when workflows end or a new batch starts.
- Persist pinned streams in session storage so refreshes retain key outputs during long sessions.
- Consider size limits to avoid storing large transcripts indefinitely (e.g., 1 MB cap per stream).

### 6. Testing Strategy

**Unit Tests**
- Store reducers: append, finalize, trim history, pin/unpin logic.
- Hooks: confirm they return correct stream data for active and completed cases.

**Integration Tests**
- Simulate multiple concurrent `research:stream_*` sequences and confirm UI state updates correctly.
- Ensure JSON parser handles partial input without blocking other streams.

**End-to-End / Manual QA**
- Run Phase 0 summarization with 3+ overlapping calls; verify each stream render.
- Switch between history entries, pinned items, and active stream.
- Confirm keyboard shortcuts and copy/pin actions.

### 7. Rollout
- Implement behind a feature flag `streaming.multipleBuffers` to allow gradual enablement.
- Deploy backend with `stream_id` support first (fallback to default ID), then roll out front-end changes once tested.
- Remove fallback and enforce `stream_id` after confirmation.

### 8. Documentation & Support
- Update developer docs with new message contract and state shape.
- Add UX guidelines mirroring Cursor-style interactions (history rail, previews, split view).
- Include troubleshooting section (e.g., what to check if tokens appear in the wrong pane).

### 9. Open Questions
- How long should completed streams persist? (Default 5, configurable?)
- Should pinned streams sync across sessions or remain local only?
- Do we need export options for archived streams (e.g., download as JSON)?
- How to surface stream metadata in logs/telemetry dashboards (Grafana, etc.)?

