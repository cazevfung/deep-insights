# Phase 3 Prompt & Schema Enhancement Execution Plan

## Objective
Update the Phase 3 execution prompts and schema so that each step produces a comprehensive article answering the step goal and the system role dynamically reflects the generated research persona.

## Deliverables
- Revised `research/prompts/phase3_execute/output_schema.json` including a new article field positioned between the current summary and analysis sections.
- Updated `research/prompts/phase3_execute/instructions.md` that explicitly requires generation of the article between “重要发现” and “深入分析”, with guidance on scope and tone.
- Updated `research/prompts/phase3_execute/system.md` that sources the analyst role from the Phase 0.5 artifact instead of hardcoding it, preserving reasonable fallbacks.
- Verification notes confirming downstream components consume the new schema field and dynamic role without regression.

## Work Breakdown Structure

### 1. Audit Current Behavior
- Review existing Phase 3 artifacts (e.g. recent session JSON) to confirm current section ordering and identify rendering hooks for “重要发现”与“深入分析”.
- Trace how `Phase3Execute` builds the prompt payload and serializes LLM responses to map the insertion point for the new article field.
- Inspect any consumer paths (UI, reporting, phase 4 inputs) that assume the present schema so regression points are known ahead of implementation.

### 2. Extend Output Schema
- Modify `output_schema.json` to introduce a `article` (or equivalent name) string property between `summary` and `analysis_details` within `findings`.
- Document description focusing on the article’s requirement to fully address the step goal with overview and deep analysis.
- Ensure validation expectations (required vs optional) align with product requirements; update example artifacts or tests if they exist.

### 3. Revise Authoring Instructions
- Update `instructions.md` to direct the model to emit a detailed article section located between “重要发现” and “深入分析”.
- Specify the narrative expectations (overview + deep analysis answering the goal) and clarify serialization mapping to the new schema property.
- Reiterate language/tone requirements so the model understands the article must be in Chinese and aligned with prior style guidance.

### 4. Dynamic System Role Injection
- Update `system.md` to interpolate the research persona from the Phase 0.5 role artifact (per `phase0_5_role_generation/output_schema.json`).
- Implement fallback messaging for cases where the role is unavailable, maintaining compatibility with existing sessions lacking role data.
- Verify the prompt assembly pipeline supplies the role context; adjust loader/template logic if necessary.

### 5. Dependency & Regression Checks
- Examine code that reads Phase 3 findings (e.g. report synthesis, UI renderers) to confirm they gracefully handle the new `article` field.
- Update any downstream schema references, mocks, or fixtures to include the article section.
- Run lint/tests relevant to the touched modules; capture evidence of passing results.

### 6. Acceptance & Sign-off
- Produce sample output demonstrating the new article section inline between “重要发现” and “深入分析”.
- Collect stakeholder review focusing on article quality and role personalization.
- Update documentation (internal runbooks or README snippets) summarizing the change for future maintainers.

## Risks & Mitigations
- **Schema drift**: Coordinate updates across all consumers simultaneously; search for `analysis_details` references to ensure insertions succeed.
- **Prompt token pressure**: Monitor prompt length impact when adding the article requirement; adjust chunking if necessary.
- **Missing role context**: Provide clear fallback behavior to avoid prompt failures when Phase 0.5 data is absent.

## Timeline & Owners
- Draft & review schema/instruction changes: 0.5 day — Assigned to Prompt Engineer.
- Implement dynamic role sourcing: 0.5 day — Assigned to Backend Engineer.
- Integration QA & documentation: 0.5 day — Assigned to QA/Tech Writer.
