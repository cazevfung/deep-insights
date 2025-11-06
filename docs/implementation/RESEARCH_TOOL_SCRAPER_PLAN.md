# Research Tool - Scraper Implementation Plan (REFINED)

## Overview
This document outlines the architecture for building independent content scrapers for YouTube, Bilibili, and general articles. These scrapers will be standalone, reusable modules that can be called independently.

## Key Requirements
- **Storage Format**: JSON with rich metadata (title, author, publish date, source, etc.)
- **Caching**: Enabled to avoid re-extracting same URLs
- **Parallel Processing**: Yes, with proper Playwright worker pattern (each worker gets own browser context)
- **GUI**: Web-based local server (Flask/FastAPI) - no external hosting
- **Timestamps**: NOT preserved in transcripts
- **Languages**: Bilibili in Chinese, YouTube in original language, UI and research output in Chinese
- **API Integration**: Qwen3-max for research (requires API key management)

---

## Architecture Overview

```
research-tool/
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py              # Abstract base class
│   ├── youtube_scraper.py           # YouTube transcript extractor
│   ├── bilibili_scraper.py          # Bilibili subtitle extractor  
│   └── article_scraper.py           # Generic article text extractor
├── core/
│   ├── __init__.py
│   ├── scraper_manager.py           # Orchestrates all scrapers with parallel support
│   ├── config.py                    # Configuration management
│   └── qwen_research.py             # Qwen3-max API integration
├── storage/
│   ├── __init__.py
│   ├── content_storage.py           # Handles JSON storage with caching
│   └── cache_manager.py             # URL-based caching system
├── web/
│   ├── app.py                       # Flask/FastAPI web server
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css           # Chinese UI styling
│   │   └── js/
│   │       └── main.js            # Frontend JavaScript
│   └── templates/
│       └── index.html              # Main Chinese UI
├── utils/
│   ├── __init__.py
│   ├── api_key_manager.py          # Secure API key management
│   └── metadata_extractor.py       # Extract titles, authors, dates from pages
├── data/
│   ├── cache/                       # URL cache storage
│   └── research/                    # Research session data (JSON)
├── requirements.txt
├── config.yaml                      # User configuration
└── main.py                          # Entry point (starts web server locally)
```

---

## 1. Base Scraper (`base_scraper.py`)

### Purpose
Abstract base class that defines the common interface for all scrapers.

### Structure
```python
class BaseScraper:
    """Abstract base class for all content scrapers"""
    
    def __init__(self, **kwargs):
        # Common initialization: playwright setup, logging, config
        pass
    
    def extract(self, url: str) -> Dict:
        """
        Main extraction method (to be implemented by subclasses)
        
        Returns:
            {
                'success': bool,
                'url': str,
                'content': str or None,
                'metadata': Dict,
                'error': str or None,
                'method': str,
                'timestamp': str
            }
        """
        raise NotImplementedError
    
    def validate_url(self, url: str) -> bool:
        """Check if URL is valid for this scraper"""
        raise NotImplementedError
    
    def clean_content(self, content: str) -> str:
        """Basic content cleaning (shared across scrapers)"""
        pass
    
    def close(self):
        """Cleanup resources"""
        pass
```

### Key Features
- Common Playwright setup
- Standardized return format
- Error handling
- Logging
- Resource cleanup

---

## 2. YouTube Scraper (`youtube_scraper.py`)

### Purpose
Extract transcripts from YouTube videos using Playwright.

### Strategy (from your existing code)
1. Navigate to YouTube video URL
2. Wait for page load (`domcontentloaded`)
3. Try to expand description if collapsed
4. Click "Show transcript" button (multiple selector attempts)
5. Wait for transcript segments to load
6. Extract text from `ytd-transcript-segment-renderer` elements
7. Filter out `[Music]`, `[Applause]`, `[Laughter]` markers
8. Join segments with spaces

