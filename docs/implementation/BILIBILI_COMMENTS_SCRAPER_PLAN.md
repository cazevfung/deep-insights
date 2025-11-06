# Bilibili Comments Scraper - Implementation Plan

## Overview

This document outlines the implementation plan for a new Bilibili comments scraper that will allow scraping comments from Bilibili videos. The scraper is designed with cookie management flexibility in mind, allowing for easy cookie updates when building a client app later.

## Objectives

1. Create a standalone scraper for Bilibili video comments
2. Support multiple videos and paginated comments
3. Extract comprehensive comment data (author, time, IP location, likes, content)
4. Allow cookie updates without code changes (via config)
5. Maintain consistency with existing scrapers in the project

## Architecture

### File Structure

```
scrapers/
  └── bilibili_comments_scraper.py    # New scraper
tests/
  └── test_bilibili_comments.py        # New test file
config.yaml                            # Updated with cookie config
data/
  └── cookies/
      └── bilibili_cookies.json        # Cookie storage (for easy updates)
```

### Configuration Design

**Location: `config.yaml`**
```yaml
scrapers:
  bilibili_comments:
    headless: false
    timeout: 30000
    max_comments_per_page: 20
    max_pages: 30  # Maximum pages to scrape per video
    cookie_source: 'file'  # 'file' or 'config'
    cookie_file: 'data/cookies/bilibili_cookies.json'
    # Fallback cookies in config (if cookie_source is 'config')
    cookies: []  # Populated from file or manual entry
    sort_mode: 3  # 3 = hot comments, 2 = new comments
    num_workers: 3
```

**Cookie Storage: `data/cookies/bilibili_cookies.json`**
```json
[
  {
    "domain": ".bilibili.com",
    "name": "SESSDATA",
    "value": "...",
    "path": "/",
    "secure": true,
    "httpOnly": true,
    "session": false,
    "expirationDate": 1788845105
  },
  ...
]
```

### Why This Design?

1. **Flexible Cookie Management**: Cookies can be stored in a separate JSON file, making it easy to update without touching code or config.yaml
2. **Future Client App Integration**: When building the client app, users can update `bilibili_cookies.json` directly
3. **Fallback Support**: If file doesn't exist, cookies can be specified directly in config.yaml
4. **Cookie Format**: Uses standard JSON format compatible with browser extensions

## BilibiliCommentsScraper Class

### Class Structure

```python
class BilibiliCommentsScraper(BaseScraper):
    """Extract comments from Bilibili videos."""
    
    def __init__(self, **kwargs):
        """Initialize Bilibili comments scraper."""
        super().__init__(**kwargs)
        self.cookie_source = self.scraper_config.get('cookie_source', 'file')
        self.cookie_file = self.scraper_config.get('cookie_file')
        self.max_pages = self.scraper_config.get('max_pages', 30)
        self.sort_mode = self.scraper_config.get('sort_mode', 3)  # 3=hot, 2=new
        self.cookies = self._load_cookies()
        self.headers = self._build_headers()
```

### Key Methods

#### 1. Cookie Management
```python
def _load_cookies(self) -> dict:
    """Load cookies from file or config."""
    if self.cookie_source == 'file':
        return self._load_cookies_from_file()
    else:
        return self._load_cookies_from_config()

def _load_cookies_from_file(self) -> dict:
    """Load cookies from JSON file."""
    # Read from data/cookies/bilibili_cookies.json
    # Parse and convert to cookie header string
    
def _parse_cookies_to_string(self, cookies: list) -> str:
    """Convert cookie JSON array to cookie header string."""
    # Convert: [{"name": "X", "value": "Y"}] -> "X=Y; A=B"
```

#### 2. URL Validation
```python
def validate_url(self, url: str) -> bool:
    """Check if URL is a valid Bilibili video URL."""
    # Accept formats:
    # - https://www.bilibili.com/video/BVxxxxxxx
    # - https://bilibili.com/video/avxxxxxxx
    # - BVxxxxxxx (just the BV ID)
```

#### 3. Main Extraction
```python
def extract(self, url: str) -> Dict:
    """
    Extract comments from Bilibili video.
    
    Returns:
        Dictionary with extraction results containing:
        - comments: List of comment objects
        - total_comments: Total number of comments scraped
        - video_info: Video metadata
        - extraction_timestamp: When extraction was performed
    """
```

