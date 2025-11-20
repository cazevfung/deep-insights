# Upload & Text Ingestion Plan

## 1. Objectives & Success Criteria
- Allow researchers to provide **URLs, local files (PDF/Word/PowerPoint/Excel), or raw text blocks** from the LinkInput stage without branching the downstream workflow.
- Extend the scraping subsystem so uploaded assets and manual text use the **same JSON payload format** as remote scrapes (batch items + metadata + extracted content chunks).
- Deliver a clear path for **Excel -> JSON** conversion and document parsing (PDF/DOCX/PPTX) with retry/error reporting comparable to existing scrapers.
- Ensure the backend does **not initiate external scraping** for uploads/text; these items should still appear in scraping progress, status feeds, and the research session store.

## 2. Current Flow Recap (baseline)
1. `LinkInputPage` gathers newline-delimited URLs -> POST `/api/links/format`.
2. Backend `LinkFormatterService` builds batch items (type, source, metadata) + `batch_id` -> persists to `tests/data/test_links.json` and session metadata.
3. Scraping workers read batch items and pipeline results via `ProgressService` + WebSocket updates.
4. Downstream phases expect each item to expose:
   - `id`, `source_url`, `source_type`, per-source metadata.
   - `status` transitions (queued -> scraping -> done/error).
   - Extracted content chunk JSON saved under `data/research/<session>/<batch>/<item>.json` (varies by scraper).

## 3. Proposed Experience Overview
- **Single multi-source form** on `LinkInputPage`: users can mix URLs, upload one or more files (5-10 per batch target), and add optional free-form text notes.
- Form outputs a unified payload: `links[]`, `uploads[]`, `textEntries[]`.
- Backend creates one `batch_id` and synthesizes batch items with `source_kind` (`url`, `upload`, `text_manual`).
- Scraping service dispatches workers:
  - URLs follow existing remote scrapers.
  - Uploads/text go to new **LocalIngestionWorker** that converts assets to JSON and marks them `scraped` without network IO.

## 4. Detailed Implementation Plan

### 4.1 Frontend (client)
- **Component structure**
  - Refactor `LinkInputPage` into modular subcomponents: `LinkEntry`, `FileUploadPanel`, `TextEntryList`, `SourceSummaryCard` to keep file logic contained.
  - Track three pieces of state: `linkText`, `uploadedFiles[]`, `textSnippets[]` (each snippet has `id`, `label`, `content`).
  - Provide drag-and-drop + click-to-upload (HTML `<input type="file" multiple>`). Limit accepted MIME types: PDF, DOC/DOCX, PPT/PPTX, XLS/XLSX.
  - Text block UI: simple textarea with "Add note" button; render editable list with delete.
- **Validation & UX**
  - Ensure at least one source (URL/file/text) before enabling submit.
  - Show per-source counts, total estimated processing time, and warnings for oversized files.
  - Integrate existing notification system for validation errors and backend responses.
- **API contract**
  - Replace `apiService.formatLinks` call with new helper that sends `FormData`:
    ```json
    {
      "links": ["https://..."],
      "text_entries": [{"label": "Context", "content": "..."}],
      "metadata": {"session_id": "..."}
    }
    ```
    plus multipart file fields (`files[]`).
  - Expect response structure: `{ "batch_id": string, "session_id": string, "items": [{"source_kind": "upload" | "url" | "text_manual", ...}] }`.
  - After success navigate to `/scraping` exactly as today.

### 4.2 Backend API surface
- **New endpoint** `POST /api/ingestion/sources`
  - Accept `multipart/form-data` with JSON fields for links/text and binary file streams.
  - Validate file count/size, store binary payloads under `backend/uploads/{session_id}/{batch_id}/{item_id}/raw.{ext}`.
  - Build unified `BatchItem` models: `source_kind`, `ingestion_strategy`, `original_name`, `mime_type`, `content_locator` (path), `status`.
  - Return same schema as `/api/links/format`; consider deprecating old endpoint by making it a thin wrapper that calls the new ingestion service when only links are provided.
- **Service layer**
  - Create `IngestionBatchBuilder` in `backend/app/services/ingestion_service.py` responsible for:
    1. Normalizing payload segments.
    2. Assigning `item_id`s.
    3. Writing a manifest (JSON) describing all items to `data/research/{session}/{batch}/manifest.json`.
- **Workflow integration**
  - Extend `ProgressService` to initialize progress records for `upload`/`text` items and route them to the local ingestion worker queue (Redis/celery/async tasks depending on existing infra--if no queue today, reuse the same scheduling mechanism as URL scrapers).

### 4.3 File ingestion workers
- Create `services/local_ingestion_worker.py` (or extend existing orchestrator) with pluggable converters per MIME type.
- Worker responsibilities:
  - Fetch manifest entry -> read uploaded file/text.
  - Call type-specific converter (see 4.4) -> normalized JSON content.
  - Save `content.json` to the same storage layout as remote scrapers (`data/research/{session}/{batch}/{item_id}.json`).
  - Emit `ProgressService.update_status(item_id, status='scraped', chunks=len(content.chunks))` for UI parity.

### 4.4 Conversion strategies
| Type | Library | Notes |
| --- | --- | --- |
| PDF | `pypdf` or `pdfminer.six` | Page-wise text extraction, capture page numbers + bounding boxes if available. Add fallback using OCR (optional backlog). |
| Word (DOC/DOCX) | `python-docx` | Iterate paragraphs, track heading styles to preserve structure. |
| PowerPoint (PPT/PPTX) | `python-pptx` | Extract slide titles + text shapes; optionally export notes section. |
| Excel (XLS/XLSX) | `pandas` with `openpyxl` engine | Read each sheet to DataFrame, detect header rows (optionally first non-empty row), convert to `records` list. Include metadata: sheet name, column types, number formats. For large sheets, chunk rows (e.g., 200-row segments) to manage downstream token limits. |