### Implementation Details
```python
class YouTubeScraper(BaseScraper):
    """Extract transcripts from YouTube videos"""
    
    def validate_url(self, url: str) -> bool:
        # Check if contains 'youtube.com' or 'youtu.be'
        return any(domain in url for domain in ['youtube.com', 'youtu.be'])
    
    def extract(self, url: str) -> Dict:
        # Implementation similar to PlaywrightTranscriptScraper._extract_transcript
        # But standalone and reusable
        pass
    
    def _extract_transcript_segments(self, page: Page) -> List[str]:
        """Extract and clean transcript segments"""
        pass
    
    def _normalize_timestamp_format(self, content: str) -> str:
        """Optional: Preserve or remove timestamps"""
        pass
```

### Methods
- `extract()`: Main extraction with error handling
- `_extract_transcript_segments()`: Extract raw transcript from page
- `_normalize_timestamp_format()`: Optional timestamp handling
- `clean_content()`: Remove speaker markers and normalize text

### Configuration
- Headless mode (default: False for visibility)
- Timeout settings
- User agent strings
- Optional timestamp preservation

---

## 3. Bilibili Scraper (`bilibili_scraper.py`)

### Purpose
Extract subtitles from Bilibili videos using Playwright.

### Strategy (Two-tier Approach)
**Primary Method (Recommended):**
- Navigate to Bilibili video URL
- Access transcript via AI assistant feature (as per GitHub reference)
- Click subtitle download button if available
- Extract subtitle content

**Fallback Method:**
- Navigate to `https://www.kedou.life/caption/subtitle/bilibili`
- Find the URL input field
- Paste the Bilibili video URL
- Click "提取" (Extract) button
- Wait for subtitle to appear
- Download or extract subtitle text

### Implementation Details
```python
class BilibiliScraper(BaseScraper):
    """Extract subtitles from Bilibili videos"""
    
    def validate_url(self, url: str) -> bool:
        # Check if contains 'bilibili.com'
        return 'bilibili.com' in url
    
    def extract(self, url: str) -> Dict:
        # Try primary method first
        result = self._extract_from_bilibili(url)
        
        if not result['success']:
            # Fall back to Kedou method
            result = self._extract_from_kedou(url)
        
        return result
    
    def _extract_from_bilibili(self, url: str) -> Dict:
        """Try to extract directly from Bilibili page"""
        # Use AI assistant or transcript feature
        # Similar to the GitHub project approach
        pass
    
    def _extract_from_kedou(self, url: str) -> Dict:
        """Fallback: Extract via Kedou subtitle service"""
        # Navigate to kedou.life
        # Fill in URL
        # Click extract button
        # Download subtitle
        pass
```

### Methods
- `extract()`: Main extraction with fallback logic
- `_extract_from_bilibili()`: Direct Bilibili extraction
- `_extract_from_kedou()`: Fallback via Kedou service
- `_parse_subtitle_format()`: Handle SRT or other subtitle formats

### Configuration
- Prefer Bilibili direct vs. Kedou fallback
- Timeout for fallback
- Retry logic

---

## 4. Article Scraper (`article_scraper.py`)

### Purpose
Extract text content from web articles and blog posts.

### Strategy (from your existing code)
1. Use Playwright to load page (handles JS-heavy sites)
2. Scroll page to trigger lazy loading
3. Click "Read More" / "展开全文" expand buttons
4. Remove blocking elements (paywalls, modals, ads)
5. Extract main content using multiple selector attempts:
   - `article` tag
   - `main` tag
   - `[role="article"]`
   - Common class names (`article-content`, `content-wrapper`, etc.)
6. Fallback to trafilatura library if Playwright fails
7. Clean and return text

