# Phase Feedback Enhancement Plan

## Goal
- Prompt the user for guidance twice: once before role generation (shared with Phase 0.5 and Phase 1) and again after Phase 1 (feeding Phase 2).
- Persist both inputs so downstream phases (especially Phase 4) can reference the specific guidance that shaped the workflow.

## Key Changes
- Capture an initial free-text prompt before Phase 0.5 begins.
- Reuse the existing post-Phase-1 amendment prompt but distinguish its storage and usage.
- Ensure both prompts are stored in the session metadata for later phases, including Phase 4 synthesis.

## Implementation Steps
1. **Capture Pre-Role Feedback**
   - In `research/agent.py`, prompt the user before calling `Phase0_5RoleGeneration`.
   - Store the response (allowing empty) in a variable like `pre_role_feedback`.
   - Save this to the session metadata (e.g., `session.set_metadata("phase_feedback_pre_role", pre_role_feedback)`).

2. **Feed Pre-Role Feedback Into Phases**
   - Update the call to `Phase0_5RoleGeneration.execute` to accept an optional feedback argument, and adjust `Phase0_5RoleGeneration` to forward the text in its prompt context.
   - Pass the same `pre_role_feedback` into the first `Phase1Discover.execute` as the `amendment_feedback` (or a new parameter if a separate field is clearer), so Phase 1 goal generation reflects the initial guidance.

3. **Retain Post-Phase-1 Amendment Loop**
   - Keep the existing amendment prompt after displaying the initial Phase 1 goals.
   - Rename local variables if needed for clarity (e.g., `post_phase1_feedback`).
   - Continue to rerun Phase 1 with this feedback and confirm approval as today.

4. **Persist Both Inputs**
   - Store both `pre_role_feedback` and `post_phase1_feedback` in session metadata (e.g., `phase_feedback_pre_role`, `phase_feedback_post_phase1`).
   - Ensure existing metadata such as `phase1_user_input` remains accurate or is updated to clarify which feedback it represents.

5. **Propagate Feedback to Phase 2 and Phase 4**
   - When calling `Phase2Synthesize.execute`, pass the post-Phase-1 feedback (current behavior) and also make available the pre-role feedback if needed by the synthesis prompt.
   - For Phase 4, confirm that both feedback entries are accessible—either by passing explicitly when initializing the phase or by having Phase 4 read from session metadata. Update prompt context to include both if useful.

6. **Schema and Prompt Adjustments**
   - Review prompt templates for Phase 0.5, Phase 1, Phase 2, and Phase 4 to incorporate the new feedback strings appropriately.
   - Update any JSON schema validations if new fields are included in outputs.

7. **Testing and Validation**
   - Run console workflow to verify the two prompts appear at the intended times and that phases react accordingly.
   - Confirm session metadata contains both feedback strings and that Phase 4 output references them when applicable.


