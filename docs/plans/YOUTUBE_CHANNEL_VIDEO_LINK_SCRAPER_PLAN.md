# YouTube Channel Video Link Scraper Service Plan

## Overview

This document outlines the plan for implementing a backend service that uses Playwright to scrape video links from YouTube channels listed in `data/news/channels`. The service will filter videos by date range and save the links as batch-numbered text files.

**Status:** Planning Phase  
**Created:** 2025-01-20  
**Last Updated:** 2025-01-20

---

## Goals

1. **Scrape video links** from YouTube channels programmatically using Playwright
2. **Filter by date range** to collect videos published within specific time periods
3. **Batch management** with sequential batch numbering and timestamp tracking
4. **File output** in simple text format for easy consumption
5. **Integration** with existing backend architecture and patterns

---

## Scope

### In Scope
- Scraping video links from channel videos pages
- Date range filtering (start date to end date)
- Batch file generation with sequential numbering
- Support for all active channels in `data/news/channels`
- Error handling and partial batch completion
- Progress tracking (optional, following existing patterns)

### Out of Scope (Future Enhancements)
- Resume interrupted scrapes
- Incremental updates (only new videos since last scrape)
- Parallel channel processing
- Video metadata extraction (title, duration, views)
- Filter by category/priority from channels file
- Real-time WebSocket progress updates (can be added later)

---

## Architecture

### File Locations Summary

**⚠️ IMPORTANT: All production code is separate from test files.**

| Component | Location | Notes |
|-----------|----------|-------|
| YouTube Channel Scraper | `scrapers/youtube_channel_scraper.py` | Project root, alongside `youtube_scraper.py`, `bilibili_scraper.py`, etc. |
| Channel Scraper Service | `backend/app/services/channel_scraper_service.py` | Backend services folder, alongside `scraping_service.py`, `ingestion_service.py`, etc. |
| API Routes | `backend/app/routes/channel_scraper.py` | Backend routes folder, alongside `links.py`, `ingestion.py`, etc. |
| Test Files (optional) | `tests/test_youtube_channel_scraper.py`<br>`backend/tests/test_channel_scraper_service.py` | Separate test files, NOT production code |
| Output Files | `{config.channel_scraper.paths.batches_dir}/`<br>`{config.channel_scraper.paths.metadata_dir}/` | Paths from `config.yaml`, not hardcoded |

**Key Principle:** Production code lives in `scrapers/` and `backend/app/`. Test files (if created) are separate in `tests/` or `backend/tests/`.

### High-Level Flow

```
User Request (date range, optional channel filters)
    ↓
API Route (/api/channel-scraper/scrape)
    ↓
Channel Scraper Service
    ↓
Load channels from data/news/channels
    ↓
Filter active channels (active: true)
    ↓
For each channel (sequential processing):
    ↓
YouTube Channel Scraper (Playwright)
    ↓
Navigate to channel/videos page
    ↓
Scroll/load videos (handle pagination/infinite scroll)
    ↓
Extract video links + metadata
    ↓
Filter by date range
    ↓
Collect all links
    ↓
Generate batch ID
    ↓
Save to batch file (batch_001.txt, batch_002.txt, etc.)
    ↓
Save metadata JSON
```

### Component Structure

**Important:** The scraper and service code are **NOT** in the `tests/` folder. They are production code in their respective directories:

```
# Production scraper code (at project root, alongside other scrapers)
scrapers/
  youtube_channel_scraper.py          # Playwright-based channel scraper

# Backend service code (in backend/app/)
backend/
  app/
    services/
      channel_scraper_service.py      # Main orchestration service
    routes/
      channel_scraper.py              # FastAPI route handlers

# Output directories (paths from config.yaml)
{config.channel_scraper.paths.batches_dir}/    # From config.yaml
  batch_001_2025-01-20_14-30-00.txt
  batch_002_2025-01-20_15-45-00.txt

{config.channel_scraper.paths.metadata_dir}/   # From config.yaml
  batch_001_2025-01-20_14-30-00.json
  batch_002_2025-01-20_15-45-00.json

# Test files (separate, optional - not part of production code)
tests/
  test_youtube_channel_scraper.py     # Optional: unit tests for scraper
backend/tests/
  test_channel_scraper_service.py     # Optional: unit tests for service
```

