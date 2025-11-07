## Research Agent User Input Refinement Plan

### Objective

Ensure every interactive user input block in the research workflow is (1) consistently visible at the top of its context, and (2) clearly transitions to a completed state once the user submits a response. This plan covers the necessary front-end architecture adjustments, state management updates, backend signals, and validation steps required before implementation.

### Current Entry Points

- `client/src/pages/LinkInputPage.tsx`: session bootstrap form that gathers URLs before the workflow starts.
- `client/src/pages/ResearchAgentPage.tsx`: dynamic prompt area triggered by `researchAgentStatus.waitingForUser` within the research phase, fed by WebSocket messages handled in `client/src/hooks/useWebSocket.ts` and persisted via `client/src/stores/workflowStore.ts`.

Observed issues:

1. Dynamic prompts render inline near the bottom of the research card, so they may scroll out of view during long token streams.
2. After submission, the UI immediately resets the textarea but retains `waitingForUser` state until the backend sends another event, so the prompt block never visually completes or collapses.
3. Multiple prompts in quick succession are not tracked individually; only the latest message is stored, preventing a history or clear completion indication.

### Design Goals

1. Surface active prompts at the top of the research experience so the user never misses required input.
2. Maintain explicit status states: `awaiting`, `submitting`, `completed`, and `dismissed`.
3. Support sequential or queued prompts without losing context.
4. Prevent regressions in existing workflow progress, stream display, and notifications.

### State Management Plan

- Extend `researchAgentStatus` in `workflowStore`:
  - `activePromptId: string | null`
  - `promptQueue: PromptEntry[]` where `PromptEntry` holds `id`, `type`, `prompt`, `choices?`, `status`, `submittedAt?`, `response?`.
  - `lastCompletedPromptId?: string` for quick reference when highlighting completion.
- Add actions:
  - `enqueuePrompt`, `markPromptSubmitting`, `markPromptCompleted`, `dismissPrompt`.
  - Update existing `updateResearchAgentStatus` usage to funnel new prompt messages through `enqueuePrompt` instead of directly setting `waitingForUser`.
- Derive `waitingForUser` from whether any `promptQueue` entries have `status === 'awaiting'` to avoid manual resets.

### WebSocket / Backend Coordination

- Maintain current `research:user_input_required` event to enqueue prompts. Capture `prompt_id`, prompt text, and optional choices.
- Introduce a paired acknowledgement event (`research:user_input_status` or similar) emitted when the backend receives the user response via `deliver_user_input`. The payload should include `prompt_id`, `status: 'received' | 'error'`, and optional metadata.
- On the front end, listen for the new status event in `useWebSocket` and call `markPromptCompleted` or `dismissPrompt` accordingly.
- As a fallback for legacy flows, continue clearing prompts when any new `research:stream_start` arrives to avoid leaving stale UI in long-running sessions.

### Front-End UI Strategy

1. Abstract a new `PromptPanel` component:
   - Accepts active prompt, queue, and callbacks for submission/choice selection.
   - Always renders at the top of the `ResearchAgentPage` card (above stream output).
   - Displays queued prompts collapsed with brief summaries beneath the active block.
2. Active prompt presentation:
   - Use a sticky container inside the card to keep it visible during scrolling.
   - Show status chips or iconography for `awaiting` vs `submitting`.
   - Disable inputs and show spinner while `submitting`.
3. Completion handling:
   - Once `markPromptCompleted` runs, transition the prompt into a compact summary row (timestamp + response) and collapse it. The main input area disappears until another prompt is enqueued.
   - For approval-only prompts (empty response allowed), display a “已确认” badge in the summary.
4. Link input page adjustments:
   - Verify the session bootstrap form already anchors at the top; if future redesign introduces competing panels, consider applying the same sticky or priority layout conventions there for consistency.

### Interaction Flow (Research Prompts)

1. WebSocket receives `research:user_input_required` → `enqueuePrompt` appends entry, sets `activePromptId` if none.
2. `PromptPanel` renders active prompt at top. User submits text or selects choice.
3. `handleSendInput` dispatches `markPromptSubmitting(activePromptId)` and sends `research:user_input` message.
4. Front end waits for `research:user_input_status`:
   - On success: `markPromptCompleted` stores response, sets `activePromptId` to the next queued prompt (if any), and triggers completion animation.
   - On error/timeout: `dismissPrompt` (or revert to awaiting with error message) and surface notification.
5. Completed prompt summary remains accessible until the research phase ends or the user clears history manually.

### Accessibility & UX Notes

- Provide ARIA live region updates announcing when a new prompt appears or completes.
- Support keyboard submission (Ctrl+Enter) and explicit buttons; ensure focus automatically moves to the active prompt when one arrives.
- Maintain responsive layout: on small screens, collapse summary history into an accordion to keep the active prompt visible.

### Implementation Sequencing

1. **State groundwork**: introduce store schema changes, preserving backward compatibility by defaulting queue to empty and deriving `waitingForUser`.
2. **WebSocket updates**: handle new queue-aware actions on `research:user_input_required` and wire up acknowledgement handling.
3. **Backend emission**: update `deliver_user_input` (and any REST endpoint bridging) to broadcast the new status event after enqueuing responses.
4. **UI refactor**: replace inline block in `ResearchAgentPage` with `PromptPanel`, apply sticky layout, display queue and completion summary.
5. **Cleanup**: remove legacy `waitingForUser` toggles and ensure all references derive from the queue state.

### Testing & Validation

- **Unit tests**: cover store actions for prompt lifecycle transitions and ensure derived `waitingForUser` behaves correctly.
- **WebSocket integration**: mock socket events to verify the panel updates on required, submitting, confirmation, and error paths.
- **UI tests**: component tests for `PromptPanel` (React Testing Library) focusing on ordering, sticky behavior, and accessibility announcements.
- **End-to-end**: simulate full workflow with multiple prompts to confirm top-of-view placement and completion collapse in Cypress/Playwright scenario.
- **Regression checks**: validate that streaming content, notifications, and progress tracker remain unaffected.

### Rollout Considerations

- Feature flag the queue-based handling to allow rapid rollback if backend coordination encounters issues.
- Monitor WebSocket logs for prompt acknowledgement latency and front-end error notifications during staging.
- Update documentation and internal playbooks to reflect the new user experience before release.


