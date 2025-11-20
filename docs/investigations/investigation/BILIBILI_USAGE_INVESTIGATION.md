## Session 20251109 Bilibili vs. YouTube Usage Check

### Scope
- Session: `session_20251109_211104.json`
- Phases reviewed: 1–3 (context gathering through synthesis)
- Question: Are Bilibili fetches present in downstream reasoning, or does the engine rely almost entirely on YouTube material?

### Source Ingestion Snapshot
- Total items ingested in phase0: 19 (YouTube 14, Bilibili 5).
- Bilibili transcripts are present and sizable (≈1.6k–10k characters each) but report extremely low `transcript_word_count` values (median 9 vs. YouTube median 4,922). The counter appears to be whitespace-based, so Chinese text is effectively treated as “short”.
- One Bilibili asset (`bili_req4`, 37 “words”) never surfaces in later phases; the remaining four do appear at least once.

### Downstream Referencing (counts include textual mentions such as `yt_reqN`/`bili_reqN`)

| Phase | YouTube refs | Bilibili refs | Unique YouTube IDs | Unique Bilibili IDs | Notes |
|-------|--------------|---------------|--------------------|---------------------|-------|
| 1     | 78           | 21            | 8 (`yt_req1`, `yt_req2`, `yt_req3`, `yt_req4`, `yt_req5`, `yt_req8`, `yt_req10`, `yt_req13`) | 4 (`bili_req1`, `bili_req2`, `bili_req3`, `bili_req5`) | Early framing already leans ~4:1 toward YouTube |
| 2     | 26           | 7             | same 8             | same 4              | Planning retains the same imbalance |
| 3     | 114          | 20            | 7 (`yt_req1`, `yt_req2`, `yt_req3`, `yt_req4`, `yt_req5`, `yt_req10`, `yt_req11`) | 4 (`bili_req1`, `bili_req2`, `bili_req3`, `bili_req5`) | Final synthesis references YouTube 5.7× as often |

Additional phase3 details:
- Only 6 of 15 synthesis steps mention any Bilibili doc IDs (steps 1, 2, 3, 7, 9, 14), while YouTube sources appear in 13/15 steps.
- Structured `sources` arrays in the step outputs are empty, so downstream tooling cannot differentiate which materials were actually cited.

### Retrieval Telemetry Highlights (phase3)
- Vector search ran on most steps (`vector_calls` 1–4) with best scores clustered in the 0.14–0.48 range.
- Telemetry does not log document IDs, making it impossible to confirm whether Bilibili chunks enter the retrieved context.
- `vector_appended_chars` is non-zero even when `vector_hits` = 0 (step 1), implying fallback context injection outside standard retrieval.

### Interpretation
1. **Bilibili material is not ignored entirely**—its identifiers surface in reasoning text—but YouTube dominates every downstream phase even after normalizing for the initial item imbalance (14 vs. 5).  
2. **Chinese transcripts are mischaracterized as “short”** because the word counter is whitespace-based. Any heuristic depending on word counts (e.g., chunk sizing, retrieval weighting, pruning) will systematically down-rank Bilibili content.  
3. **Missing structured citations** (`sources: []`) suggest that even when Bilibili text is used, it is not registered as supporting evidence, reducing visibility and traceability.  
4. **Telemetry lacks per-document traces**, obscuring whether vector retrieval ever selects Bilibili chunks. Coupled with the low “word count” metrics, this supports the hypothesis that the English-oriented indexing path under-serves Chinese content.

### Suggested Follow-ups (no implementation yet)
- Audit the chunking/indexing pipeline for language-sensitive metrics (word count, tokenizers, embedding model choice). Replace whitespace-based counters with Unicode-aware length/tokens.  
- Capture retrieval diagnostics that include document IDs so we can prove whether Bilibili chunks are excluded upstream.  
- Re-run the session after adjusting indexing to compare reference ratios and confirm whether Bilibili coverage improves.  
- Expose structured source lists in downstream artifacts to surface when non-English materials contribute.