#### 4. Helper Methods
```python
def _extract_video_id(self, url: str) -> tuple:
    """Extract BV and AV IDs from URL."""
    # Returns: (bv_id, av_id)

def _bv_to_av(self, bv_id: str) -> str:
    """Convert BV ID to AV ID (required by API)."""
    # Bilibili API uses AV IDs internally

def _fetch_comments_page(self, av_id: str, page: int) -> dict:
    """Fetch one page of comments from Bilibili API."""
    # API endpoint: 
    # https://api.bilibili.com/x/v2/reply?oid={av_id}&type=1&pn={page}&ps=20&mode={mode}
    
def _parse_comment_data(self, api_response: dict) -> list:
    """Parse API response to extract comment data."""
    
def _trans_date(self, timestamp: int) -> str:
    """Convert 10-digit timestamp to readable date."""
    # Format: "YYYY-MM-DD HH:MM:SS"
```

## API Integration

### Bilibili Comments API

**Endpoint:** `https://api.bilibili.com/x/v2/reply`

**Parameters:**
- `oid`: Video AV ID (required)
- `type`: Always 1 for video comments
- `pn`: Page number (starts from 1)
- `ps`: Page size (20 comments per page)
- `mode`: 3 = hot comments, 2 = new comments
- `jsonp`: Response format (use 'jsonp')

**Headers Required:**
- `cookie`: Bilibili session cookies (CRITICAL)
- `referer`: Video page URL
- `user-agent`: Standard browser UA
- `accept`: application/json

**Response Structure:**
```json
{
  "code": 0,
  "message": "0",
  "data": {
    "replies": [
      {
        "rpid": 12345,
        "mid": 67890,
        "member": {
          "uname": "username",
          "mid": 67890
        },
        "content": {
          "message": "comment text",
          "location": "上海"  # IP location (if available)
        },
        "like": 42,
        "ctime": 1672531200  # 10-digit timestamp
      }
    ],
    "page": {
      "count": 1000,
      "num": 1,
      "size": 20
    }
  }
}
```

## Data Extraction

### Comment Fields to Extract

1. **video_id**: BV ID (e.g., BV1DP411g7jx)
2. **video_url**: Full video URL
3. **page_number**: Page number (1-based)
4. **comment_id**: Comment ID (rpid)
5. **author**: Comment author username
6. **author_id**: Author's Bilibili UID (mid)
7. **comment_time**: Timestamp (10-digit)
8. **comment_time_readable**: Human-readable time
9. **ip_location**: IP location (if available)
10. **likes**: Number of likes
11. **content**: Comment text

### Pagination

- Default: Scrape up to 30 pages per video
- Each page contains 20 comments
- Maximum: ~600 comments per video (30 pages × 20 comments)
- Can be configured via `max_pages` in config

### Comment Sorting

- **mode=3**: Hot/popular comments (default)
- **mode=2**: New/recent comments
- Configurable via `sort_mode` in config

## Output Format

### Return Structure

```python
{
    'success': True/False,
    'url': str,  # Original video URL
    'content': str,  # All comments as text
    'comments': list,  # List of comment dicts
    'total_comments': int,
    'video_info': {
        'bv_id': str,
        'av_id': str,
        'title': str,  # Could be fetched via video API
    },
    'source': 'Bilibili Comments',
    'language': 'zh-CN',
    'word_count': int,  # Total words in all comments
    'extraction_method': 'bilibili_comments_api',
    'extraction_timestamp': str,  # ISO format
    'error': None or str
}
```

### Individual Comment Structure

```python
{
    'comment_id': int,
    'author': str,
    'author_id': int,
    'content': str,
    'comment_time': int,  # 10-digit timestamp
    'comment_time_readable': str,  # "YYYY-MM-DD HH:MM:SS"
    'ip_location': str or None,
    'likes': int,
    'page_number': int,
    'video_url': str,
    'video_id': str
}
```

## Implementation Steps

### Phase 1: Core Functionality
1. Create `BilibiliCommentsScraper` class
2. Implement cookie loading from JSON file
3. Implement BV to AV conversion
4. Implement API request method
5. Implement comment parsing

