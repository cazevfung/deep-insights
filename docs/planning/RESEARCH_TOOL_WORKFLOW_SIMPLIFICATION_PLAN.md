## Goal

Streamline the end-to-end research workflow and simplify prompt instructions to improve AI compliance, reduce repetition, and enable guided user input without over-constraining the model. No implementation yet; this document specifies the plan.

## Scope

- Update the integration workflow in `tests/test_full_workflow_integration.py` to introduce user-guided goal creation and approval before proceeding to execution and synthesis phases.
- Revise prompt instruction files under `research/prompts/` to remove overly restrictive guidance and allow more autonomous, creative reasoning.
- Keep the existing word count rule in `phase4_synthesize/instructions.md` (reference to current line indicating ≥7000 words) while simplifying structure to minimize redundancy.

## Objectives

- Add a role-selection prompt before AI generates research goals.
- Insert a user amendment-and-approval loop for research goals prior to proceeding to later phases.
- Simplify Phase 2 and Phase 3 instructions to avoid overly prescriptive step-by-step directives; keep necessary structure but encourage flexible planning and the 5 Whys technique.
- Ensure Phase 4 keeps the word-count constraint while reducing complexity and repetition.
- Avoid providing specific example goals in the prompt formats.

## High-Level UX Flow Changes

1. Prompt the user: "What role should the AI research as?" (free-text).
2. Generate 5 research goals using the selected role and any existing context.
3. Show the 5 goals to the user, then prompt: "How would you like to amend these goals?" (free-text, can be empty).
4. Send the amendment feedback to the AI to produce an amended set of goals.
5. Ask the user to approve: "Proceed with these goals? (y/n)".
   - If no, loop back to Step 3.
   - If yes, continue with Phase 2 → Phase 3 → Phase 4.
6. Run the rest of the workflow as today, but with simplified prompts in each phase.

## Implementation Plan

### A) `tests/test_full_workflow_integration.py` updates

- Insert role prompt prior to goal generation.
- Replace the current auto-synthesize behavior after goal generation with a user-mediated amendment cycle:
  - Collect free-text amendments from the user.
  - Call the goal-amendment prompt with both the original goals and the user feedback.
  - Render amended goals to the user and ask for approval.
  - On approval, proceed; otherwise, repeat the amendment step.
- Ensure the collected role and amendment text are persisted in the session data for traceability.
- Guard for non-interactive mode (e.g., CI) with defaults or a bypass flag.

Notes:
- Do not hard-code goal examples in prompts.
- Maintain backward compatibility by enabling a flag to run the old auto-flow if needed.

### B) Prompt instruction simplification

Guiding principles for all phases:
- Reduce nested, prescriptive checklists; keep outcomes-focused guidance.
- Favor flexible thinking steps over rigid templates.
- Prevent redundancy: explicitly instruct the model to avoid repeating points.
- Preserve necessary constraints (e.g., word count in Phase 4).

#### Phase 1 (`research/prompts/phase1_discover/instructions.md`)
- Add an input parameter for the "research role" selected by the user.
- Direct the AI to generate exactly 5 goals aligned with the role and provided context.
- Remove specific example goals; provide a neutral schema/format without examples.
- Add a short instruction that goals should be distinct, non-overlapping, and actionable.

#### Phase 2 (`research/prompts/phase2_plan/instructions.md`)
- Replace long, prescriptive step lists with a concise planning brief:
  - Identify key information gaps and approaches to fill them.
  - Propose a minimal set of prioritized steps (search, sources to consult, experiments/tests).
  - Allow the AI to adapt steps based on evolving evidence.
  - Emphasize coherence with Phase 1 goals and available materials.
- Keep outputs structured but not exhaustive; no rigid sub-step checklists.

#### Phase 3 (`research/prompts/phase3_execute/instructions.md`)
- Retain the 5 Whys technique as the central investigative method.
- Remove or condense narrow, domain-specific or highly detailed directives.
- Encourage hypothesis generation, testing, and updating with evidence.
- Instruct to track contradictions, uncertainties, and dead ends concisely.
- Require non-redundant reasoning; avoid repeating points.

#### Phase 3 Output Schema (`research/prompts/phase3_execute/output_schema.json`)
- Review fields to ensure they remain compatible with a leaner instruction set.
- Remove fields that enforce overly granular steps, if present.
- Keep fields for hypotheses, evidence, findings, remaining questions, next steps.

#### Phase 4 (`research/prompts/phase4_synthesize/instructions.md`)
- Keep the explicit word count constraint already present (≥7000 words recommended range 7000–12000).
- Simplify the structure: focus on clear argument, evidence synthesis, limitations, and implications.
- Add an explicit non-repetition rule (deduplicate points; collapse duplicates into one strong articulation).
- Allow the AI to design the section flow to best fit the findings.

## Prompt Engineering Notes

- Use short meta-instructions: "Be concise where possible; avoid repetition; prefer original synthesis over restatement."
- Avoid vivid examples that could anchor the model unduly.
- Emphasize alignment with user-selected role and approved goals.
- Permit dynamic adjustment: the AI may revise plans mid-execution if evidence warrants.

## Acceptance Criteria

- Workflow prompts for role selection, goal amendment, and approval are present and wired.
- Phase 1 produces 5 goals with no example text in the prompt.
- Phases 2 and 3 instructions are significantly shorter and less prescriptive while maintaining clarity:
  - Phase 2 enables the AI to propose steps without rigid templates.
  - Phase 3 uses 5 Whys and encourages creative, evidence-driven exploration.
- Phase 4 preserves the word-count requirement and reduces repetition.
- No regressions in non-interactive/CI runs (config flag or sensible defaults).

## Risks and Mitigations

- Risk: Under-specification leads to shallow outputs.
  - Mitigation: Keep outcome-oriented checklists and require explicit evidence use and contradictions handling.
- Risk: User loop can stall.
  - Mitigation: Provide a bypass/timeout or proceed-on-blank-amendment behavior.
- Risk: Backward compatibility issues in tests.
  - Mitigation: Feature flag for legacy auto-flow path.

## Open Questions

- Should we persist user role and amendments to a dedicated metadata file per session? YES.
- Do we need a configurable maximum number of amendment iterations? NO. DEFAULT TO 2 ITERATIONS.
- Any compliance constraints on minimum/maximum word count beyond the current rule? NO.