### Implementation Details
```python
class ArticleScraper(BaseScraper):
    """Extract text content from web articles"""
    
    def validate_url(self, url: str) -> bool:
        # Accept all URLs (generic scraper)
        return url.startswith(('http://', 'https://'))
    
    def extract(self, url: str) -> Dict:
        # Try Playwright first
        result = self._extract_with_playwright(url)
        
        if not result['success']:
            # Fallback to trafilatura
            result = self._extract_with_trafilatura(url)
        
        return result
    
    def _extract_with_playwright(self, url: str) -> Dict:
        # Similar to ArticleContentExtractor._extract_with_playwright
        pass
    
    def _extract_with_trafilatura(self, url: str) -> Dict:
        # Use trafilatura library
        pass
    
    def _click_expand_buttons(self, page: Page):
        """Click 'Read More' style buttons"""
        pass
    
    def _remove_blocking_elements(self, page: Page):
        """Remove paywalls, overlays, modals"""
        pass
```

### Methods
- `extract()`: Main extraction with dual-method approach
- `_extract_with_playwright()`: Playwright-based extraction
- `_extract_with_trafilatura()`: Fallback trafilatura extraction
- `_click_expand_buttons()`: Expand hidden content
- `_remove_blocking_elements()`: Clean page from blocking elements
- `clean_content()`: Remove extra whitespace, normalize text

### Configuration
- Method preference (Playwright vs. trafilatura)
- Minimum content word count
- Timeout settings
- Enable/disable blocking element removal

---

## 5. Scraper Manager (`scraper_manager.py`)

### Purpose
Orchestrates multiple scrapers with parallel processing and handles link type detection.

### Implementation
```python
class ScraperManager:
    """Manages and coordinates all scrapers with parallel processing"""
    
    def __init__(self, num_workers: int = 3, enable_cache: bool = True):
        self.youtube_scraper = YouTubeScraper()
        self.bilibili_scraper = BilibiliScraper()
        self.article_scraper = ArticleScraper()
        self.num_workers = num_workers
        self.cache_manager = CacheManager() if enable_cache else None
    
    def extract_from_url(self, url: str) -> Dict:
        """Detect link type and route to appropriate scraper"""
        # Check cache first
        if self.cache_manager and self.cache_manager.is_cached(url):
            cached = self.cache_manager.get_cached(url)
            if cached:
                logger.info(f"[CACHE HIT] {url}")
                return cached
        
        # Route to appropriate scraper
        if self.youtube_scraper.validate_url(url):
            result = self.youtube_scraper.extract(url)
        elif self.bilibili_scraper.validate_url(url):
            result = self.bilibili_scraper.extract(url)
        else:
            result = self.article_scraper.extract(url)
        
        # Save to cache if successful
        if result.get('success') and self.cache_manager:
            self.cache_manager.save_to_cache(url, result)
        
        return result
    
    def extract_batch(self, urls: List[str]) -> List[Dict]:
        """
        Extract from multiple URLs with parallel processing
        
        Each worker gets its own Playwright browser context to prevent crashes
        """
        if len(urls) == 1:
            return [self.extract_from_url(urls[0])]
        
        # Use ThreadPoolExecutor with proper browser isolation
        results = []
        results_lock = threading.Lock()
        
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = []
            for url in urls:
                future = executor.submit(self._extract_with_lock, url, results, results_lock)
                futures.append(future)
            
            # Wait for all to complete
            for future in futures:
                future.result()
        
        return results
    
    def _extract_with_lock(self, url: str, results: List, lock: threading.Lock):
        """Thread-safe extraction"""
        result = self.extract_from_url(url)
        with lock:
            results.append(result)
    
    def close(self):
        """Cleanup all scrapers"""
        self.youtube_scraper.close()
        self.bilibili_scraper.close()
        self.article_scraper.close()
```

### Features
- Automatic link type detection
- Parallel batch processing with browser isolation
- Caching support
- Progress tracking
- Error handling and reporting

---

## 6. Content Storage (`content_storage.py`)

### Purpose
Handle saving and loading extracted content for research purposes.