**Key Points:**
- **Scraper implementation** goes in `scrapers/` folder (project root), alongside existing scrapers like `youtube_scraper.py`
- **Service implementation** goes in `backend/app/services/` folder
- **Route handlers** go in `backend/app/routes/` folder
- **Test files** (if created) go in `tests/` or `backend/tests/` - these are separate and optional
- All output paths are read from `config.yaml` - no hardcoded paths in the code

---

## Detailed Component Design

### 1. YouTube Channel Scraper (`scrapers/youtube_channel_scraper.py`)

**Location:** `scrapers/youtube_channel_scraper.py` (project root, NOT in tests folder)

This is production code that lives alongside other scrapers like `youtube_scraper.py`, `bilibili_scraper.py`, etc.

**Purpose:** Playwright-based scraper for extracting video links from YouTube channel pages.

#### Key Methods

**`scrape_channel_videos(channel_id: str, start_date: str, end_date: str) -> List[str]`**
- Navigate to `https://www.youtube.com/channel/{channel_id}/videos`
- Handle infinite scroll to load all videos
- Extract video links from page
- Parse publish dates and filter by date range
- Return list of video URLs

**`_scroll_and_load_videos(page: Page, max_scrolls: int) -> List[Dict]`**
- Scroll down incrementally to trigger lazy loading
- Wait for new videos to appear
- Extract video elements and metadata
- Stop when no new videos load or max scrolls reached

**`_extract_video_links(page: Page) -> List[Dict]`**
- Find all video link elements using Playwright selectors
- Extract: video URL, video ID, publish date (if available)
- Return list of video metadata dictionaries

**`_parse_publish_date(date_str: str) -> Optional[datetime]`**
- Parse YouTube relative dates ("2 days ago", "3 weeks ago")
- Convert to absolute datetime objects
- Handle edge cases (missing dates, invalid formats)

**`_filter_by_date_range(videos: List[Dict], start_date: datetime, end_date: datetime) -> List[str]`**
- Filter videos within date range (inclusive)
- Return list of video URLs

#### Playwright Strategy

1. **Page Navigation:**
   - Use `page.goto()` with wait for network idle
   - Wait for video grid container to load
   - Set viewport size (1920x1080 recommended)

2. **Infinite Scroll Handling:**
   - Scroll down incrementally (e.g., 500px per scroll)
   - Wait 1-2 seconds between scrolls (randomized)
   - Check for "No more videos" indicator
   - Track number of videos loaded to detect when scrolling stops
   - Maximum scroll attempts (configurable, default: 50)

3. **Video Link Extraction:**
   - Selector: `a#video-title-link` or `ytd-grid-video-renderer a#video-title`
   - Extract `href` attribute (may be relative, convert to absolute)
   - Extract video ID from URL
   - Try to extract publish date from video metadata element

4. **Date Extraction Challenges:**
   - YouTube shows relative dates in video grid
   - May need to click into video or parse from tooltip
   - Alternative: Use YouTube Data API v3 (requires API key, out of scope)
   - Fallback: Include all videos if date parsing fails (with warning)

5. **Stopping Conditions:**
   - Date range limit reached (all older videos filtered out)
   - No new videos load after N consecutive scrolls (default: 3)
   - Maximum videos limit reached (safety limit, default: 1000)
   - Maximum scroll attempts reached

#### Error Handling

- **Channel not found:** Log error, skip channel, continue with next
- **Network timeout:** Retry up to 3 times with exponential backoff
- **CAPTCHA/Blocking:** Log warning, skip channel, continue
- **Date parsing errors:** Log warning, include video in results (conservative approach)

