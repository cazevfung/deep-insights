# YouTube Scraper Failure Investigation

## Problem
YouTube scraper is **failing in localhost:3000** (web server) but **working in test_youtube_scraper.py**.

## Investigation Summary

### Code Flow Comparison

#### Test File (`tests/test_youtube_scraper.py`)
```python
# 1. Create scraper ONCE
scraper = YouTubeScraper(headless=False)

# 2. Reuse same scraper for all links
for link in yt_links:
    result = scraper.extract(url, batch_id=batch_id, link_id=link_id)

# 3. Close scraper at end
scraper.close()
```

#### Web Server Flow (`localhost:3000`)
1. **Entry Point**: `backend/app/routes/workflow.py` → `start_workflow()`
2. **Service**: `backend/app/services/workflow_service.py` → `run_workflow()`
3. **Execution**: Calls `run_all_scrapers_direct()` via `asyncio.to_thread()`
4. **Scraper Creation**: `backend/lib/workflow_direct.py` → `_run_scraper_for_link()`

```python
# In workflow_direct.py - _run_scraper_for_link()
def _run_scraper_for_link(...):
    # Creates NEW scraper for EACH link
    scraper = scraper_class(progress_callback=progress_callback, **scraper_kwargs)
    result = scraper.extract(url, batch_id=batch_id, link_id=link_id)
    scraper.close()  # Closes immediately after each link
```

### Key Differences Identified

#### 1. **Scraper Lifecycle**
- **Test**: One scraper instance reused for all links
- **Web Server**: New scraper instance created and closed for each link

#### 2. **Execution Context**
- **Test**: Runs in main thread (synchronous)
- **Web Server**: Runs in thread pool via `asyncio.to_thread()` (async → sync bridge)

#### 3. **Progress Callback**
- **Test**: No progress callback
- **Web Server**: Progress callback passed to scraper (used for WebSocket updates)

#### 4. **Browser Context Management**
- **Test**: Single browser instance shared across extractions
- **Web Server**: Browser created/destroyed per link via `_create_context()` → `close()`

### Potential Root Causes

#### **Issue #1: Browser Context Lifecycle in Threads**
When running in `asyncio.to_thread()`, Playwright's browser context creation might behave differently:
- `BaseScraper._create_context()` creates a new context each time
- Context is closed immediately after extraction (`scraper.close()`)
- Thread context might affect Playwright's browser initialization

**Location**: `scrapers/base_scraper.py` lines 221-249

#### **Issue #2: Context Reuse vs New Context**
In test file:
- First call to `_create_context()` initializes Playwright and browser
- Subsequent calls reuse the same browser instance
- Context is only closed at the end

In web server:
- Each link gets a fresh browser context
- Browser might be closing before transcript fully loads
- No shared state between extractions

#### **Issue #3: Threading + Playwright Interaction**
Playwright's `sync_playwright()` may have issues when:
- Called from within a thread created by `asyncio.to_thread()`
- Browser contexts are created/destroyed rapidly
- Multiple contexts compete for resources

**Location**: `scrapers/base_scraper.py` lines 157-219 (`_init_playwright()`)

#### **Issue #4: Progress Callback Timing**
The progress callback might be interfering with extraction:
- Callback is called during extraction (lines 138-364 in youtube_scraper.py)
- Callback queues messages for async processing
- Thread synchronization might cause race conditions

**Location**: `scrapers/youtube_scraper.py` - multiple `_report_progress()` calls

#### **Issue #5: Timeout Behavior in Thread Context**
Timeouts might behave differently:
- `page.wait_for_selector()` with timeout=10000 might fail faster in thread context
- YouTube page might not fully load before transcript extraction starts
- `time.sleep()` calls might not work as expected in thread pool

**Location**: `scrapers/youtube_scraper.py` lines 139-283

### Specific Failure Points in YouTube Scraper

Based on the code flow, likely failure points:

1. **Line 139**: `page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)`
   - Page might not fully load in thread context
   - `domcontentloaded` might fire before JavaScript executes

2. **Line 168-289**: Transcript button clicking
   - Multiple selectors tried sequentially
   - Button might not be visible/clickable in thread context
   - Timing issues with `time.sleep()` calls

3. **Line 177**: `page.wait_for_selector('ytd-transcript-segment-renderer', timeout=5000)`
   - Selector might not appear in time
   - Thread context might affect selector detection

4. **Line 134**: `context = self._create_context()`
   - Context creation might fail or timeout in thread
   - Browser initialization might be incomplete

### Recommended Investigation Steps

1. **Add logging** to track where exactly the failure occurs:
   - Log before/after `_create_context()`
   - Log before/after `page.goto()`
   - Log before/after transcript button click
   - Log before/after segment extraction

2. **Check error messages** in web server logs:
   - Look for specific Playwright errors
   - Check for timeout exceptions
   - Look for context creation failures

3. **Test scraper lifecycle**:
   - Try creating scraper once and reusing (like test)
   - Try delaying `close()` call
   - Try removing progress callback

4. **Test threading behavior**:
   - Run test in thread to see if it fails
   - Check if Playwright works in `asyncio.to_thread()` context

5. **Check browser configuration**:
   - Verify `headless=False` is working in web server
   - Check if browser window actually opens
   - Verify browser instance is properly initialized

### Files to Review

1. `scrapers/youtube_scraper.py` - Main extraction logic
2. `scrapers/base_scraper.py` - Browser initialization and context creation
3. `backend/lib/workflow_direct.py` - Scraper execution in web server
4. `backend/app/services/workflow_service.py` - Workflow orchestration
5. `tests/test_youtube_scraper.py` - Working test implementation

### Next Steps

1. **Add detailed logging** to identify exact failure point
2. **Compare browser state** between test and web server
3. **Test scraper reuse** in web server context
4. **Check Playwright version compatibility** with threading
5. **Verify timeout values** are appropriate for thread context

