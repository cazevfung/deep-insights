% PHASE 3 CONTEXT REPETITION MITIGATION PLAN

## 1. Context & Pain Points
- Phase 3 step outputs begin to repeat earlier findings as execution progresses, especially from step 4 onwards in `session_20251109_211104`.
- Current prompts only see the immediate step context plus the scratchpad; they lack a structured reminder of which evidence has already been surfaced.
- The scratchpad stores free-form text without machine-friendly anchors, making it hard to suppress duplicates or to score novelty.
- Downstream phases rely on diverse findings; repetition wastes cost tokens and leaves gaps in coverage.

## 2. Goals
1. **Maximize novelty**: Each step should prioritize uncovering new evidence, not restating prior points.
2. **Structured memory**: Maintain per-step digests (goal text, summary, points of interest, notable evidence) that downstream prompts can reference.
3. **Explicit anti-duplication instructions**: Prompts must ask for new ideas and penalize repeats.
4. **Automatic dedupe guardrails**: Execution layer should detect and trim overlaps before sending content to the model or accepting its output.
5. **Telemetry**: Measure repetition rate to prove improvement against baseline sessions.

## 3. Initiatives & Deliverables

### 3.1 Step Memory Aggregation
- Introduce a `StepDigest` record on each completed step capturing:
  - `goal_text`, `summary`, `points_of_interest` (bullets), `notable_evidence` (source anchored).
- Persist digests in the session state and expose helper `aggregate_digests(up_to_step: int)` to build cumulative context.
- Update UI/debug logging to surface digests for inspection.

### 3.2 Prompt Enhancements
- Amend Phase 3 execution prompt template:
  - Include cumulative digest text (`step <= n-1`) ahead of the new step request.
  - Add explicit instructions: “Do not repeat previously logged summaries, points of interest, or evidence. Only surface net-new findings and clearly label them.”
- Add post-response verifier prompt (or function call) that highlights duplicated bullets and requests revisions when overlap > threshold.
- For long contexts, compress digest fields using deterministic summarizer (e.g., `summarize_points_of_interest(digests, max_tokens)`).

### 3.3 Scratchpad Structuring & Dedupe
- Refactor scratchpad to store typed entries: `{id, step_id, title, evidence_ids, summary}`.
- Implement novelty scoring prior to persistence: fuzzy match new bullets against existing ones (embedding cosine similarity, optional keyword heuristics).
- Only append entries when score < novelty threshold; otherwise append comment “duplicate of step X evidence Y” and optionally skip writing.
- Ensure downstream phases consume the structured scratchpad without breaking compatibility.

### 3.4 Execution Flow Updates
- Modify `_execute_step` to fetch `aggregate_digests(current_step_index - 1)` and inject into prompt args.
- After each model response:
  - Run `novelty_filter` to prune repeated bullets.
  - Update `StepDigest` with filtered outputs.
  - Emit `[PHASE3-NOVELTY]` logs summarizing additions vs. pruned items.
- Add config flag `research.phase3.enforce_novelty` with thresholds for duplication similarity.

### 3.5 Telemetry & Evaluation
- Extend analytics pipeline to compute duplication rate: ratio of repeated bullets vs. total bullets per step.
- Add regression benchmark comparing baseline session vs. novelty-enforced run (expect ≥60% reduction in repeats).
- Provide notebook/report template for QA to review novelty metrics alongside qualitative samples.

## 4. Implementation Milestones
1. **M0 – Data Structures (1 day)**: Define `StepDigest`, update session schema, migrate scratchpad writer to typed entries.
2. **M1 – Prompt Changes (1 day)**: Update Phase 3 templates, add cumulative digest injection, implement instruction copy edits.
3. **M2 – Novelty Engine (2-3 days)**: Build similarity checks, response post-processor, and config flags.
4. **M3 – Telemetry & QA (1-2 days)**: Add `[PHASE3-NOVELTY]` logs, metrics computation, baseline comparison automation.
5. **M4 – Rollout (1 day)**: Run staged experiments on archived sessions, gather feedback, toggle flag default.

## 5. Risks & Mitigations
- **Token budget expansion**: Supplying cumulative digests increases prompt size. Mitigate via aggressive summarization and truncation heuristics (priority order: notable evidence > points of interest > summaries).
- **LLM forgetfulness**: Even with instructions, model may still repeat. Backstop with automatic novelty filter that rejects duplicates before finalizing outputs.
- **Latency impact**: Similarity checks add compute. Cache embeddings and reuse them per step; batch comparisons.
- **Regression in downstream phases**: Structured scratchpad changes may break consumers. Provide compatibility layer that presents legacy format alongside new structure during rollout.

## 6. Decision Log & Open Questions
- ✅ Adopt cumulative digests as the primary context-sharing mechanism.
- ✅ Enforce anti-duplication both via prompt engineering and deterministic filters.
- ✅ Use embedding-based similarity (cosine) as the default novelty check with keyword-overlap fallback for tie-breaks.
- ✅ Allow deliberate repeats when prior evidence is being revised; guard via `allow_revision_duplicates=true` config flag.
- ✅ Limit cumulative digest expansion to an additional 1,800 tokens over the base prompt, applying truncation heuristics when at risk of exceeding the cap.

## 7. Next Actions
1. Align with research agents team on digest schema and scratchpad compatibility.
2. Draft revised prompt template incorporating digest + anti-repeat instructions.
3. Spike novelty scoring using recent sessions to calibrate thresholds.
4. Prepare implementation tickets tied to milestones M0–M4.