### Structure
```python
class ContentStorage:
    """Manages storage of extracted content in JSON format"""
    
    def save_content(self, 
                     url: str, 
                     content: str, 
                     metadata: Dict) -> str:
        """
        Save content as JSON with rich metadata
        
        Returns:
            JSON structure:
            {
                'url': str,
                'content': str,              # Full text content
                'title': str,                # Page/video title
                'author': str,               # Author/creator (if available)
                'publish_date': str,         # Publishing date (ISO format)
                'source': str,               # Source site name
                'language': str,             # Content language
                'word_count': int,           # Word/character count
                'extraction_method': str,    # 'youtube', 'bilibili', 'article'
                'extraction_timestamp': str,  # When extracted
                'error': str or None,         # Error message if failed
                'success': bool              # Extraction success status
            }
        """
        # Save to: data/research/{session_id}/{url_hash}.json
        pass
    
    def load_content(self, url: str) -> Optional[Dict]:
        """Load saved content from JSON"""
        pass
    
    def get_all_content(self, session_id: str) -> List[Dict]:
        """Get all saved content for a research session"""
        pass
```

### CacheManager Structure
```python
class CacheManager:
    """Manages URL caching to avoid re-extraction"""
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_key(self, url: str) -> str:
        """Generate cache key from URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def is_cached(self, url: str) -> bool:
        """Check if URL is already cached"""
        pass
    
    def get_cached(self, url: str) -> Optional[Dict]:
        """Retrieve cached content"""
        pass
    
    def save_to_cache(self, url: str, data: Dict):
        """Save content to cache"""
        pass
    
    def clear_cache(self):
        """Clear all cached content"""
        pass
```

---

## Dependencies

### Required Packages
```python
playwright>=1.40.0        # Browser automation
trafilatura>=1.6.0       # Article extraction fallback
loguru>=0.7.0            # Logging
pydantic>=2.0.0          # Data validation (optional but recommended)
```

### Playwright Installation
```bash
pip install playwright
playwright install chromium
```

---

## Configuration

### Config File (`config.yaml`)
```yaml
scrapers:
  youtube:
    headless: false
    timeout: 15000
    min_transcript_length: 10
    preserve_timestamps: false
    num_workers: 3
  
  bilibili:
    headless: false
    timeout: 20000
    use_kedou_fallback: true
    kedou_fallback_timeout: 30000
    prefer_direct: true
    language: 'zh-CN'  # Chinese
    num_workers: 3
  
  article:
    headless: true
    timeout: 30000
    method_preference: 'playwright'  # or 'trafilatura'
    min_content_words: 50
    remove_blocking_elements: true
    num_workers: 3

storage:
  base_dir: 'data/research'
  format: 'json'  # JSON with metadata
  save_metadata: true
  cache_enabled: true
  cache_dir: 'data/cache'

web:
  host: '127.0.0.1'  # Local only
  port: 5000
  debug: false
  title: '智能研究工具'

qwen:
  api_key: ''  # User will configure
  api_url: 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation'
  model: 'qwen-turbo'
  temperature: 0.7
  max_tokens: 2000
  language: 'zh-CN'  # Output in Chinese
```

### Config Module (`config.py`)
```python
import yaml
from pathlib import Path

class Config:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
    
    def get(self, key_path: str, default=None):
        """Get config value using dot notation"""
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            value = value.get(key, default)
            if value is None:
                return default
        return value
```

---

## Usage Example

```python
# Individual scraper usage
from scrapers.youtube_scraper import YouTubeScraper

scraper = YouTubeScraper()
result = scraper.extract('https://www.youtube.com/watch?v=VIDEO_ID')
print(result['content'])

# Scraper manager usage
from core.scraper_manager import ScraperManager

manager = ScraperManager()

urls = [
    'https://www.youtube.com/watch?v=VIDEO_ID',
    'https://www.bilibili.com/video/BVxxxxx',
    'https://example.com/article'
]

results = manager.extract_batch(urls)

for result in results:
    if result['success']:
        print(f"Extracted {len(result['content'])} chars from {result['url']}")
    else:
        print(f"Failed: {result['error']}")

manager.close()
```

---

## Error Handling Strategy

### Return Format (Standardized)
```python
{
    'success': bool,
    'url': str,
    'content': str or None,
    'metadata': {
        'method': str,           # 'youtube', 'bilibili', 'article'
        'word_count': int,
        'extraction_time': float,
        'language': str,         # Optional
        'transcript_available': bool,  # For videos
    },
    'error': str or None,
    'timestamp': str
}
```