### 2. Channel Scraper Service (`backend/app/services/channel_scraper_service.py`)

**Location:** `backend/app/services/channel_scraper_service.py` (in backend folder, NOT in tests)

This is production service code that lives alongside other services like `scraping_service.py`, `ingestion_service.py`, etc.

**Purpose:** Orchestrate channel scraping, batch management, and file output.

#### Service Initialization

The service should initialize with a `Config` instance to read all paths from `config.yaml`:

```python
from core.config import Config

class ChannelScraperService:
    def __init__(self):
        self.config = Config()
        # Read paths from config (with defaults as fallback)
        self.batches_dir = Path(self.config.get('channel_scraper.paths.batches_dir', 'data/channel_scrapes/batches'))
        self.metadata_dir = Path(self.config.get('channel_scraper.paths.metadata_dir', 'data/channel_scrapes/metadata'))
        self.channels_file = Path(self.config.get('channel_scraper.channels_file', 'data/news/channels'))
        
        # Ensure directories exist
        self.batches_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
```

This ensures all paths are configurable and not hardcoded, following the same pattern as `storage.paths` in the existing configuration.

#### Key Methods

**`load_channels() -> List[Dict]`**
- Read channels file path from config: `Config.get('channel_scraper.channels_file', 'data/news/channels')`
- Read channels file (JSON format)
- Filter channels where `active: true`
- Return list of channel dictionaries

**`scrape_channels(date_range: Dict, channel_filters: Optional[List[str]] = None) -> Dict`**
- Load active channels
- Optionally filter by channel IDs if provided
- For each channel:
  - Call YouTube Channel Scraper
  - Collect video links
  - Apply random delay between channels (0-2 seconds)
- Generate batch ID
- Save batch file and metadata
- Return batch information

**`generate_batch_id() -> str`**
- Read existing batch files to determine next number
- Format: `batch_{number:03d}_{timestamp}`
- Example: `batch_001_2025-01-20_14-30-00`

**`save_batch_file(batch_id: str, links: List[str], metadata: Dict) -> Tuple[str, str]`**
- Read output paths from `config.yaml` using `Config.get('channel_scraper.paths.batches_dir')` and `Config.get('channel_scraper.paths.metadata_dir')`
- Save links to `{batches_dir}/{batch_id}.txt`
- Save metadata to `{metadata_dir}/{batch_id}.json`
- Return paths to both files

**`_get_next_batch_number() -> int`**
- Read batches directory path from config: `Config.get('channel_scraper.paths.batches_dir')`
- Scan batches directory for existing batch files
- Find highest batch number
- Return next number (highest + 1)

#### Rate Limiting & Delays

- **Between channels:** Random delay between 0-2 seconds
  - Use `random.uniform(0, 2)` for randomization
  - Helps avoid rate limiting while keeping throughput reasonable
- **Between scrolls:** Random delay between 1-2 seconds (in scraper)
- **Retry backoff:** Exponential backoff for failed requests (1s, 2s, 4s)

### 3. API Route (`backend/app/routes/channel_scraper.py`)

**Location:** `backend/app/routes/channel_scraper.py` (in backend folder, NOT in tests)

This is production API code that lives alongside other routes like `links.py`, `ingestion.py`, etc.

**Purpose:** FastAPI endpoints for triggering scrapes and retrieving results.

#### Endpoints

**`POST /api/channel-scraper/scrape`**
- **Request Body:**
  ```json
  {
    "start_date": "2025-01-01",
    "end_date": "2025-01-15",
    "channel_ids": []  // Optional: filter specific channels
  }
  ```
- **Response:**
  ```json
  {
    "batch_id": "batch_001",
    "status": "started",
    "timestamp": "2025-01-20T14:30:00"
  }
  ```
- **Behavior:**
  - Validate date format
  - Trigger async scraping task
  - Return immediately with batch ID

