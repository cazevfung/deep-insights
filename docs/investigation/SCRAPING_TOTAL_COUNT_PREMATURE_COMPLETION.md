# Scraping Total Count Premature Completion Investigation

## Problem Summary

The scraping process incorrectly determines completion because the total task count is calculated dynamically based on **started** tasks rather than **expected** tasks. This causes premature transition to Phase 2 (research) when some scrapers haven't even started processing their links yet.

## Root Cause Analysis

### How Total Count is Currently Calculated

**Location:** `backend/app/services/progress_service.py` line 209

```python
async def _update_batch_status(self, batch_id: str):
    """Calculate and broadcast batch-level status."""
    if batch_id not in self.link_states:
        return
    
    links = self.link_states[batch_id]
    
    total = len(links)  # ❌ PROBLEM: Only counts registered links
    completed = sum(1 for l in links.values() if ... == 'completed')
    failed = sum(1 for l in links.values() if ... == 'failed')
```

**Issue:** `total = len(links)` only counts links that have been **registered** in `link_states`, not the actual total expected.

### How Links Are Registered

**Location:** `backend/app/services/progress_service.py` lines 70-79

Links are registered **lazily** when they start processing:

```python
async def update_link_progress(self, ...):
    # Update in-memory state
    if batch_id not in self.link_states:
        self.link_states[batch_id] = {}
    
    if link_id not in self.link_states[batch_id]:  # ❌ Only registered when started
        self.link_states[batch_id][link_id] = {
            'url': url,
            'status': 'pending',
            'started_at': datetime.now().isoformat(),
        }
```

### Parallel Scraper Execution

**Location:** `backend/lib/workflow_direct.py` lines 469-485

Multiple scrapers run in parallel threads:

```python
# Run scrapers in parallel (one thread per scraper type)
with ThreadPoolExecutor(max_workers=len(active_configs)) as executor:
    futures = []
    
    for config in active_configs:
        future = executor.submit(
            _run_scraper_type,
            config['scraper_class'],
            config['scraper_name'],
            config['link_type'],
            batch_id,
            config['links'],
            progress_callback,
            **config['kwargs']
        )
        futures.append((future, config))
```

**Problem:** Each scraper type processes its links sequentially, but scrapers start at different times:
- Fast scrapers (e.g., YouTube) might finish all links quickly
- Slow scrapers (e.g., Bilibili with video download) take longer to start
- Comments scrapers might start even later

### Total Links Discovery

**Location:** `backend/lib/workflow_direct.py` lines 399-406

The system DOES discover the total upfront:

```python
total_links = sum(len(links) for links in link_types.values())

if progress_callback:
    progress_callback({
        'type': 'scraping:discover',
        'message': f'发现 {total_links} 个链接',
        'total_links': total_links  # ✅ Total is known upfront
    })
```

**But:** This `total_links` value is only sent as a message (`scraping:discover`), not used to initialize the progress tracker.

### Completion Check Logic

**Location:** `client/src/pages/ScrapingProgressPage.tsx` lines 294-300

```typescript
if (
  scrapingStatus.total > 0 &&
  scrapingStatus.completed + scrapingStatus.failed === scrapingStatus.total
) {
  setCurrentPhase('research')  // ❌ Premature transition!
}
```

**Location:** `client/src/hooks/useWorkflowStep.ts` lines 42-44

```typescript
const scrapingComplete =
  scrapingStatus.total > 0 &&
  scrapingStatus.completed + scrapingStatus.failed === scrapingStatus.total
```

## The Problem Flow

1. **Initial State:**
   - `scraping:discover` message sent with `total_links: 31`
   - But `progress_service.link_states[batch_id]` is empty
   - `total = 0` (no links registered yet)

2. **Scraper A Starts (Fast - YouTube):**
   - Processes 18 links quickly
   - Each link registers when it starts: `link_states[batch_id][link_id] = {...}`
   - All 18 links complete quickly
   - `total = 18` (only registered links)
   - `completed = 18`, `failed = 0`
   - `completed + failed === total` → **TRUE** ✅