### Error Scenarios
1. **Transcript not available**: Return `success=False` with error message
2. **Page load timeout**: Retry with longer timeout or skip
3. **Element not found**: Log and continue to fallback method
4. **Network error**: Retry mechanism (configurable)
5. **Content too short**: Return with warning but allow processing

---

## Testing Strategy

### Unit Tests
- Test URL validation for each scraper
- Test content extraction from sample pages
- Test error handling

### Integration Tests
- Test scraper manager routing
- Test batch processing
- Test storage operations

### Sample Test Cases
```python
def test_youtube_scraper():
    scraper = YouTubeScraper()
    result = scraper.extract('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
    assert result['success'] == True
    assert len(result['content']) > 100
    assert 'transcript' in result['metadata']
```

---

## Next Steps After Implementation

1. ✅ Build YouTube scraper
2. ✅ Build Bilibili scraper  
3. ✅ Build Article scraper
4. Build Scraper Manager
5. Build Content Storage
6. Build Qwen integration for research
7. Build CLI/GUI client
8. Package as .exe

---

## Web-Based GUI Architecture

### Purpose
Provide a Chinese-language web interface running locally for research tasks.

### Technology Stack
- **Backend**: Flask (lightweight, easy to package) or FastAPI (modern async)
- **Frontend**: HTML + CSS + Vanilla JavaScript
- **Language**: Chinese UI throughout
- **Server**: Local only (127.0.0.1), no external hosting

### Implementation
```python
# web/app.py
from flask import Flask, render_template, request, jsonify
from core.scraper_manager import ScraperManager
from core.qwen_research import QwenResearch
from storage.content_storage import ContentStorage

app = Flask(__name__)
scraper_manager = ScraperManager(num_workers=3)
content_storage = ContentStorage()
qwen_research = QwenResearch(api_key=config.get('qwen.api_key'))

@app.route('/')
def index():
    """Main page - Chinese UI"""
    return render_template('index.html')

@app.route('/api/extract', methods=['POST'])
def extract_content():
    """Extract content from URLs"""
    urls = request.json.get('urls', [])
    results = scraper_manager.extract_batch(urls)
    return jsonify({'results': results})

@app.route('/api/research', methods=['POST'])
def conduct_research():
    """Conduct research using Qwen"""
    topic = request.json.get('topic')
    content_urls = request.json.get('content', [])
    
    research_result = qwen_research.analyze(topic, content_urls)
    return jsonify({'result': research_result})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
```

### UI Design (Chinese)
```html
<!-- templates/index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>智能研究工具</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <div class="container">
        <h1>智能研究工具</h1>
        
        <div class="section">
            <h2>📌 研究主题</h2>
            <input type="text" id="topic" placeholder="输入研究主题...">
        </div>
        
        <div class="section">
            <h2>🔗 添加链接</h2>
            <textarea id="urls" placeholder="每行一个链接 (支持YouTube, Bilibili, 文章)"></textarea>
            <button onclick="extractContent()">提取内容</button>
        </div>
        
        <div class="section">
            <h2>📊 提取结果</h2>
            <div id="extraction-results"></div>
        </div>
        
        <div class="section">
            <button onclick="startResearch()">🚀 开始研究</button>
            <div id="research-result"></div>
        </div>
    </div>
    
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
</body>
</html>
```

### Key Features
- Chinese UI throughout
- Real-time extraction progress
- Visual feedback for extraction status
- Research output display
- Export research results

---

## 7. Qwen Research Integration (`core/qwen_research.py`)

### Purpose
Integrate with Qwen3-max API to conduct deep research on extracted content.

