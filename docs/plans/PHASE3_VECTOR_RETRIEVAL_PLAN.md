# Phase 3 Vector Retrieval Acceleration Plan

## 1. Goal & Scope
- Stabilize and speed up Phase 3 execution when content volume is high.
- Introduce ANN vector retrieval that complements existing marker-first flow.
- Maintain output fidelity and observability with exhaustive debug markers.

## 2. Current State Recap
- Phase 0 generates key-marker summaries but does not produce vector-friendly chunks.
- `Phase3Execute.execute()` iterates plan steps, building `data_chunk` strings and streaming responses.
- `_execute_step()` prefers marker overview, then requests context via `_run_followups_with_retrieval()`.
- Retrieval remains keyword/marker/topic-driven (`RetrievalHandler`), with no ANN support or caching beyond per-request in-memory.
- Logs exist (INFO level) but lack structured step/request identifiers, making deep debugging difficult during long runs.

## 3. Bottleneck Analysis Roadmap
- **Benchmark harness**: simulate high-volume batches (≥200 content items) and measure latency per step, follow-up call count, and retrieval latency.
- **Profile retrieval path**: add timing for `_handle_retrieval_request()` and downstream keyword lookups.
- **Track request churn**: log repeated missing-context loops to identify when the model cannot converge due to slow data fetching.
- **Surface telemetry**: emit Prometheus/Grafana metrics for step duration, retrieval hits, and cache performance.

## 4. Indexing Strategy (Phase 0 Enhancements)
- **Chunking**
  - Use adaptive windowing: default 600-800 token chunks with 15-20% overlap, but merge smaller segments to minimize request count and avoid over-fragmentation.
  - Generate multi-scale representations (document-level summary vectors + fine-grained chunks) so Phase 3 can start with coarse hits and only request detailed slices when necessary.
  - Persist `chunk_id`, `link_id`, `chunk_index`, `token_span`, checksum for change detection.
- **Embedding Pipeline**
  - Select base model: `text-embedding-3-small` (cloud) or `bge-base-en-v1.5` (self-hostable fallback).
  - Normalize text (lowercase, strip HTML, standardize whitespace) before embedding.
  - Persist preprocessing rules + model version.
- **Metadata & Markers**
  - Attach Phase 0 marker data (`marker_id`, `marker_type`, summary text, confidence).
  - Capture language, timestamps, and engagement stats for hybrid filtering.
- **Storage Options**
  - Primary: `pgvector` schema (`chunks`, `chunk_embeddings`) with ANN indexes (IVFFlat/HNSW as available).
  - Alternative: dedicated vector store (FAISS + SQLite metadata, Qdrant/Pinecone managed).
- **Debug Markers**
  - Emit `[PHASE0-EMBED] link_id=..., chunk=..., tokens=..., model=...` for each embedding batch.
  - Log `[PHASE0-INDEX]` events when writing to storage, including latency and batch size.
- **Backfill Strategy**
  - Offline job to embed historical content; throttle to respect API limits.
  - Track progress with resumable checkpoints (`last_processed_link_id`).

## 5. Data Maintenance
- Versioned schema (`embedding_version`, `preprocess_hash`).
- Incremental updates triggered by content changes (hash mismatch → re-embed).
- Nightly validation job to detect orphaned vectors or stale metadata.
- Optional replication/backup policy for the vector store.

## 6. Phase 3 Retrieval Refactor
- **Service Layer**
  - Introduce `VectorRetrievalService` with methods:
    - `search(query_text, filters, top_k)` → hybrid vector search.
    - `embed_query(text)` for caching.
    - `fetch_chunks(chunk_ids)` for detailed context.
  - Retrofit into `_handle_retrieval_request()` when `request_type` is semantic or when markers reference chunk IDs.
- **Hybrid Workflow**
  - For each model request:
    1. Embed query (reuse cached vectors per step).
    2. Apply metadata filters (marker type, link_id, language) before ANN search.
    3. Retrieve top `N` chunks (configurable, default 40) and collapse by parent document.
    4. Optionally keyword-boost using BM25/marker overlaps.
  - Ensure fallback to keyword retrieval if vector store unavailable.
- **Context Assembly**
  - Summarize retrieved chunks into bullet previews (with source refs) before sending full text.
  - Respect `_max_total_followup_chars` by truncating or batching chunk payloads.
- **Caching and Memoization**
  - Memorize `(step_id, query_hash)` → results for duplicate requests.
  - Cache embeddings for Phase 3 queries and chunk vectors if local store supports.
- **Debug Instrumentation**
  - Add `[PHASE3-VECTOR] step=..., req=..., top_k=..., latency_ms=..., cache_hit=...]` logs.
  - Surface warnings when ANN latency exceeds thresholds or results fall back to keyword mode.

## 7. API & Schema Adjustments
- Extend Phase 3 prompt instructions to let the model request semantic lookups (`request_type="semantic"`, `parameters.query`).
- Update output schema documentation to clarify that `findings.sources` may reference chunk IDs.
- Validate new `requests` fields in `_parse_phase3_response_forgiving()` without breaking legacy runs.

## 8. Observability & Debugging
- Centralize logging patterns:
  - `[PHASE3-STEP]`, `[PHASE3-RETRIEVE]`, `[PHASE3-VECTOR]`, `[PHASE3-API]`, `[PHASE3-CHUNK]`.
  - Include `trace_id` carried from Phase 0 embedding to Phase 3 execution for correlation.
- Add structured payloads (JSON logs) for tooling ingestion.
- Expose metrics:
  - Query latency histograms, cache hit ratio, retrieved chunk counts, follow-up loop counts.
- Dashboard to monitor long-running jobs, highlighting steps with repeated follow-up churn.

## 9. Testing & Evaluation
- **Unit/Integration**
  - Mock vector store to test `_handle_retrieval_request()` semantic paths.
  - Ensure fallback paths activate when vector store is offline.
- **Benchmark Suite**
  - Curate representative research batches (small/medium/large) with expected findings.
  - Compare baseline vs. vector retrieval: latency, number of follow-ups, relevance metrics (hit rate, precision@k).
- **Quality Review**
  - Human evaluation on a sample of outputs to ensure no regression in accuracy.
  - Monitor hallucination rate and coverage of requested markers.

## 10. Rollout Plan
1. Implement Phase 0 embedding pipeline and complete backfill.
2. Deploy vector store and verify health checks.
3. Integrate `VectorRetrievalService` behind a feature flag (e.g., `research.retrieval.use_vectors`).
4. Enable in staging, run benchmarks, collect telemetry.
5. Gradually enable for subsets of research sessions; monitor logs and metrics.
6. Finalize documentation, update runbooks, and train team on new debug markers.

## 11. Risks & Mitigations
- **Embedding cost/latency**: batch processing and caching; evaluate cheaper model variants.
- **Index drift**: versioned embeddings and automated re-index jobs.
- **Model request churn**: enforce max follow-ups; include guardrails when no relevant chunks found.
- **Operational overhead**: choose managed vector service if team lacks infra bandwidth.
- **Data sensitivity**: ensure embeddings respect data governance; anonymize if required.

## 12. Next Steps Checklist
- [ ] Design and document vector store schema.
- [ ] Prototype embedding job with logging markers.
- [ ] Implement semantic request path in Phase 3 (flagged off).
- [ ] Build benchmark scripts and dashboards.
- [ ] Prepare rollback instructions and playbooks.

