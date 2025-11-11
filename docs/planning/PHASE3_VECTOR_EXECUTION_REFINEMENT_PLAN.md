# Phase 3 Vector Execution Refinement Plan

## 1. Context & Pain Points
- Latest profiling run (`session_20251107_202526` on `batch 20251107_121603`) still paged through 15×4k-word windows (`Processing window 13 (36000-40000/98561)` … `window 15 (42000-46000/98561)`), leading to >60k-word LLM calls.
- Vector store indexing completes quickly ([TIMING] vector_indexing ≈0.5 s) but Phase 3 falls back to sequential chunking before leveraging ANN results.
- Large sequential payloads inflate latency, cost, and exceed memory budgets; retrieval loop rarely emits `[PHASE3-VECTOR]` hits because steps lack semantic requests.
- Phase 2 plans default to `required_data='transcript_with_comments'` and `chunk_strategy='sequential'`, guaranteeing the slow path even when vector summaries exist.
- Debug telemetry insufficient to prove when vector search was skipped vs. no matches found.
- Latest log excerpt (2025‑11‑08 03:12 UTC) shows Steps 1 & 2 consuming the full 33 sequential windows with `max_transcript_chars=0`, and follow-up cycles repeatedly logging `appended_context_len=33 from 0 blocks`, confirming that the current code never issued a successful semantic retrieval before paging. Only one window (`Step 2 Window 30`) surfaced vector context (`872` chars from 2 blocks), far too late to change overall latency.

## 2. Goals
1. **Vector-first execution**: Ensure Phase 3 exhausts semantic/marker retrieval before chunk paging; sequential fallback becomes rare.
2. **Smarter plans**: Phase 2 generates step metadata that enables vector retrieval (marker IDs, semantic queries, link filters).
3. **Observability**: Detailed timing + counters that distinguish vector hits, fallback triggers, and sequential coverage gaps.
4. **Adaptive chunking**: Dynamically adjust window sizes using vector hit density and transcript stats.

## 3. Initiatives & Deliverables

### 3.1 Retrieval Strategy Overhaul
- **Hybrid routing layer**: Extend `_execute_step` to run in order: marker filters → semantic vector search → keyword fallback. Only call `_execute_step_paged` if collected context < configurable threshold (e.g., 2k tokens).
- **Semantic request synthesis**: When the model returns `missing_context`, detect natural language phrases and automatically reissue `request_type="semantic"` with the same text before opening another window.
- **Window throttling**: Cap sequential windows to 3 per step unless vector results are empty; log a warning `[PHASE3-FALLBACK] step=<id> windows=<n>`.
- **Implementation notes**:
  - Introduce a `VectorRoutingContext` helper inside `research/phases/phase3_execute.py` that tracks collected context tokens and vector hits. The helper should own the threshold logic and expose `should_page_next_window()`.
  - Refactor `_run_followups_with_retrieval` so the first retry issues `request_type="semantic"` when the model responds with `still_missing` and no vector results have been tried.
  - Add guardrails that persist hit metadata (`source_id`, `link_id`) to avoid re-fetching the same blocks in later windows.

### 3.2 Plan Generation Improvements
- **Phase 2 schema update**: add optional fields `vector_queries`, `primary_markers`, `source_whitelist`. Teach prompt to emit per-step ANN hints (e.g., `"vector_queries": ["LLM NPC memory synchronization"]`).
- **Post-plan optimizer**: Lightweight pass that inspects required data and rewrites `chunk_strategy` to `vector_first` when transcripts are >8k words and markers exist.
- **Retrofit existing sessions**: When loading legacy plans without hints, derive default `vector_queries` from goal text + marker overview before execution.

### 3.3 Vector Store Enhancements
- **ANN diagnostics**: Track match counts, top score, and latency; emit `[PHASE3-VECTOR] matches=10 best=0.82 time=35ms` to confirm success.
- **Context bundling**: When multiple chunks from the same `link_id` rank high, merge them into a condensed bullet summary before shipping to the model to reduce duplicate evidence.
- **Cold-start guard**: Detect when embeddings are missing (`vector_indexed=False`) and block sequential paging until indexing re-runs.

### 3.4 Adaptive Chunking
- **Transcript histogram**: During Phase 0 indexing, persist word-count distribution. Use it in Phase 3 to set `chunk_size` dynamically (e.g., 25% of transcript length capped at 2500 words).
- **Evidence saturation**: After each model turn, compute overlap between new findings and existing scratchpad. If <10% new markers, switch strategy to targeted vector queries instead of next sequential window.

### 3.5 Instrumentation & Tooling
- **Structured logs**: Adopt JSON logging for key events (`phase`, `step_id`, `action`, `duration_ms`, `context_tokens`).
- **Metrics surface**: Add counters for `phase3.vector.hits`, `phase3.vector.empty`, `phase3.sequential.windows`, feeding into Grafana for latency dashboards.
- **Replay harness**: Expand `scripts/profile_phase3_vector.py` to accept flags (`--vector-only`, `--force-sequential`) and summarize timing deltas across modes.
- **Immediate telemetry gaps observed**: add `[PHASE3-ROUTER]` debug entries whenever the routing layer decides to fall back, including `tokens_collected`, `vector_hits`, and `window_index`, so we can confirm decisions directly in logs like the provided session.

### 3.6 Engineering Work Breakdown (implementation-focused)
- **Routing Layer (owners: Phase 3 team)**
  - File targets: `research/phases/phase3_execute.py`, `research/retrieval/vector_service.py`.
  - Deliver `VectorRoutingContext`, rewire `_execute_step` orchestration, and enforce the 3-window cap via config flag `research.retrieval.max_sequential_windows`.
  - Update unit tests under `tests/research/test_phase3_execute.py` (add new fixture covering vector-first path).