### Implementation
```python
class QwenResearch:
    """Qwen3-max API integration for research"""
    
    def __init__(self, api_key: str, config: dict):
        self.api_key = api_key
        self.api_url = config.get('qwen.api_url')
        self.model = config.get('qwen.model')
        self.temperature = config.get('qwen.temperature')
        self.max_tokens = config.get('qwen.max_tokens')
        self.language = config.get('qwen.language', 'zh-CN')
    
    def analyze(self, topic: str, content_data: List[Dict]) -> Dict:
        """
        Conduct deep research on a topic using extracted content
        
        Args:
            topic: Research topic/question
            content_data: List of extracted content dicts
        
        Returns:
            {
                'topic': str,
                'research_result': str,  # Chinese research output
                'sources_used': List[str],  # URLs referenced
                'timestamp': str,
                'word_count': int
            }
        """
        # Prepare content summary for API
        content_summary = self._prepare_content(content_data)
        
        # Construct research prompt in Chinese
        prompt = self._create_research_prompt(topic, content_summary)
        
        # Call Qwen API
        response = self._call_qwen_api(prompt)
        
        # Parse and return results
        return {
            'topic': topic,
            'research_result': response,
            'sources_used': [item['url'] for item in content_data if item.get('success')],
            'timestamp': datetime.now().isoformat(),
            'word_count': len(response.split())
        }
    
    def _create_research_prompt(self, topic: str, content: str) -> str:
        """Create research prompt in Chinese"""
        prompt = f"""
        You are a research assistant. Based on the following content sources, provide a comprehensive analysis on the topic: {topic}
        
        Requirements:
        1. Provide detailed analysis in Chinese
        2. Summarize key findings from all sources
        3. Identify main arguments and evidence
        4. Note any conflicting viewpoints
        5. Provide insights and conclusions
        
        Content sources:
        {content}
        
        Please provide your research analysis:
        """
        return prompt
    
    def _call_qwen_api(self, prompt: str) -> str:
        """Call Qwen API and return response"""
        import requests
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'input': {'messages': [{'role': 'user', 'content': prompt}]},
            'parameters': {
                'temperature': self.temperature,
                'max_tokens': self.max_tokens,
                'result_format': 'message'
            }
        }
        
        response = requests.post(self.api_url, headers=headers, json=payload)
        # Parse response and return text
        pass
```

### Metadata Extractor (`utils/metadata_extractor.py`)
```python
class MetadataExtractor:
    """Extract titles, authors, dates from web pages"""
    
    def extract_metadata(self, page: Page, url: str, scraper_type: str) -> Dict:
        """
        Extract rich metadata from page
        
        Returns:
            {
                'title': str,
                'author': str,
                'publish_date': str,
                'source': str,
                'description': str
            }
        """
        metadata = {
            'title': self._extract_title(page),
            'author': self._extract_author(page, url, scraper_type),
            'publish_date': self._extract_publish_date(page),
            'source': self._extract_source(url),
            'description': self._extract_description(page)
        }
        return metadata
    
    def _extract_title(self, page: Page) -> str:
        """Extract page title"""
        selectors = [
            'h1',
            'meta[property="og:title"]',
            'meta[name="twitter:title"]',
            'title'
        ]
        for selector in selectors:
            try:
                element = page.locator(selector).first
                if element.count() > 0:
                    text = element.inner_text() if selector == 'h1' else element.get_attribute('content')
                    if text:
                        return text
            except:
                continue
        return 'Untitled'
    
    def _extract_author(self, page: Page, url: str, scraper_type: str) -> str:
        """Extract author based on site type"""
        if 'youtube.com' in url or 'youtu.be' in url:
            # Extract channel name
            try:
                channel = page.locator('ytd-channel-name a').first
                return channel.inner_text() if channel.count() > 0 else 'Unknown'
            except:
                return 'Unknown'
        elif 'bilibili.com' in url:
            # Extract uploader name
            try:
                uploader = page.locator('.username').first
                return uploader.inner_text() if uploader.count() > 0 else 'Unknown'
            except:
                return 'Unknown'
        else:
            # Try meta tags for articles
            meta_selectors = [
                'meta[name="author"]',
                'meta[property="article:author"]',
                '[rel="author"]'
            ]
            for selector in meta_selectors:
                try:
                    element = page.locator(selector).first
                    if element.count() > 0:
                        return element.get_attribute('content') or element.get_attribute('text')
                except:
                    continue
            return 'Unknown'
    
    def _extract_publish_date(self, page: Page) -> str:
        """Extract publishing date"""
        # Try various date selectors and meta tags
        # Return ISO format or empty string
        pass
    
    def _extract_source(self, url: str) -> str:
        """Extract source site name from URL"""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        return domain.replace('www.', '')
```

