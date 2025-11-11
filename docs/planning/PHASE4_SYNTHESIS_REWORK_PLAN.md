% PHASE 4 SYNTHESIS REWORK PLAN

## 1. Context & Pain Points
- Phase 4 currently over-constrains the synthesis prompt with prescriptive guidance that yields generic, low-value article reports.
- The LLM lacks a unified view of the session journey: role definitions from Phase 0.5, synthesized research goals from Phases 1–2, and execution outputs from Phase 3 arrive piecemeal or are omitted.
- Without structured integration of upstream outputs, the model cannot systematically address every research goal or question; critical insights from Phase 3 are dropped or repeated.
- Existing prompt shape does not enforce critical analysis, evidence attribution, or coverage checks, leading to shallow narratives misaligned with user expectations.

## 2. Goals
1. **Holistic context delivery**: Guarantee Phase 4 sees the complete role brief, consolidated research goals, and full Phase 3 evidence set in a structured schema.
2. **Systematic coverage**: Require the article to answer every goal and question, explicitly referencing supporting evidence.
3. **Critical synthesis**: Elevate the output beyond summary by demanding evaluation, trade-off discussion, and open issues.
4. **Traceability & quality controls**: Produce artifacts (outline, coverage map, evidence citations) that downstream reviewers and automation can verify.

## 3. Initiatives & Deliverables

### 3.1 Context Assembly Pipeline
- Build a pre-synthesis assembler that collates:
  - Role charter(s) from Phase 0.5 (persona, tone, responsibilities).
  - Final research goals/questions distilled in Phase 1–2.
  - Ordered Phase 3 step outputs (summaries, evidence references, metadata).
- Normalize into a typed payload (`Phase4ContextBundle`) exposed to prompt templates and saved with the session.
- Add guardrails/fallbacks when any upstream artifact is missing (warn + skip or regenerate).

### 3.2 Prompt Architecture Refresh
- Replace the monolithic article prompt with a staged prompt sequence:
  - **Outline Draft**: Model builds a structured outline tied to goals/questions.
  - **Coverage Check**: Verify each goal/question maps to outline sections; request revisions if gaps exist.
  - **Full Article Generation**: Expand outline sections, referencing evidence IDs and providing critical analysis.
- Standardize citations as inline tokens (`[EVID-##]`) that the UI renders with tooltips showing source metadata.
- Embed explicit instructions for tone, role alignment, and citation style derived from the context bundle.
- Add configurable knobs for verbosity, critical rigour, and citation density via template parameters.

### 3.3 Reasoning Aids & Intermediate Artifacts
- Introduce helper tables in the prompt (goal → relevant evidence) to focus the model on comprehensive coverage.
- Ask the model to annotate uncertainties, conflicting findings, and recommended next steps.
- Persist intermediate outputs (outline, coverage matrix, article) for debugging, QA, and downstream reuse.
- Support optional supplemental artifacts (FAQs, slide bullets) via configuration flags that extend the staged prompts when enabled.

### 3.4 Quality Gates & Post-Processing
- Implement a deterministic validator that checks:
  - All goals/questions appear in the article with at least one evidence citation.
  - Citations reference valid Phase 3 evidence IDs.
  - Required structural elements (executive summary, deep dive, limitations, recommendations) are present.
- When validation fails, trigger an automated refinement prompt or flag for manual review.
- Log structured coverage metrics (`coverage_score`, `citation_count`, `criticality_score`) for analytics.

### 3.5 Telemetry & Evaluation Loop
- Capture before/after samples to measure article usefulness (internal rubric + optional human QA).
- Track token + latency impacts of the multi-stage prompt to ensure production viability.
- Set up regression dashboards alerting on coverage or citation drops relative to baseline sessions.

## 4. Implementation Milestones
1. **M0 – Context Bundle (1–2 days)**: Define `Phase4ContextBundle`, implement assembler, ensure persistence + tests.
2. **M1 – Prompt Sequencing (2 days)**: Draft new outline/coverage/article templates, wire staged execution.
3. **M2 – Validator & Refinement Loop (2 days)**: Build coverage validator, refinement prompts, and logging hooks.
4. **M3 – QA & Benchmarking (1–2 days)**: Run historical sessions, compare outputs, iterate prompts.
5. **M4 – Rollout (1 day)**: Feature flag deployment, documentation update, team training on new artifacts.

## 5. Risks & Mitigations
- **Token bloat**: Consolidated context may exceed limits; current budgets appear sufficient, so monitor usage and revisit mitigation only if limits are hit.
- **Model drift / hallucinations**: Even with evidence tables, the model may fabricate details; counter with stricter instructions and automated citation validation.
- **Latency increase**: Multi-stage prompting adds round-trips; consider caching outline for reuse and supporting parallel validator checks.
- **Upstream dependency gaps**: Missing or inconsistent Phase 3 outputs could break synthesis; introduce sanity checks and regeneration paths.

## 6. Open Questions & Next Actions
- ❓ Determine acceptable maximum token budget for the context bundle + staged prompts.
- ✅ Adopt inline evidence citations (e.g., `[EVID-17]`) and render via tooltips in the article UI.
- ✅ Enable optional auxiliary artifacts (FAQs, slide bullets) when requested by configuration.
- ✅ Schedule working session with research agents + prompt engineers to review this plan.
- ✅ Draft prompt templates and validator spec for stakeholder feedback.
- ✅ Prepare experiment design comparing current vs. staged synthesis on recent sessions.


