# Phase 0–4 Streaming Implementation Plan

## 1. Objectives
- Guarantee streamed AI output appears in the pinned right column for Phases 0, 0.5, 1, 2, 3, and 4.
- Provide clear progress state for each phase, including per-link summarization in Phase 0 and persona creation in Phase 0.5.
- Preserve backward compatibility with existing event bus contracts while extending the UI model.
- Deliver developer diagnostics so QA can verify streaming behavior quickly.
- Detect and recover from stalled streams, especially during long-running Phase 3 executions.

## 2. Scope & Deliverables
- **Backend alignment**: Confirm WebSocket payloads for `research:stream_*` and `summarization:*` events, including metadata required by the new UI.
- **Frontend data model**: Extend stores/hooks so streams for Phases 0–2 have stable IDs, metadata, and lifecycle state.
- **Right column UI**: Render live token streams and status bubbles organized by phase and subtask (summaries, goals, synthesis).
- **Phase 3/4 reliability**: Keep streaming active for long LLM calls and multi-step execution, surfacing heartbeats or interim updates when tokens pause.
- **QA tooling**: Provide instrumentation (feature flag or developer mode) to quickly inspect active streams and payloads.
- **Docs**: Update README or developer docs describing the streaming contract and testing checklist.

## 3. Milestones & Tasks

### Milestone A — Streaming Contract Audit
1. Review backend code paths (`Phase0Prepare`, `Phase0_5RoleGeneration`, `Phase1Discover`, `Phase2Synthesize`) to list emitted stream IDs and metadata fields.
2. Catalogue existing WebSocket events (`research:stream_start`, `research:stream_token`, `research:stream_end`, `summarization:progress`) and note any missing fields for UI rendering (phase key, link ID, timestamps).
3. Decide whether additional metadata must be appended (e.g., `link_id`, `component` for transcript/comments) and document changes required in backend adapters if any.

### Milestone B — Frontend State Refactor
1. Map the audited event types into a unified TypeScript interface (per stream record with `phase`, `title`, `tokens`, `status`, `metadata`).
2. Update the WebSocket subscription layer to normalize events into the new interface.
3. Ensure the store retains incremental token buffers per stream and handles lifecycle transitions (`starting` → `streaming` → `completed` or `error`).
4. Add progress reducers for summarization events so the UI reflects per-item completion and reuse/load states.

### Milestone C — UI Rendering Enhancements
1. Redesign the right column layout to group entries by phase:
   - Phase 0: Summarization streams (transcript/comments) and quality-assessment notes.
   - Phase 0.5: Role-generation prompts/responses and persona summary.
   - Phase 1: Goal generation prompts/responses.
   - Phase 2: Synthesis prompts/responses and derived plans.
   - Phase 3: Execution streams per plan step (prompt, intermediate reasoning, step findings).
   - Phase 4: Final synthesis prompt + streamed report content.
2. Implement streaming text components that append tokens as they arrive, with scroll locking and “copy all” affordance.
3. Display compact status chips (e.g., `Summarizing`, `Reused`, `Error`) using stream metadata.
4. Show summarization progress bars for each content item, including counts (current/total) and stage text.
5. Provide empty states for phases that have not yet started or produced streams.

### Milestone D — Phase 0.5–4 Streaming Reliability
1. Audit `_stream_with_callback` usage across `Phase0_5RoleGeneration`, `Phase3Execute`, and `Phase4Synthesize` to verify callbacks stay attached through long steps.
2. Ensure Phase 0.5 role-generation requests emit unique stream IDs (e.g., `phase0_5:role`) and include persona metadata in `stream_end`.
3. Confirm backend emits periodic heartbeats (`display_message`) during extended tool loops; add additional timers if gaps exceed 20s.
4. Ensure each Phase 3 plan step opens its own stream ID (`phase3:{step_id}`) and remains active until findings land—re-open if retried.
5. Verify Phase 4 report generation streams via unique ID (`phase4:report`) and surfaces saved-path metadata in `stream_end`.
6. Update frontend state reducers to treat Phase 0.5–4 streams identically to earlier phases, including idle detection and resume logic.

### Milestone E — Diagnostics & QA Support
1. Introduce a developer toggle (env flag or keyboard shortcut) that exposes raw payload logs in the right column footer.
2. Add console logging or toast notifications when streams begin/end to aid debugging.
3. Document manual QA steps:
   - Trigger Phase 0 summarization and confirm real-time tokens.
   - Trigger Phase 0.5 role generation, confirm persona stream and final role summary.
   - Trigger Phase 1 goal generation and Phase 2 synthesis, confirm tokens and final state updates.
   - Execute multi-step Phase 3 plan lasting >5 minutes; ensure streaming persists and heartbeats display.
   - Run Phase 4 synthesis and confirm token streaming plus saved-location message.
   - Simulate error responses to validate fallback messaging.

### Milestone F — Documentation & Handoff
1. Summarize the streaming model in `docs/frontend/` (event types, UI mapping, testing steps).
2. Update release notes / changelog with Phase 0–2 streaming support.
3. Provide follow-up tasks for Phase 3/4 parity if needed.

## 4. Dependencies & Risks
- Requires backend to send UI reference into Phase 0 (already tracked separately).
- Large token volumes could affect rendering performance; consider chunking or throttling updates.
- Existing tests may rely on previous store shape; plan updates to unit tests and snapshots.
- QA access to API keys / test datasets must be ensured for end-to-end validation.

## 5. Testing Checklist
- [ ] Phase 0 summarization stream renders transcript tokens live with metadata (link ID, totals).
- [ ] Summarization progress stages update in tandem with streaming.
- [ ] Phase 0.5 role generation streams prompts/responses and shows final persona.
- [ ] Phase 1 goal generation displays prompt and streamed answer.
- [ ] Phase 2 synthesis shows streamed content and final plan summary.
- [ ] Phase 3 streaming remains active for runs longer than 5 minutes without collapsing to final blob.
- [ ] Phase 4 report synthesis streams tokens until completion, then highlights the saved report path.
- [ ] Stream end events close out UI sections and present final token counts.
- [ ] Developer diagnostics accurately reflect underlying WebSocket payloads.
- [ ] No regressions in existing right-column interactions (history, report links, etc.).



