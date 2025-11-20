## Right Column Conversational Feedback Plan

### Situation & Goals
- Provide a consistent conversational space in the right column so users can message the AI at any time, independent of the current streaming phase.
- Ensure AI responses are grounded in the active workflow state, completed phases, and the user’s latest intent.
- Avoid regressing existing streaming UX while introducing the feedback loop.

### Success Criteria
- **Availability**: Right column input and response stream stay functional during all phases (0-4) and while background streaming tasks run.
- **Context Awareness**: AI responses leverage prior phase outputs, current phase objectives, and active user engagement.
- **Low Friction**: Minimal additional user actions; message → coherent reply loop with sub-5s perceived latency.
- **Safety**: Guard against hallucinated state; system gracefully reports when required context is missing.

### High-Level Approach
- Treat the right column as a “conversational overlay” that mirrors the timeline/state machine but remains decoupled from streaming render logic.
- Maintain a lightweight `conversation_context` object assembled per message prior to LLM call.
- Use streaming-compatible messaging channel (existing SSE/WebSocket) so responses can be piped without freezing primary content.
- Allow phase-specific enrichers to contribute to `conversation_context`, ensuring modularity.

### Prompt Strategy
- **System Prompt Foundation**: Describe assistant role (“You are Research Tool Copilot…”) with directives:
  - respond succinctly when clarifying; be detailed when asked for deep feedback
  - reference provided artefacts explicitly; never invent missing phases
  - highlight blockers, risks, or suggested actions relevant to phase.
- **Context Sections Injected** (ordered, optional if empty):
  1. `session_metadata`: user id, project id, active phase, sub-phase, UI mode.
  2. `phase_playbook_excerpt`: canonical goals, success signals, guardrails for active phase.
  3. `completed_phase_summaries`: concise bullet summaries from prior phases (Phase 0…current-1).
  4. `active_stream_snapshot`: current streaming step label, last emitted chunk (if any), pending tasks.
  5. `user_message_history`: last N (3-5) right column exchanges for continuity.
  6. `known_constraints`: deadlines, scope boundaries, flagged risks.
- **User Prompt Assembly**:
  ```
  <system_prompt>
  <developer_orchestration_instructions>
  <context_bundle>
  User: <latest user message>
  Assistant:
  ```
- Leverage `phase_playbook` when present; else default to generic research assistant guidance.

### Context Aggregation Logic
- **Source of Truth**: Persist `phaseOutputs[phaseId]` summaries after each phase completes. Already exists for Phase 3 pipeline; extend to previous phases.
- **Aggregator Service**:
  - Input: `session_state`, `user_message`
  - Steps:
    1. Fetch active phase metadata (`phase_state_store`).
    2. Pull `phaseOutputs` for completed phases; truncate to 300-500 tokens total.
    3. Fetch active streaming step (if pipeline streaming) including partial output buffer.
    4. Append conversation memory (same channel).
    5. Compose context sections JSON-like, ensuring deterministic ordering.
  - Output: `context_bundle` string to inject.
- **Caching**: Memoize per phase state hash to avoid recomputing heavy context when unchanged.
- **Fallbacks**: If aggregator fails, respond with apology + prompt user to retry.

### Phase-Specific Enhancements
- **Phase 0-1**: Emphasize goal clarification; include backlog of research questions and constraints.
- **Phase 2**: Add mapping of shortlisted data sources and evaluation status.
- **Phase 3**: Reuse existing method to pass previous step outputs; ensure last completed step summary appended.
- **Phase 4**: Bring synthesis rubric + required deliverable format; highlight open issues.
- **Any Post-Phase**: Provide final summary reference and suggest next actions.

### Structured Prompt Integration (Phases 0-2)
- **Intent Routing**: Treat procedural inputs (e.g., Y/N, short text) as high-priority prompts owned by the phase workflow; right column submissions are queued until required procedural input resolves.
- **UI Coordination**: Lock right column send action with tooltip explaining “Waiting for phase prompt response” when a modal/inline prompt is active; auto-unlock once workflow input accepted or timeout occurs.
- **Backend Arbitration**:
  - State machine exposes `awaiting_user_input` flag + metadata (prompt id, allowed responses).
  - Conversation endpoint checks this flag before executing; if active, either reject with structured message or append to `deferred_messages` queue to replay after procedural input captured.
  - After procedural response persists, aggregator merges it into context (`latest_phase_input`) and drains deferred user messages FIFO.
- **Validation & Consistency**:
  - Procedural input handler normalizes responses and performs conflict detection (e.g., Phase 1 yes/no vs contradictory right column request); when detected, respond via right column with clarification prompt referencing authoritative choice.
  - Log both sources separately (`phase_inputs`, `conversation_messages`) to preserve audit trail.
- **Fallback UX**: If procedural input times out or errors, show recovery steps in both primary prompt UI and right column (e.g., “Phase 1 prompt failed, please retry”).
- **Testing Plan**: Simulate concurrent inputs (phase prompt + user question) to ensure no crashes, state leakage, or duplicate LLM calls.

### UX Considerations
- Right column retains current conversation transcript; new messages append at bottom with timestamps.
- Disable send button only while prior response streaming; show typing indicator.
- Display “context snapshot” toggle (optional) for debugging what the AI saw.
- Surface error banner if context injection fails; allow retry with minimal disruption.

### Technical Tasks (Defer Implementation)
- Define TypeScript interfaces for `ConversationContext`, `PhaseSummary`, `ActivePhaseState`.
- Implement aggregator module in backend (likely `backend/services/contextAggregator.ts`).
- Extend FE right column component to request conversation response API.
- Update backend conversation endpoint to orchestrate prompt assembly and call LLM.
- Add tests: unit for context aggregator, integration for conversation endpoint per phase scenario.

### Open Questions
- What is the maximum token budget we can dedicate without impacting main pipeline calls?
- Should user be able to reference artefacts outside the current session (e.g., attach files)?
- How to log feedback interactions for analytics without capturing sensitive text?

### Next Steps
- Circulate plan for stakeholder review.
- Confirm token budget + latency targets with infra team.
- Once approved, schedule implementation tasks per phase.

