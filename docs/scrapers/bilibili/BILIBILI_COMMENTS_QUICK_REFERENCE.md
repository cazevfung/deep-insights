# Bilibili Comments Scraper - Quick Reference

## One-Sentence Summary
A new scraper that extracts comments from Bilibili videos using the API, with cookies stored in a separate JSON file for easy updates.

## Architecture

```
User Input (BV URL)
    ↓
BilibiliCommentsScraper
    ↓
Load Cookies (from JSON file)
    ↓
Convert BV → AV ID
    ↓
Fetch Comments from API (paginated)
    ↓
Parse & Extract Data
    ↓
Return Structured Results
```

## Cookie Management (Key Feature)

### Current Approach
- Cookies stored in: `data/cookies/bilibili_cookies.json`
- Format: Standard JSON (compatible with browser extensions)
- Update method: Replace JSON file

### Why This Design?
✅ Easy updates without code changes  
✅ Compatible with future client app  
✅ Users can export from browser directly  
✅ Security: cookies not in version control  

## Configuration

**Location**: `config.yaml`
```yaml
scrapers:
  bilibili_comments:
    cookie_source: 'file'
    cookie_file: 'data/cookies/bilibili_cookies.json'
    max_pages: 30  # Pages to scrape
    sort_mode: 3    # 3=hot, 2=new
```

## Data Extracted

| Field | Description | Example |
|-------|-------------|---------|
| `comment_id` | Comment ID | 12345 |
| `author` | Username | "用户123" |
| `author_id` | UID | 67890 |
| `content` | Comment text | "太棒了！" |
| `likes` | Like count | 42 |
| `comment_time` | 10-digit timestamp | 1672531200 |
| `comment_time_readable` | Human-readable | "2023-01-01 12:00:00" |
| `ip_location` | IP location | "上海" |
| `page_number` | Page number | 1 |
| `video_url` | Full URL | "https://..." |

## API Details

**Endpoint**: `https://api.bilibili.com/x/v2/reply`

**Critical Parameters**:
- `oid`: AV ID (converted from BV)
- `pn`: Page number (1-based)
- `ps`: Page size (20 comments)
- `mode`: 3=hot, 2=new

**Critical Headers**:
- `cookie`: Required for IP location data
- `referer`: Video page URL

## Quick Usage (Planned)

```python
from scrapers.bilibili_comments_scraper import BilibiliCommentsScraper

# Initialize
scraper = BilibiliCommentsScraper()

# Scrape single video
result = scraper.extract('https://www.bilibili.com/video/BV1DP411g7jx')

# Access results
print(f"Total comments: {result['total_comments']}")
print(f"Comments: {result['comments'][:5]}")  # First 5 comments
```

## File Structure

```
New Files to Create:
├── scrapers/bilibili_comments_scraper.py
├── tests/test_bilibili_comments.py
├── data/cookies/bilibili_cookies.json  # Your provided cookies go here
└── (Update config.yaml)

Documentation Created:
├── docs/implementation/BILIBILI_COMMENTS_SCRAPER_PLAN.md  # Detailed plan
├── docs/BILIBILI_COMMENTS_PLANNING_SUMMARY.md            # Executive summary
└── docs/BILIBILI_COMMENTS_QUICK_REFERENCE.md            # This file
```

## Comparison: Comments vs Video Scraper

| Feature | bilibili_scraper.py (Existing) | bilibili_comments_scraper.py (New) |
|---------|-------------------------------|-----------------------------------|
| Purpose | Video transcription | Comment extraction |
| Method | Browser automation | API requests |
| Output | Transcript text | Comment metadata |
| Cookie | Browser session | JSON file |
| Speed | Slow (full automation) | Fast (API calls) |
| Dependencies | Playwright, SnapAny | requests only |

## Update Cookie Workflow

### Current State (Planning)
1. Cookie data provided ✅
2. Will be stored in `data/cookies/bilibili_cookies.json`

### Future (Client App)
```
User → Export cookies → Upload via UI → Save to JSON file → Scraper uses new cookies
```

### Manual Update
```
Browser → Cookie Export → Replace bilibili_cookies.json → Restart scraper
```

## Key Implementation Details

### 1. Cookie Loading
```python
def _load_cookies(self) -> dict:
    # Load from: data/cookies/bilibili_cookies.json
    # Format: [{"name": "X", "value": "Y"}, ...]
    # Convert to: "X=Y; A=B" cookie header string
```

### 2. BV to AV Conversion
```python
def _bv_to_av(self, bv_id: str) -> str:
    # BV123456789 → AV1234567890
    # Required because API uses AV IDs internally
```

### 3. Timestamp Conversion
```python
def _trans_date(self, timestamp: int) -> str:
    # 1672531200 → "2023-01-01 12:00:00"
    # Bilibili uses 10-digit Unix timestamps
```

## Error Scenarios

| Error | Detection | Response |
|-------|-----------|----------|
| Expired Cookie | API code != 0 | Log warning, return error |
| Invalid URL | URL validation | Raise ValueError |
| No Comments | Empty replies | Return success with empty array |
| Rate Limit | API error | Add delay, retry |
| Missing Cookie File | File not found | Try config fallback |

## Benefits

1. **Easy Updates**: Update cookie without code changes
2. **Fast**: API-based (no browser automation)
3. **Comprehensive**: Extracts all comment fields
4. **Flexible**: Configurable pagination and sorting
5. **Future-Ready**: Designed for client app integration

## Next Steps

1. Review planning documents ✅
2. Implement scraper ⏳
3. Test with provided cookie ⏳
4. Create usage documentation ⏳

## Documentation Created

1. **BILIBILI_COMMENTS_SCRAPER_PLAN.md**
   - Complete technical plan
   - Method signatures
   - API integration details
   - Error handling

2. **BILIBILI_COMMENTS_PLANNING_SUMMARY.md**
   - Executive summary
   - Key architectural decisions
   - Usage examples

3. **BILIBILI_COMMENTS_QUICK_REFERENCE.md** (this file)
   - Quick overview
   - Table references
   - Common workflows

---

**Status**: Planning complete, ready for implementation! 🎉







