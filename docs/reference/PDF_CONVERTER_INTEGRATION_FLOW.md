# PDF Converter Integration Flow

This document describes how the PDF to Markdown converter integrates into the scraper → summarization system from frontend to backend.

## Overview Flow

```
Frontend Upload → Ingestion Service → PDF Converter → File Storage → Scraper → Summarization
```

## Detailed Flow

### 1. Frontend Upload (`client/src/pages/LinkInputPage.tsx`)

**User Action:**
- User selects PDF files via file input
- Files are stored in component state as `uploadedFiles`

**Code:**
```typescript
// File input accepts PDF files
<input
  id="file-upload"
  type="file"
  multiple
  accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.markdown"
  onChange={handleFileSelect}
/>
```

**On Submit:**
- Files are added to FormData
- Sent to `/ingestion/sources` endpoint via `api.ingestSources(formData)`

---

### 2. Backend Ingestion Route (`backend/app/routes/ingestion.py`)

**Endpoint:** `POST /ingestion/sources`

**Process:**
1. Receives FormData with files
2. Parses files, links, and text entries
3. Calls `IngestionService.ingest_sources()`

---

### 3. Ingestion Service (`backend/app/services/ingestion_service.py`)

**Key Method:** `_convert_upload()`

**PDF Processing Flow:**

```python
# Step 1: Save raw PDF file
raw_path = batch_storage / "uploads" / f"{uuid}.pdf"
raw_path.write_bytes(contents)

# Step 2: Extract markdown from PDF
text_content = self._extract_text_from_file(raw_path, suffix)

# Step 3: Save as markdown file
text_file = batch_storage / "prepared" / f"{uuid}.md"
text_file.write_text(text_content, encoding="utf-8")
```

**PDF Extraction Method:** `_extract_text_from_file()`

```python
if suffix in PDF_EXTENSIONS:
    try:
        from utils.pdf_to_markdown import convert_pdf_to_markdown
        return convert_pdf_to_markdown(path)  # Converts PDF → Markdown
    except ImportError as e:
        # Fallback to plain text if converter unavailable
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)
```

**Output:**
- **Raw PDF:** `data/research/{session_id}/{batch_id}/uploads/{uuid}.pdf`
- **Markdown File:** `data/research/{session_id}/{batch_id}/prepared/{uuid}.md`
- **URL:** `file://` URI pointing to markdown file (e.g., `file:///D:/App Dev/Research Tool/data/research/.../prepared/{uuid}.md`)

**Manifest Entry:**
```json
{
  "source_kind": "upload",
  "display_name": "document.pdf",
  "raw_path": "data/research/.../uploads/{uuid}.pdf",
  "text_file": "data/research/.../prepared/{uuid}.md",
  "file_extension": ".pdf"
}
```

---

### 4. Links File Generation

**File:** `tests/data/test_links.json`

**Content:**
```json
{
  "batchId": "20251120_195654",
  "createdAt": "2025-11-20T19:56:54",
  "links": [
    {
      "id": "link_upload_1",
      "url": "file:///D:/App Dev/Research Tool/data/research/.../prepared/{uuid}.md",
      "type": "upload"
    }
  ]
}
```

---

### 5. Scraping Service (`backend/app/services/scraping_service.py`)

**Process:**
1. Reads `test_links.json`
2. Routes links to appropriate scrapers based on URL type
3. **File URLs (`file://`)** → `ArticleScraper`

---

### 6. Article Scraper (`scrapers/article_scraper.py`)

**Key Method:** `extract()`

**File URL Handling:**
```python
if url.startswith('file://'):
    result = self._extract_from_local_file(url)
    return result
```

**Local File Extraction:** `_extract_from_local_file()`

```python
# Convert file:// URL to file path
file_path = url.replace('file:///', '')  # Remove file:// prefix

# Read markdown content (preserves formatting)
content = path.read_text(encoding='utf-8')

# Return in scraper format
return {
    'success': True,
    'content': content,  # Markdown content
    'metadata': {
        'title': path.stem,
        'source': 'local_file',
        'url': file_url,
        'file_path': str(path),
        'word_count': word_count
    }
}
```

**Output File:**
- `data/research/batches/run_{batch_id}/{batch_id}_ARTICLE_{link_id}_article.json`

**Content:**
```json
{
  "success": true,
  "content": "# Markdown Content\n\n**Bold text** and *italic text*\n\n| Table | Data |\n|-------|------|\n| ... | ... |",
  "metadata": {
    "title": "{uuid}",
    "source": "local_file",
    "url": "file:///...",
    "word_count": 1234
  }
}
```

---

### 7. Data Loader (`research/data_loader.py`)

**Key Method:** `load_batch(batch_id)`

**Process:**
1. Scans batch directory for JSON files
2. Groups by `link_id`
3. Extracts content from `{batch_id}_ARTICLE_{link_id}_article.json`
4. Normalizes into research agent format

**Output Structure:**
```python
{
  "link_id": {
    "transcript": "# Markdown Content\n\n**Bold**...",  # Full markdown
    "comments": [],
    "metadata": {
      "title": "...",
      "source": "local_file",
      "word_count": 1234
    },
    "source": "article",
    "data_availability": {
      "has_transcript": True,
      "transcript_word_count": 1234
    }
  }
}
```

---

### 8. Phase 0 Summarization (`research/phases/phase0_prepare.py`)

**Key Method:** `execute()`

**Process:**
1. Receives batch data from DataLoader
2. Combines all transcripts into context
3. Sends to AI model (Qwen-flash) for summarization
4. **Markdown formatting is preserved** in the content sent to AI

**AI Input:**
```python
context = ""
for link_id, data in batch_data.items():
    if data.get("transcript"):
        context += f"\n\n--- Source: {data['metadata'].get('title')} ---\n\n"
        context += data["transcript"]  # Markdown content included here
```

**AI Output:**
- Structured summary with markers (Facts, Opinions, Data)
- Summary references the markdown content structure

---

### 9. Subsequent Phases

**Phase 0.5, 1, 2, 3, 4:**
- All phases receive the markdown content through the data loader
- Markdown formatting helps AI models understand document structure
- Headers, lists, tables are preserved for better semantic understanding

---

## Key Benefits of Markdown Format

1. **Structure Preservation:** Headers, lists, tables remain structured
2. **Better AI Understanding:** Models can parse markdown syntax for better comprehension
3. **Semantic Search:** Vector embeddings capture markdown structure
4. **Readability:** Human-readable format for debugging and inspection

## File Storage Structure

```
data/research/
  └── {session_id}/
      └── {batch_id}/
          ├── uploads/
          │   └── {uuid}.pdf              # Original PDF
          ├── prepared/
          │   └── {uuid}.md               # Converted Markdown
          └── manifest.json               # Metadata

data/research/batches/
  └── run_{batch_id}/
      └── {batch_id}_ARTICLE_{link_id}_article.json  # Scraper output
```

## Error Handling

1. **Converter Unavailable:** Falls back to plain text extraction using `pypdf`
2. **File Read Errors:** Article scraper handles encoding issues gracefully
3. **Missing Files:** Scrapers return error in standard format, workflow continues

## Dependencies

- **Frontend:** React file input (native)
- **Ingestion:** `utils/pdf_to_markdown.py` → `pymupdf`, `pdfplumber`
- **Scraping:** `ArticleScraper` handles `file://` URLs
- **Data Loading:** `ResearchDataLoader` reads JSON files
- **Summarization:** Phase 0+ processes markdown content