**`GET /api/channel-scraper/batches`**
- **Response:**
  ```json
  {
    "batches": [
      {
        "batch_id": "batch_001",
        "timestamp": "2025-01-20T14:30:00",
        "date_range": {
          "start": "2025-01-01",
          "end": "2025-01-15"
        },
        "total_videos": 150,
        "channels_scraped": 25
      }
    ]
  }
  ```
- **Behavior:**
  - List all batch metadata files
  - Return summary information

**`GET /api/channel-scraper/batches/{batch_id}`**
- **Response:**
  ```json
  {
    "batch_id": "batch_001",
    "timestamp": "2025-01-20T14:30:00",
    "date_range": {
      "start": "2025-01-01",
      "end": "2025-01-15"
    },
    "channels_scraped": 25,
    "total_videos": 150,
    "channels": [
      {
        "name": "3Blue1Brown",
        "channelId": "UCYO_jab_esuFRV4b17AJtAw",
        "videos_found": 12,
        "status": "success"
      }
    ]
  }
  ```
- **Behavior:**
  - Load metadata JSON for specific batch
  - Return full metadata

**`GET /api/channel-scraper/batches/{batch_id}/links`**
- **Response:** Plain text file download
- **Behavior:**
  - Return links file as downloadable text
  - Content-Type: `text/plain`

---

## Data Models

### Batch File Format (TXT)

```
# Batch: batch_001
# Scraped: 2025-01-20 14:30:00
# Date Range: 2025-01-01 to 2025-01-15
# Total Videos: 150

https://www.youtube.com/watch?v=VIDEO_ID_1
https://www.youtube.com/watch?v=VIDEO_ID_2
https://www.youtube.com/watch?v=VIDEO_ID_3
...
```

**Format Rules:**
- Header comments with batch info
- One video URL per line
- No empty lines between URLs
- URLs are absolute YouTube watch URLs

### Metadata File Format (JSON)

```json
{
  "batch_id": "batch_001",
  "timestamp": "2025-01-20T14:30:00",
  "date_range": {
    "start": "2025-01-01",
    "end": "2025-01-15"
  },
  "channels_scraped": 25,
  "total_videos": 150,
  "channels": [
    {
      "name": "3Blue1Brown",
      "channelId": "UCYO_jab_esuFRV4b17AJtAw",
      "handle": "@3blue1brown",
      "videos_found": 12,
      "status": "success",
      "error": null
    },
    {
      "name": "ABC News",
      "channelId": "UCBi2mrWuNuyYy4gbM6fU18Q",
      "handle": "@ABCNews",
      "videos_found": 0,
      "status": "failed",
      "error": "Channel not found"
    }
  ],
  "errors": [
    {
      "channel": "ABC News",
      "error": "Channel not found"
    }
  ]
}
```

---

## Configuration

### Add to `config.yaml`

```yaml
channel_scraper:
  # Path configuration for batch and metadata directories
  # These paths are relative to project root
  paths:
    batches_dir: 'data/channel_scrapes/batches'      # Where batch files are saved
    metadata_dir: 'data/channel_scrapes/metadata'    # Where metadata JSON files are saved
  channels_file: 'data/news/channels'                 # Path to channels JSON file
  # Scraping configuration
  scroll_delay_min: 1.0      # Minimum seconds between scrolls
  scroll_delay_max: 2.0      # Maximum seconds between scrolls
  channel_delay_min: 0.0     # Minimum seconds between channels
  channel_delay_max: 2.0     # Maximum seconds between channels
  max_scrolls: 50            # Maximum scroll attempts per channel
  videos_per_channel_limit: 1000  # Safety limit per channel
  request_timeout: 60000     # Playwright timeout in milliseconds
  max_retries: 3             # Retry attempts for failed requests
  retry_backoff_base: 1.0   # Base delay for exponential backoff (seconds)
```

**Implementation Note:** The service should use the `Config` class to read all paths:

