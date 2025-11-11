# Phase & Step Restart Enhancements Plan

## Objectives
- Allow users to re-run individual research phases without repeating the entire workflow.
- Enable targeted re-execution of specific Phase 3 steps while maintaining downstream consistency.
- Preserve and reuse intermediate artifacts so reruns are efficient and reliable.
- Extend backend/frontend interfaces to expose restart actions with clear user feedback.

## High-Level Strategy
- Modularize the research agent to execute phases independently and persist each phase's outputs.
- Augment session storage to capture all artifacts required for replays (plans, findings, reports, metadata).
- Provide backend orchestration endpoints and job handlers dedicated to phase/step reruns.
- Update frontend UI and state management to trigger reruns, visualize progress, and refresh results.

## Detailed Work Plan

### 1. Research Agent Refactor
- [ ] Break `DeepResearchAgent.run_research` into discrete `run_phaseX` methods returning structured results.
- [ ] Ensure each phase method accepts existing session metadata and can be invoked independently.
- [ ] Define dependency rules (e.g., rerunning Phase 2 invalidates Phase 3 & 4 outputs) for cascade handling.
- [ ] Update orchestration logic to compose phases dynamically and respect rerun requests.

### 2. Session Persistence & Data Model
- [ ] Extend `ResearchSession` to persist phase artifacts (Phase 0 combined abstract, Phase 1 goals, Phase 2 synthesis, Phase 3 plan & findings, Phase 4 report).
- [ ] Implement versioning or timestamps for each artifact to manage rerun history.
- [ ] Provide helper APIs to load/save artifacts atomically and invalidate dependent data when reruns occur.
- [ ] Evaluate storage footprint; consider referencing large blobs via file paths instead of embedding.

### 3. Phase Restart Backend Flow
- [ ] Introduce backend service entry points (e.g., `WorkflowService.run_phase` / `rerun_phase`) that:
  - Load the targeted session.
  - Invoke the appropriate `run_phaseX` method.
  - Cascade reruns for downstream phases or flag them as stale.
  - Stream progress via existing WebSocket UI hooks.
- [ ] Add REST/WebSocket control endpoints (e.g., `POST /workflow/restart/phase`) accepting `batch_id`, `session_id`, target phase, and options.
- [ ] Ensure reruns queue safely with existing background jobs (no concurrent conflicts).
- [ ] Log and broadcast completion status, refreshing stored artifacts on success.

### 4. Phase 3 Step Restart Mechanics
- [ ] Persist the Phase 3 plan structure within the session for lookup.
- [ ] Expose targeted execution API on `Phase3Execute` (e.g., `rerun_step(step_id, ...)`) that reuses `_execute_step` logic.
- [ ] When rerunning a step:
  - Replace scratchpad + stored findings for that step.
  - Broadcast updated `phase3:step_complete` message.
  - Mark Phase 4 outputs as stale (or trigger regeneration).
- [ ] Optionally support batched reruns (multiple steps) with shared batching logic.

### 5. Phase 4 Regeneration Flow
- [ ] Allow Phase 4 to run independently using persisted Phase 2 + updated Phase 3 outputs.
- [ ] Wire rerun triggers (from phase or step reruns) to automatically regenerate the final report or prompt the user to do so.
- [ ] Maintain previous report revisions or provide diffing metadata for transparency.

### 6. Frontend Enhancements
- [ ] Add UI controls on phase summary pages and Phase 3 step cards to initiate reruns (with confirmation dialogs).
- [ ] Extend WebSocket handlers & stores to process new rerun messages (status updates, restarts, stale markers).
- [ ] Reflect rerun progress in the UI (loading indicators, timeline entries, updated timestamps).
- [ ] Handle stale data states (e.g., disable report view until new Phase 4 completes).

### 7. Testing & Quality
- [ ] Create integration tests covering:
  - Phase rerun end-to-end (Phase 2 rerun triggers new Phase 3 & 4 outputs).
  - Step rerun flow (single step refresh + report regenerate).
  - Persistence correctness (artifacts reload across process restarts).
- [ ] Add unit tests for new session persistence helpers and rerun orchestration logic.
- [ ] Verify concurrency and cancellation handling for rerun jobs.

### 8. Documentation & Rollout
- [ ] Update developer docs describing the new modular agent API and session schema.
- [ ] Document backend endpoints and expected WebSocket events for reruns.
- [ ] Provide user-facing guidance in app docs/tooltips about rerun behavior.
- [ ] Plan phased rollout with feature flags if necessary (enable per environment).

## Open Questions / Follow-Ups
- How to manage cross-phase artifact versioning (keep history vs. latest only)? latest only
- Should rerunning Phase 0 also allow skipping scraping by reusing cached downloads? yes allow skipping, dont scrape again, used scraped results of that batch
- Do we need per-step diffing views to compare rerun results with previous outputs? no.
- How will reruns interact with cancellation logic and session expiration policies? not sure what you mean, but i think it would mean that the entire batch process will be kept in the server and never timeout unless the user explicitly tells the service to stop the entire batch. that's becoz user could restart any phase or step along the way.

## Next Steps
1. Review scope and confirm dependency cascade rules with stakeholders.
2. Sequence implementation milestones (agent refactor → persistence → backend APIs → frontend → tests).
3. Create feature branch and set up tracking tasks aligned with the to-do list above.
