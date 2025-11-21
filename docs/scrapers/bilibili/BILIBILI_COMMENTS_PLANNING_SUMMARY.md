# Bilibili Comments Scraper - Planning Summary

## Overview

A comprehensive plan has been created for implementing a Bilibili comments scraper that allows flexible cookie management for future client app integration.

## Key Features

### 1. **Flexible Cookie Management**
- Cookies stored in separate JSON file (`data/cookies/bilibili_cookies.json`)
- Easy to update without touching code or main config
- Fallback to config.yaml if file doesn't exist
- Compatible with browser extension exports

### 2. **Separate from Existing Bilibili Scraper**
- Current `BilibiliScraper`: Video transcription via browser automation
- New `BilibiliCommentsScraper`: Comment extraction via API
- Different use cases, different methods

### 3. **Comprehensive Comment Data**
Extracts:
- Comment ID, Author, Author ID
- Timestamp (both raw and readable)
- IP Location (when available)
- Like counts
- Content text
- Video information
- Page number

### 4. **Configuration**
```yaml
# config.yaml
scrapers:
  bilibili_comments:
    headless: false
    timeout: 30000
    max_comments_per_page: 20
    max_pages: 30
    cookie_source: 'file'  # 'file' or 'config'
    cookie_file: 'data/cookies/bilibili_cookies.json'
    sort_mode: 3  # 3=hot, 2=new
    num_workers: 3
```

### 5. **API-Based Approach**
- Uses Bilibili API endpoint: `https://api.bilibili.com/x/v2/reply`
- Fast and efficient (no browser automation needed)
- Supports pagination (up to 30 pages by default)
- Can handle 600+ comments per video

## Architecture Decisions

### Why Separate Cookie File?
1. **Easy Updates**: Users can export cookies from browser and drop into file
2. **No Code Changes**: Update cookie without touching Python code
3. **Client App Ready**: Future app can provide UI to upload cookie JSON
4. **Security**: Cookies not in version control (file can be gitignored)

### Cookie Format
Uses standard JSON format compatible with browser extensions:
```json
[
  {
    "domain": ".bilibili.com",
    "name": "SESSDATA",
    "value": "...",
    "path": "/",
    "secure": true,
    "httpOnly": true
  }
]
```

Your provided cookie data is already in this format - perfect fit!

## Implementation Plan

### File Structure
```
scrapers/
  └── bilibili_comments_scraper.py  # NEW
tests/
  └── test_bilibili_comments.py     # NEW
config.yaml                          # UPDATE
data/
  └── cookies/
      └── bilibili_cookies.json      # NEW (for your cookie)
```

### Key Methods

1. **`_load_cookies()`**: Load from JSON file or config
2. **`_parse_cookies_to_string()`**: Convert JSON array to cookie header
3. **`_extract_video_id()`**: Parse BV/AV from URL
4. **`_bv_to_av()`**: Convert BV to AV ID (API uses AV)
5. **`_fetch_comments_page()`**: Fetch one page from API
6. **`_parse_comment_data()`**: Extract fields from API response
7. **`_trans_date()`**: Convert 10-digit timestamp to readable date

### API Integration

**Endpoint**: `https://api.bilibili.com/x/v2/reply`

**Key Parameters**:
- `oid`: AV ID (not BV)
- `pn`: Page number (1-based)
- `ps`: Page size (20 comments)
- `mode`: 3 = hot, 2 = new

**Critical Headers**:
- `cookie`: Session cookies (required for IP location data)
- `referer`: Video page URL

## Output Format

Returns structured data with:
```python
{
    'success': True/False,
    'url': str,
    'content': str,  # All comments as text
    'comments': list,  # Individual comment dicts
    'total_comments': int,
    'video_info': {...},
    'extraction_timestamp': str,
    ...
}
```

## Usage Example (Planned)

```python
from scrapers.bilibili_comments_scraper import BilibiliCommentsScraper

scraper = BilibiliCommentsScraper()

# Single video
result = scraper.extract('BV1DP411g7jx')

# Multiple videos
urls = ['BV1DP411g7jx', 'BV1M24y117K3']
results = []
for url in urls:
    result = scraper.extract(url)
    results.append(result)
```

## Cookie Management Workflow

### Current (Planning Phase)
1. Cookie data provided in JSON format ✅
2. Plan to store in `data/cookies/bilibili_cookies.json`

### Future (Client App)
1. User exports cookies from browser
2. Uploads via client app UI
3. App validates and saves to `bilibili_cookies.json`
4. Scraper automatically picks up updated cookies

### Manual Update
1. Export cookies from browser (extension)
2. Replace `data/cookies/bilibili_cookies.json`
3. Restart scraper

## Comparison with Reference Article

| Feature | Reference Article | Our Implementation |
|---------|-------------------|---------------------|
| Cookie Storage | Hardcoded | Separate JSON file |
| Cookie Updates | Edit code | Update JSON file |
| Multiple Videos | Supported | Supported |
| Pagination | Supported | Supported (configurable) |
| Timestamp Conversion | Yes | Yes |
| IP Location | Yes | Yes |
| Output Format | CSV | JSON + configurable |

## Benefits of This Design

1. **Maintainability**: Clear separation of concerns
2. **Flexibility**: Easy cookie updates
3. **Extensibility**: Ready for client app
4. **Consistency**: Matches existing scraper patterns
5. **User-Friendly**: Simple workflow for updates

## Testing Strategy

1. **Unit Tests**: Cookie parsing, BV→AV conversion
2. **Integration Tests**: API requests with valid cookie
3. **Error Tests**: Invalid cookie, invalid URL, rate limiting
4. **Pagination Tests**: Multiple pages, empty comments

## Next Steps

1. ✅ Planning completed (this document)
2. ⏳ Implementation (awaiting approval)
3. ⏳ Testing with provided cookie
4. ⏳ Documentation

## Files Created

1. **`docs/implementation/BILIBILI_COMMENTS_SCRAPER_PLAN.md`**
   - Complete implementation plan
   - API details
   - Method signatures
   - Error handling

2. **`docs/BILIBILI_COMMENTS_PLANNING_SUMMARY.md`** (this file)
   - Executive summary
   - Key decisions
   - Usage examples

## Questions to Consider

1. Should we support nested reply comments? (Currently planned as flat list)
2. Should we implement rate limiting delays? (Recommend 0.5-1s between requests)
3. Should we cache results to avoid re-scraping? (Could add later)
4. Should we support export to CSV/Excel? (Currently JSON only)

## Ready for Implementation

All planning is complete. The implementation can begin once approved. Key points:

- ✅ Cookie management strategy defined
- ✅ API integration plan ready
- ✅ Data structure planned
- ✅ Configuration structure designed
- ✅ Error handling planned
- ✅ Testing strategy defined

The plan is comprehensive and ready for implementation!