```python
from core.config import Config

config = Config()
batches_dir = config.get('channel_scraper.paths.batches_dir', 'data/channel_scrapes/batches')
metadata_dir = config.get('channel_scraper.paths.metadata_dir', 'data/channel_scrapes/metadata')
channels_file = config.get('channel_scraper.channels_file', 'data/news/channels')
```

This ensures paths are configurable and not hardcoded, following the same pattern as `storage.paths` in the existing configuration.

### Environment Variables

- `PLAYWRIGHT_BROWSERS_PATH` (optional): Custom browser installation path

---

## Implementation Steps

### Phase 1: Core Scraper (Week 1)

1. **Create YouTube Channel Scraper**
   - **Location:** `scrapers/youtube_channel_scraper.py` (project root, NOT in tests)
   - Implement `youtube_channel_scraper.py` in the `scrapers/` folder
   - Basic page navigation and video link extraction
   - Infinite scroll handling
   - Date parsing (basic relative date support)

2. **Testing**
   - Create test file in `tests/test_youtube_channel_scraper.py` (optional, separate from production code)
   - Test with single channel
   - Verify link extraction
   - Test scroll behavior

### Phase 2: Service Layer (Week 1-2)

3. **Create Channel Scraper Service**
   - **Location:** `backend/app/services/channel_scraper_service.py` (in backend folder, NOT in tests)
   - Implement `channel_scraper_service.py` in the `backend/app/services/` folder
   - Initialize with `Config` class to read paths from `config.yaml`
   - Channel loading and filtering
   - Batch ID generation
   - File output (TXT and JSON) using paths from config

4. **Testing**
   - Create test file in `backend/tests/test_channel_scraper_service.py` (optional, separate from production code)
   - Test batch file generation
   - Test metadata creation
   - Test with multiple channels

### Phase 3: API Integration (Week 2)

5. **Create API Route**
   - **Location:** `backend/app/routes/channel_scraper.py` (in backend folder, NOT in tests)
   - Implement `channel_scraper.py` route in the `backend/app/routes/` folder
   - All four endpoints
   - Request validation
   - Error handling

6. **Testing**
   - Test API endpoints (can use existing test patterns in `tests/` or `backend/tests/`)
   - Test date range filtering
   - Test error scenarios

### Phase 4: Date Filtering Enhancement (Week 2-3)

7. **Improve Date Parsing**
   - Robust relative date parsing
   - Handle edge cases
   - Timezone handling

8. **Testing**
   - Test various date formats
   - Test date range edge cases
   - Test with real channel data

### Phase 5: Polish & Documentation (Week 3)

9. **Error Handling**
   - Comprehensive error handling
   - Logging improvements
   - User-friendly error messages

10. **Documentation**
    - API documentation
    - Usage examples
    - Troubleshooting guide

---

## Technical Considerations

### Rate Limiting

- **Random delays:** 0-2 seconds between channels, 1-2 seconds between scrolls
- **Respect YouTube limits:** Avoid aggressive scraping patterns
- **Retry logic:** Exponential backoff for transient failures
- **Circuit breaker:** Skip channel after repeated failures

### Error Handling

- **Channel-level errors:** Log error, skip channel, continue with others
- **Partial batch saves:** Save what was collected even if some channels fail
- **Network timeouts:** Retry with exponential backoff
- **Date parsing failures:** Include video in results with warning (conservative)

### Performance

- **Sequential processing:** Process channels one at a time to avoid rate limiting
- **Async/await:** Use async where possible for I/O operations
- **Progress tracking:** Optional WebSocket updates (can be added later)

### Date Range Filtering

- **Relative date parsing:** Convert "2 days ago" to absolute dates
- **Timezone handling:** Use UTC for consistency
- **Edge cases:** Handle videos without dates, invalid dates
- **Inclusive ranges:** Include videos on start and end dates

### Browser Management

- **Playwright context:** Reuse browser context across channels
- **Resource cleanup:** Properly close browsers and pages
- **Memory management:** Avoid memory leaks with long-running scrapes