- **Plan Schema + Optimizer (owners: Phase 2 team)**
  - Modify `research/phases/phase2_plan.py` to emit new fields, extend `PlanStep` dataclass in `research/plans/schema.py`, and add backward-compatible loader for historical sessions.
  - Introduce optimizer module `research/plans/postprocess/vector_hints.py` with full test coverage.
- **Telemetry + Harness (owners: Infra)**
  - Enhance logging utilities in `research/logging/structured.py` to emit JSON events, wire counters into `metrics/exporter.py`.
  - Extend `scripts/profile_phase3_vector.py` CLI with new flags plus tabular summary comparing vector vs. sequential latency; ensure example run prints vector hit rate and sequential windows consumed.

## 4. Implementation Milestones
1. **M0 – Telemetry foundation (1 day)**
   - Add `[PHASE3-VECTOR]` metrics, fallback warnings, and summary counters.
   - Update profiling script to print vector stats.
2. **M1 – Retrieval pipeline (2-3 days)**
   - Implement hybrid routing + window throttling.
   - Introduce semantic request synthesis.
3. **M2 – Plan optimizer (2 days)**
   - Update Phase 2 prompts + schema.
   - Build post-plan rewriting utility for legacy sessions.
4. **M3 – Adaptive chunking & bundling (2 days)**
   - Context bundling for high-overlap hits.
   - Dynamic window sizing/early exit heuristics.
5. **M4 – Validation & Benchmarking (2 days)**
   - Re-run archived batches, compare sequential vs. vector-first times.
   - Document findings, update runbooks.

## 5. Success Criteria
- Phase 3 completes first two steps on `batch 20251107_121603` with ≤2 sequential windows and vector hits logged.
- Average per-step time reduced by ≥40% vs. current profiling run.
- Telemetry dashboard shows ANN hit rate ≥70% for steps targeting long transcripts.
- No regressions in findings quality (validated via existing integration tests/manual review).
- Shared embedding/retrieval modules (`VectorIndexer`, `VectorRetrievalService`) remain the single integration point across phases; no phase introduces bespoke indexing code.
- Config schema (`research.embeddings.*`) and Phase 2/3 prompt outputs stay aligned—schema validation must pass in CI before rollout.
- Profiling script and integration tests exercise the full Phase 0→3 pipeline after each major change to confirm consistent indexing behavior.
- Standardized log prefixes (`[PHASE0-INDEX]`, `[PHASE3-VECTOR]`) appear in profiling outputs, proving all phases honor shared telemetry contracts.

## 6. Risks & Mitigations
- **LLM request regressions**: Semantic hints might mislead the model. Mitigate by keeping sequential fallback and monitoring `still_missing` fields.
- **Indexing lag**: If Phase 0 fails, vector lookup returns empty, causing repeated fallbacks. Add sanity check and auto-trigger reindex job.
- **Plan schema churn**: Frontend/backend need to tolerate new fields. Use feature flag and default values for legacy runs.

## 7. Next Actions
1. Ship telemetry updates + profiling harness enhancements (M0).
2. Branch off hybrid retrieval implementation and land behind `research.retrieval.vector_first` flag.
3. Iterate with real batches to calibrate window caps and ANN thresholds before enabling by default.

```
Phase 0: Prepare + Index
  ├─ Load batch via ResearchDataLoader (transcripts + comments)
  ├─ Summarize content (markers, abstracts)
  ├─ VectorIndexer
  │     ├─ Build multi-scale chunks (doc + transcript + comments)
  │     ├─ Embed chunks (EmbeddingClient → provider/hash)
  │     └─ Persist to SQLite vector_store (chunk metadata, checksum, version)
  └─ Session metadata
        ├─ Set vector_indexed=True, store chunk stats
        └─ Emit debug markers `[PHASE0-INDEX] batch=<id> items=<n> duration=<ms>`

Phase 1 / 1.5: Goal Refinement (unchanged)
  └─ Uses indexed summaries implicitly via marker overview context

Phase 2: Plan Generation
  ├─ Compose plan prompt with marker overview + summaries
  ├─ LLM outputs plan steps with vector hints (vector_queries, markers, link filters)
  └─ Plan optimizer (post-pass)
        ├─ Ensure chunk_strategy=vector_first when transcripts large
        ├─ Attach default semantic queries if missing
        └─ Emit `[PHASE2-PLAN]` debug entries (step count, vector hint coverage)

Phase 3: Execute Steps
  ├─ For each step:
  │     ├─ Gather step metadata (vector queries, markers)
  │     ├─ Vector retrieval
  │     │     ├─ VectorRetrievalService.search(query, filters)
  │     │     └─ Format top-k matches → retrieved_content
  │     ├─ Marker/keyword fallback if ANN hits empty
  │     ├─ Sequential paging only if context budget unmet
  │     ├─ Update scratchpad + chunk tracker
  │     └─ Emit telemetry + debug markers (`[PHASE3-VECTOR]`, `[PHASE3-FALLBACK]`, timings)
  └─ Final result aggregated for Phase 4 synthesis

Cross-Phase Consistency
  ├─ Shared config (`research.embeddings.*`) drives all embeddings/retrieval
  ├─ Telemetry/log prefixes shared: [PHASE0-INDEX], [PHASE2-PLAN], [PHASE3-VECTOR], [PHASE3-FALLBACK]
  └─ Profiling harness validates end-to-end flow + debug markers
```