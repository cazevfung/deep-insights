## Goal
- Ensure each step processes all available context efficiently without losing key signals.
- Reduce total API calls while keeping extraction quality high.
- Add a robust fallback/augmentation via local condensation to make large inputs tractable and interactive.

## Current Behavior (from logs)
- words=55117, chunk_size=4000, overlap=400, max_windows=8, planned_windows≈16
- Only windows 1..8 are processed (up to ~29200 words), then the step completes.
- Result: roughly half the corpus is seen per step; later content may be ignored.

## Option A: Larger Windows and Full Coverage per Step
### Overview
Increase chunk size and ensure all planned windows are processed so the full corpus is sent across fewer, bigger batches.

### Proposed Config Changes
- chunk_size: 4000 → 12000 (3×)
- overlap: 400 → 600 (keep proportionally modest to reduce duplication)
- max_windows: 8 → auto or a number large enough to cover corpus (e.g., 32)
- paging policy: iterate through all planned windows, not just the first `max_windows`. If `max_windows` is a hard cap, compute it as ceil(total_words / (chunk_size - overlap)).
- token guardrails: add adaptive downshift—if token budget is exceeded, reduce window size dynamically for the current step and retry once.

### Implementation Notes
- Add a coverage assertion per step: after paging, assert last_end >= total_words - safety_margin.
- Log effective coverage metrics: total_words_seen, unique_words_estimate, duplication_ratio.
- Expose CLI/env config for per-step overrides (phase-specific):
  - PHASE1_CHUNK_SIZE, PHASE2_CHUNK_SIZE, PHASE3_CHUNK_SIZE
  - PHASE*_OVERLAP, PHASE*_WINDOW_LIMIT (0/auto = all)
- Retry policy: 1 retry with 0.75× window when model rejects due to context limits.

### Pros
- Simpler runtime path.
- Higher recall (full coverage) when token limits allow.

### Cons/Risks
- Larger windows may increase hallucination risk if prompts aren’t tightly constrained.
- Costs concentrated into larger calls; rate limit spikes possible.

### Success Criteria
- 100% corpus coverage per step (by position).
- ≤ 1.25× increase in total tokens vs baseline to read entire corpus.
- Equal or better extraction F1 on held-out test set.

## Option B: Insert Local Condensation Between Phase 2 and Phase 3
### Overview
Introduce a local (Ollama) summarization pass to distill each source (video transcript, comment thread) into structured, step-aligned arguments. The main model then consumes condensed artifacts, and selectively requests originals for deeper dives.

### Architecture
1. Phase 2 (existing): Determine research lenses and extraction schema.
2. New Phase 2.5 (local): For each source item:
   - Prompt Ollama model with the Phase 2 schema to produce:
     - Key claims/arguments
     - Evidence quotes with timestamps/anchors
     - Counterpoints/uncertainties
     - Source metadata (video_id, comment_id, author, date)
     - Confidence and coverage markers
   - Persist per-item JSON: `<source_id>_condensed.json`
3. Phase 3 (existing, modified):
   - Primary input: concatenated condensed JSON (batched).
   - Agent may request original full text for specific items/segments by id; system retrieves and streams relevant originals back (on-demand expansion).

### Data Flow
- Inputs: transcripts, comment dumps
- Local models: `ollama run qwen2.5:7b` (or `llama3.1:8b-instruct`), configurable
- Outputs: JSON Lines or JSON per item; index written to `data/research/condensed/index.json`
- Retrieval API: function `get_original(source_id, span)` exposes the raw text slice

### Prompting (Local Condensation)
System:
- "You are a meticulous research condenser. Extract step-aligned arguments strictly grounded in text. Cite spans with byte offsets or timestamps."
User:
- Provide Phase 2 schema + source text chunk.
Output JSON schema (strict):
- source_id
- arguments[]: { claim, evidence_spans[], counterpoints[], categories[], confidence }
- coverage: { tokens_input, tokens_processed, percent_covered }
- meta: { author, date, url, content_type }
Add temperature=0.2, top_p=0.9; max context per call sized to local model.

### Batching and Safety
- Chunk long sources for local model; merge condensations by source_id with deduplication.
- Validate JSON with a schema; auto-repair once on parse failure.

### Phase 3 Modifications
- Input builder prefers condensed artifacts; computes size-aware batches.
- On demand: If the main model flags items as ambiguous or requests originals, fetch raw segments and run a focused follow-up call.
- Maintain trace: `requests_log.json` linking condensed claims → original spans.

### Pros
- Dramatically reduces tokens sent to API while preserving key arguments.
- Enables interactive drill-down on-demand.

### Cons/Risks
- Local summarizer drift: may miss niche but important details.
- Added complexity and latency in Phase 2.5.

### Mitigations
- Use high-recall prompts with explicit coverage accounting.
- Add periodic sample audits (N=10 items) comparing condensed vs original for recall.
- Add sentinel queries for rare patterns to catch misses.

### Success Criteria
- ≥ 90% recall of key arguments vs reading full text, measured on annotated subset.
- ≥ 50% reduction in tokens sent to main model.
- ≤ 5% increase in total wall-clock time for end-to-end run (or configurable).

## Rollout Plan
1. Implement Option A config toggles and coverage assertion. Measure coverage and cost deltas on existing test set (`tests/data/test_links.json`).
2. Gate: If Option A meets coverage and cost targets, keep as default for phases with large corpora.
3. Implement Option B (Phase 2.5) behind a flag `USE_LOCAL_CONDENSATION=true` with model selection `OLLAMA_MODEL`.
4. Build validators and retrieval API; add traceability logs.
5. A/B on recent sessions. Metrics: recall on gold items, tokens, runtime, user-rated quality.
6. Choose per-phase defaults:
   - Phase 1: Option A small windows or skip (light discovery)
   - Phase 2: Option B ON for large multi-source batches
   - Phase 3: Start with Option B inputs; on-demand original fetch when ambiguity detected

## Configuration Matrix (env/CLI)
- WINDOW_CHUNK_SIZE_[PHASE]=int
- WINDOW_OVERLAP_[PHASE]=int
- WINDOW_MAX_WINDOWS_[PHASE]=int (0/auto=all)
- WINDOW_ADAPTIVE_DOWNSHIFT=true|false
- USE_LOCAL_CONDENSATION=true|false
- OLLAMA_MODEL=qwen2.5:7b|llama3.1:8b-instruct|custom
- OLLAMA_MAX_PARALLEL=int (limit CPU/GPU)

## Testing
- Unit: JSON schema validation, merging, retrieval slicing.
- Integration: End-to-end with `tests/test_full_workflow_integration.py` and `tests/test_research_agent_full.py` under both options.
- Regression: Compare summaries and extractions from prior runs; alert on significant drift.

## Decision Guidance
- If API budget is tight or corpora are very large: prefer Option B.
- If simplicity and maximum recall are primary: prefer Option A.
- Hybrid is supported: Option A with moderately larger windows + Option B for extremely large sources.