---

## Important Implementation Notes

### Parallel Processing Pattern
Based on your existing implementation, we use the **worker pattern** where:
- Each worker thread gets its own Playwright browser context
- This prevents crashes from sharing browser instances
- Each worker maintains its own `sync_playwright()` context
- Thread-safe result collection using locks

```python
# In each scraper's parallel method:
with ThreadPoolExecutor(max_workers=num_workers) as executor:
    for worker_id in range(num_workers):
        executor.submit(self._worker, worker_id, ...)

def _worker(self, worker_id, ...):
    # Each worker creates its own browser
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=self.headless)
        context = browser.new_context(...)
        page = context.new_page()
        # Process URLs from queue
        # ...
```

### Language Handling
- **YouTube transcripts**: Keep in original language
- **Bilibili subtitles**: Always in Chinese
- **Article content**: Keep in original language
- **UI**: All Chinese
- **Research output**: Generated in Chinese

### No Timestamps
- Transcript segments are joined with spaces only
- Filter out `[Music]`, `[Applause]`, `[Laughter]` markers
- Clean text, no timing information

---

## Implementation Order

### Phase 1: Core Scrapers (Current Focus)
1. ✅ Create project structure
2. ✅ Implement BaseScraper with Playwright initialization
3. ⏳ Implement YouTubeScraper (standalone, no timestamps)
4. ⏳ Implement BilibiliScraper (with Kedou fallback, Chinese output)
5. ⏳ Implement ArticleScraper (dual-method: Playwright + trafilatura)

### Phase 2: Integration & Storage
6. ⏳ Implement CacheManager (URL-based caching)
7. ⏳ Implement MetadataExtractor (titles, authors, dates)
8. ⏳ Implement ContentStorage (JSON format with rich metadata)
9. ⏳ Implement ScraperManager with parallel processing
10. ⏳ Add comprehensive logging and error handling

### Phase 3: Research Integration
11. ⏳ Implement QwenResearch class (Qwen3-max API)
12. ⏳ Implement API key management (secure storage)
13. ⏳ Create research orchestration logic
14. ⏳ Test research flow end-to-end

### Phase 4: Web Client
15. ⏳ Set up Flask server
16. ⏳ Create Chinese UI (HTML/CSS/JS)
17. ⏳ Implement API endpoints for extraction and research
18. ⏳ Add real-time progress updates
19. ⏳ Test web interface

### Phase 5: Packaging
20. ⏳ Package as standalone .exe using PyInstaller
21. ⏳ Include Playwright browser binaries
22. ⏳ Create installation package
23. ⏳ Test packaged application

---

## Notes

- All scrapers should be **independent** and **reusable**
- Playwright will be the primary extraction method for all scrapers
- Each worker gets its own browser context to prevent crashes
- Error handling should be graceful with informative messages
- Logging should be comprehensive for debugging (Chinese where appropriate)
- Configuration should be flexible and user-adjustable
- Caching uses MD5 hash of URLs for fast lookup
- All data stored in JSON format with rich metadata
- Web server runs locally only (127.0.0.1)
- API key stored securely (encrypted or environment variable)

## Dependencies List (Updated)

```txt
playwright>=1.40.0           # Browser automation
trafilatura>=1.6.0            # Article extraction fallback
flask>=3.0.0                 # Web server
requests>=2.31.0             # API calls
pyyaml>=6.0                  # Config file parsing
loguru>=0.7.0                # Logging
pydantic>=2.0.0              # Data validation (optional)
hashlib                      # Built-in caching
threading                    # Built-in parallel processing
```