---

## Dependencies

### New Dependencies

- `playwright` (already in project)
- `python-dateutil` (for robust date parsing)

### Existing Dependencies (No Changes)

- `fastapi` (API framework)
- `loguru` (logging)
- `pydantic` (data validation)

---

## Testing Strategy

### Unit Tests

- Date parsing functions
- Batch ID generation
- File output formatting
- Channel filtering logic

### Integration Tests

- End-to-end scraping with mock YouTube pages
- Date range filtering with various inputs
- Error handling scenarios
- Batch file generation

### Manual Testing

- Test with real YouTube channels
- Verify date range filtering accuracy
- Test with large date ranges
- Test error recovery

---

## Security Considerations

- **No authentication required:** Service is internal/backend-only
- **Input validation:** Validate date formats and channel IDs
- **Path traversal prevention:** Sanitize batch IDs and file paths
- **Resource limits:** Enforce maximum videos per channel

---

## Monitoring & Logging

### Logging Points

- Start/end of channel scraping
- Number of videos found per channel
- Errors and warnings
- Batch file creation
- Performance metrics (time per channel, total time)

### Log Levels

- **INFO:** Normal operation (channel start, batch creation)
- **WARNING:** Non-fatal issues (date parsing failures, skipped videos)
- **ERROR:** Fatal issues (channel not found, network errors)

---

## Future Enhancements

1. **Resume interrupted scrapes:** Save progress and resume from last channel
2. **Incremental updates:** Only scrape new videos since last batch
3. **Parallel processing:** Process multiple channels with rate limiting
4. **Video metadata:** Extract title, duration, views, description
5. **Category filtering:** Filter channels by category from channels file
6. **Priority-based scraping:** Process high-priority channels first
7. **WebSocket progress:** Real-time progress updates to frontend
8. **Scheduled scraping:** Automatic daily/weekly scraping jobs
9. **YouTube Data API integration:** Use official API for better date accuracy
10. **Export formats:** Support CSV, JSON, and other formats

---

## Open Questions

1. **Date accuracy:** How to handle videos without publish dates?
   - **Decision:** Include in results with warning (conservative approach)

2. **Batch size limits:** Should there be a maximum videos per batch?
   - **Decision:** No hard limit, but safety limit per channel (1000)

3. **Concurrent processing:** Should channels be processed in parallel?
   - **Decision:** Sequential for now to avoid rate limiting (can be enhanced later)

4. **Progress tracking:** Should we implement WebSocket progress updates?
   - **Decision:** Optional enhancement, not in initial implementation

---

## Success Criteria

- ✅ Successfully scrape video links from all active channels
- ✅ Filter videos by date range accurately
- ✅ Generate batch files with proper numbering
- ✅ Handle errors gracefully without stopping entire batch
- ✅ Complete scraping of 100+ channels within reasonable time (< 2 hours)
- ✅ Zero data loss (all found videos saved to batch file)

---

## References

- Existing scraper patterns: `scrapers/youtube_scraper.py`
- Service patterns: `backend/app/services/scraping_service.py`
- API patterns: `backend/app/routes/links.py`
- Channel data: `data/news/channels` (path configurable via `config.channel_scraper.channels_file`)
- Config management: `core/config.py` (use `Config.get()` to read all paths from `config.yaml`)

---

## Appendix: Example Usage

### API Request

```bash
curl -X POST http://localhost:3001/api/channel-scraper/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-01",
    "end_date": "2025-01-15"
  }'
```

### Response

```json
{
  "batch_id": "batch_001",
  "status": "started",
  "timestamp": "2025-01-20T14:30:00"
}
```

### Retrieve Batch

```bash
curl http://localhost:3001/api/channel-scraper/batches/batch_001
```

### Download Links

```bash
curl http://localhost:3001/api/channel-scraper/batches/batch_001/links > batch_001_links.txt
```

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-20