### Phase 2: Data Processing
1. Implement timestamp conversion
2. Implement pagination logic
3. Implement comment extraction loop
4. Implement result aggregation

### Phase 3: Integration
1. Add config section to `config.yaml`
2. Create cookie directory structure
3. Update `__init__.py` to export new scraper
4. Add error handling and logging

### Phase 4: Testing
1. Create `test_bilibili_comments.py`
2. Test with provided cookie
3. Test with multiple videos
4. Test pagination
5. Test error cases (invalid URL, expired cookie)

## Error Handling

### Common Scenarios

1. **Cookie Expired**
   - Detect: API returns code != 0 or empty replies
   - Action: Log warning, return error message
   - Solution: User updates cookie file

2. **Invalid Video URL**
   - Detect: URL validation fails
   - Action: Raise ValueError before extraction

3. **No Comments**
   - Detect: API returns empty replies array
   - Action: Return success with empty comments

4. **Rate Limiting**
   - Detect: API returns error code
   - Action: Add delays, retry with backoff

5. **Cookie File Missing**
   - Detect: File not found
   - Action: Try config.yaml cookies as fallback, or return error

## Comparison with Existing BilibiliScraper

| Feature | BilibiliScraper | BilibiliCommentsScraper |
|---------|----------------|-------------------------|
| Purpose | Video transcription | Comment extraction |
| Method | Browser automation | API requests |
| Cookie | Browser session | Explicit cookie file |
| Output | Transcript text | Comment metadata |
| Use Case | Video content analysis | Comment sentiment/analysis |
| Dependencies | Playwright, SnapAny | requests only |

## Cookie Update Instructions

### For Users
1. Export cookies from browser (using extension like "Cookie-Editor")
2. Save to `data/cookies/bilibili_cookies.json`
3. Restart the scraper

### For Client App (Future)
1. Provide UI to upload/update cookie file
2. Validate cookie format
3. Save to `data/cookies/bilibili_cookies.json`
4. Refresh scraper configuration

## Testing Plan

### Test Cases

1. **Valid URL with Valid Cookie**
   - Test: Scrape comments from a video
   - Expected: Returns comments array with data

2. **Multiple Videos**
   - Test: Scrape comments from multiple BVs
   - Expected: Returns aggregated results

3. **Pagination**
   - Test: Video with 500+ comments
   - Expected: Scrapes up to max_pages

4. **Invalid Cookie**
   - Test: Use expired/ invalid cookie
   - Expected: Returns error with helpful message

5. **Invalid URL**
   - Test: Non-Bilibili URL
   - Expected: Raises validation error

6. **Empty Comments**
   - Test: New video with no comments
   - Expected: Returns success with empty comments array

## Future Enhancements

1. **Reply Threading**: Extract replies to comments
2. **Date Range Filter**: Scrape comments within date range
3. **Keyword Filter**: Filter comments by keywords
4. **Export Formats**: Support CSV, Excel export
5. **Real-time Monitoring**: Monitor comments for new videos
6. **Sentiment Analysis**: Analyze comment sentiment
7. **User Analytics**: Track top commenters

## Notes

- **Cookie Importance**: Cookies are critical for accessing IP location data
- **API Rate Limiting**: Implement delays between requests (0.5-1s recommended)
- **BV vs AV**: BV is newer public ID, AV is internal ID used by API
- **IP Location**: Only available for comments after July 2022
- **Cookie Expiry**: SESSDATA cookie typically expires, needs periodic updates

## Dependencies

```python
# New dependencies
requests  # Already in requirements.txt
pandas    # For CSV export (optional)

# No additional dependencies needed!
```

## File Structure Summary

```
Research Tool/
├── scrapers/
│   ├── base_scraper.py
│   ├── bilibili_scraper.py        # Existing (video transcription)
│   └── bilibili_comments_scraper.py  # NEW
├── tests/
│   └── test_bilibili_comments.py  # NEW
├── config.yaml                    # UPDATED
├── data/
│   └── cookies/
│       └── bilibili_cookies.json  # NEW
└── docs/
    └── implementation/
        └── BILIBILI_COMMENTS_SCRAPER_PLAN.md  # THIS FILE
```

## Next Steps

1. Review this plan
2. Implement core scraper class
3. Implement cookie loading and management
4. Create test file
5. Test with provided cookies
6. Document usage instructions