#### Excel -> JSON considerations
1. Use `pandas.read_excel(BytesIO, sheet_name=None)` to load all sheets.
2. For each sheet:
   - Drop fully empty rows/columns.
   - Attempt to infer header row: check first row for unique non-null values; fallback to generated `Column_1` etc.
   - Convert DataFrame to list of dicts via `to_dict(orient='records')`.
   - Capture summary stats (row count, column names, numeric ranges) for searchability.
3. Write output structure:
   ```json
   {
     "item_id": "sheet-1",
     "source_kind": "upload",
     "file_type": "excel",
     "sheet_name": "Q3 Pipeline",
     "records": [...],
     "schema": {"columns": [{"name": "Region", "dtype": "string"}, ...]}
   }
   ```
4. If Excel contains multiple sheets, create child chunks per sheet to avoid mega JSON payloads.
5. For formulas, rely on `openpyxl` with `data_only=True` to capture computed values.

#### Text entries
- Treat text snippets as pseudo-files: `content` already available; wrap into JSON chunk with metadata (`entered_at`, `character_count`, `user_label`).
- Mark status instantly as `scraped` but still go through worker for consistent manifest/writing.

### 4.5 Storage & metadata
- Extend manifest schema to include `content_locator` for uploads (`file://` path) and `ingestion_params` (sheet count, doc language, etc.).
- Ensure cleanup tasks remove raw uploads after ingestion completes (or mark TTL) to prevent disk bloat.
- Update session metadata to include `local_sources` summary for audit/export flows.

### 4.6 Security & validation
- Antivirus/extension allowlist to prevent arbitrary executable uploads.
- Enforce size caps (e.g., 25 MB per file, 100 MB aggregate per batch) with descriptive errors bubbled to the frontend.
- Sanitize extracted text (strip null bytes, enforce UTF-8) before writing JSON.
- Log ingestion steps with `item_id` context for debugging.

### 4.7 Testing Strategy
1. **Unit**: converters for each file type (mock `BytesIO` inputs) verifying structured JSON output.
2. **Integration**: upload mix of PDFs + Excel + text via new endpoint, assert manifest + content files exist, `ProgressService` updates propagate to WebSocket.
3. **Frontend e2e**: Cypress (if available) scenario covering: add URL + upload + text, submit, ensure UI transitions to `/scraping` and progress list shows correct counts/types.
4. **Performance**: benchmark Excel conversion on large sheets (10k rows) to size chunking strategy.
5. **Error handling**: simulate corrupted files, unsupported MIME types, oversized uploads to confirm user-facing errors.

### 4.8 Rollout Steps
1. Implement backend ingestion service + endpoint, keep `/api/links/format` for backward compatibility (proxy to new service when only URLs are present).
2. Land local ingestion worker + converters, guarded by feature flag `ENABLE_UPLOAD_SOURCES` in `config.yaml`.
3. Update frontend UI and API layer; behind feature flag until backend deployed.
4. Update docs (`docs/guides/...`) and internal runbooks for operators.
5. Enable feature flag in staging -> validate with real files -> roll out to prod.

### 4.9 Completion & Summarization Safeguards
- **ProgressService parity**: treat every `upload` and `text` manifest entry as a first-class batch item. Local ingestion workers MUST emit the same status transitions (`queued -> scraping -> scraped/error`) via `ProgressService.update_status` so the global "100% scrapers complete" logic remains untouched.
- **No new completion gate**: reuse the existing completion detector (wherever the UI/backend watches for all items to reach a terminal status) rather than adding custom flags for uploads/text. This avoids accidental divergence between item types.
- **Regression tests**:
  - Service-level: create a mixed batch (URL + upload + text) and assert the completion watcher only fires after all items hit `scraped`.
  - WebSocket/UI: simulate progress messages for mixed batches to confirm the frontend still blocks summarization until `progress.totalComplete === progress.totalItems`.
- **Feature flag checks**: keep `ENABLE_UPLOAD_SOURCES` disabled in environments until automated tests confirm completion + summarization sequencing behaves identically to today.
- **Monitoring**: add logs/metrics for batches containing local sources that record when `all_scraped` fires, making it easy to spot premature or missing completion events during rollout.

## 5. Open Questions / Follow-ups
- Do we need cloud object storage (OSS) instead of filesystem for uploads to support multi-instance scaling? (Currently plan assumes single shared disk.)
- Should we deduplicate identical uploads across sessions? Potential future enhancement.
- Are there compliance requirements (PII scanning) before storing user files? If yes, integrate scanner hook post-upload.
- For very large Excel files, do we stream results incrementally to avoid memory spikes?

## 6. Dependencies & Tooling
- Python libs: `pypdf`, `pdfminer.six`, `python-docx`, `python-pptx`, `pandas`, `openpyxl`. Add to `backend/requirements.txt`.
- Frontend: may reuse existing Dropzone component or introduce `react-dropzone` for better UX.
- Testing fixtures: add sample docs under `tests/data/uploads/`.

## 7. Timeline (high-level)
1. **Week 1**: Backend ingestion service + manifest format + text ingestion.
2. **Week 2**: File upload endpoint + storage + worker skeleton + PDF/DOCX converters.
3. **Week 3**: PPTX + Excel converter, chunking + performance tuning.
4. **Week 4**: Frontend UI overhaul, integrate API, add e2e tests, documentation, rollout.

---
Owner: TBD - Last updated: 2025-11-18