3. **Scraper B Hasn't Started Yet (Slow - Bilibili):**
   - Still initializing browser/Playwright
   - Links not registered yet (they register when processing starts)
   - But system thinks scraping is complete!

4. **Premature Transition:**
   - Frontend sees `completed + failed === total` (18/18)
   - Moves to research phase
   - Scraper B's links haven't even started!

## Evidence from Code

### Total Count Calculation
- **File:** `backend/app/services/progress_service.py:209`
- **Code:** `total = len(links)` where `links = self.link_states[batch_id]`
- **Problem:** Only counts registered links, not expected links

### Link Registration
- **File:** `backend/app/services/progress_service.py:74-79`
- **Code:** Links registered only when `update_link_progress()` or `update_link_status()` is called
- **Problem:** Registration happens when link **starts**, not upfront

### Total Discovery
- **File:** `backend/lib/workflow_direct.py:399-406`
- **Code:** `total_links` calculated and sent in `scraping:discover` message
- **Problem:** Not used to initialize progress tracker

### Completion Check
- **File:** `client/src/pages/ScrapingProgressPage.tsx:295-296`
- **Code:** `scrapingStatus.completed + scrapingStatus.failed === scrapingStatus.total`
- **Problem:** Uses dynamic total that doesn't include unstarted links

## Impact

1. **Premature Phase Transition:** System moves to research phase before all scraping tasks complete
2. **Missing Data:** Some links never get scraped because system thinks it's done
3. **Incomplete Results:** Research phase starts with incomplete data set
4. **User Confusion:** UI shows "completed" but scraping is still running in background

## Proposed Solution (Not Implemented)

### Option 1: Pre-register All Expected Links

When `scraping:discover` message is received:
1. Extract `total_links` from message
2. Load all expected links from `TestLinksLoader`
3. Pre-register all links in `progress_service.link_states[batch_id]` with status `'pending'`
4. Then `total = len(links)` will always reflect the actual total

**Implementation Points:**
- Handle `scraping:discover` message in `workflow_service.py`
- Call a new method `progress_service.initialize_expected_links(batch_id, total_links, links)`
- Pre-register all links with status `'pending'`

### Option 2: Store Expected Total Separately

Add `expected_total` field to progress service:
1. Set `expected_total` when `scraping:discover` is received
2. Use `expected_total` for completion check instead of `len(links)`
3. Keep `len(links)` for current progress display

**Implementation Points:**
- Add `expected_totals: Dict[str, int]` to `ProgressService`
- Update when `scraping:discover` received
- Use in `_update_batch_status()` for completion calculation

### Option 3: Wait for All Scrapers to Start

Track which scrapers have started:
1. When `scraping:start_type` is received, mark scraper as started
2. Only consider scraping complete when:
   - All expected scrapers have started AND
   - All registered links are completed/failed

**Implementation Points:**
- Track `started_scrapers: Set[str]` per batch
- Compare with `active_configs` from `workflow_direct.py`
- Update completion logic

## Recommended Approach

**Option 1 (Pre-register All Links)** is the cleanest solution because:
- ✅ Ensures `total` always reflects actual expected count
- ✅ Links show up in UI immediately (even if pending)
- ✅ No changes needed to completion check logic
- ✅ Clear separation: expected vs. actual progress

## Files That Need Changes

1. **`backend/app/services/progress_service.py`**
   - Add `initialize_expected_links()` method
   - Pre-register all links with status `'pending'`

2. **`backend/app/services/workflow_service.py`**
   - Handle `scraping:discover` message
   - Load links from `TestLinksLoader`
   - Call `initialize_expected_links()`

3. **`backend/lib/workflow_direct.py`**
   - Ensure `scraping:discover` includes link details (or link IDs)
   - Or ensure `TestLinksLoader` is accessible from `workflow_service`

## Testing Considerations

After fix, verify:
1. Total count matches expected links from start
2. Completion check waits for all links (including unstarted ones)
3. UI shows correct progress even when some scrapers haven't started
4. Phase transition only happens when ALL links are done

