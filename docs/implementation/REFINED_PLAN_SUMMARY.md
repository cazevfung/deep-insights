# Research Tool - Refined Plan Summary

## Key Decisions

### 1. Storage Format
- **JSON Format**: All content stored as JSON with rich metadata
- **Metadata Includes**: Title, author, publish date, source, language, word count, extraction method, etc.
- **结构**: 
  ```json
  {
    "url": "...",
    "content": "...",
    "title": "...",
    "author": "...",
    "publish_date": "...",
    "source": "...",
    "language": "...",
    "word_count": 1234,
    "extraction_method": "youtube/bilibili/article",
    "success": true
  }
  ```

### 2. Caching System
- **Enabled**: Avoid re-extracting same URLs
- **Implementation**: `CacheManager` uses MD5 hash for fast lookup
- **Storage Location**: `data/cache/`
- **Format**: JSON files matching main storage format

### 3. Parallel Processing
- **Enabled**: Support multiple URL extraction simultaneously
- **Method**: Each worker uses independent Playwright browser contexts
- **Pattern**: Reference existing `_worker()` method implementation
- **Benefits**: Prevents browser crashes, thread-safe

### 4. GUI Choice
- **Technology**: Web-based (Flask local server)
- **Language**: Completely Chinese UI
- **Server**: Local only (127.0.0.1:5000)
- **Reason**: Lightweight, easy to package as .exe

### 5. Timestamps
- **Not Preserved**: Transcript text does not include timestamps
- **Processing**: Filter out [Music], [Applause] markers
- **Output**: Plain text content only

### 6. Language Handling
- **Bilibili**: Chinese subtitles
- **YouTube**: Original language
- **Articles**: Original language
- **UI**: All Chinese text
- **Research Output**: Generated in Chinese

---

## Architecture Overview

```
research-tool/
├── scrapers/              # Independent scrapers
│   ├── base_scraper.py
│   ├── youtube_scraper.py
│   ├── bilibili_scraper.py
│   └── article_scraper.py
├── core/                 # Core functionality
│   ├── scraper_manager.py  # Parallel processing + cache
│   ├── config.py
│   └── qwen_research.py    # Qwen3 API integration
├── storage/              # Storage management
│   ├── content_storage.py  # JSON storage
│   └── cache_manager.py    # URL caching
├── utils/                # Utility functions
│   ├── metadata_extractor.py  # Metadata extraction
│   └── api_key_manager.py     # API key management
├── web/                  # Web interface
│   ├── app.py            # Flask server
│   ├── static/css/
│   ├── static/js/
│   └── templates/
├── data/                 # Data storage
│   ├── cache/           # Cache files
│   └── research/        # Research session data
├── config.yaml          # Configuration file
└── main.py             # Entry point
```

---

---

## Implementation Phases

### Phase 1: Core Scrapers
**Goal**: Build independent scrapers with caching and parallel processing support

1. **BaseScraper**: Base class with Playwright initialization
2. **YouTubeScraper**: Transcript extraction without timestamps
3. **BilibiliScraper**: Chinese subtitles with Kedou fallback
4. **ArticleScraper**: Dual-method (Playwright + trafilatura)

**Key Requirements**:
- Each scraper independently usable
- Supports parallel processing (independent browser contexts)
- Returns unified JSON format
- Metadata extraction (title, author, date)

### Phase 2: Integration & Storage
**Goal**: Implement manager, storage, and caching

5. **CacheManager**: URL hash caching
6. **MetadataExtractor**: Extract titles, authors, dates
7. **ContentStorage**: JSON format storage
8. **ScraperManager**: Parallel batch processing
9. **Logging System**: Complete error handling

**Key Requirements**:
- Cache to avoid repeated extraction
- Rich metadata
- Parallel processing without crashes
- Complete logging

### Phase 3: Research Integration
**Goal**: Qwen3 API integration

10. **QwenResearch**: API calls
11. **API Key Management**: Secure storage
12. **Research Orchestration**: Processing flow
13. **End-to-End Testing**: Complete workflow testing

**Key Requirements**:
- Chinese prompts and output
- Secure API key storage
- Error handling
- Source reference tracking

### Phase 4: Web Client
**Goal**: Flask web interface

14. **Flask Server**: Launch locally
15. **Chinese UI**: HTML/CSS/JS
16. **API Endpoints**: Extraction and research
17. **Real-time Progress**: Update display
18. **UI Testing**: Feature verification

**Key Requirements**:
- Completely Chinese interface
- Real-time progress updates
- Visual feedback
- Export research results

### Phase 5: Packaging
**Goal**: Package as .exe

19. **PyInstaller**: Package as executable
20. **Browser Binaries**: Include Playwright
21. **Installation Package**: User-friendly
22. **Testing**: Post-packaging testing

**Key Requirements**:
- Single-file .exe or installer
- Include all dependencies
- Works out-of-the-box
- Windows compatible

---

## Technology Stack

### Backend
- **Python 3.9+**: Primary language
- **Playwright**: Browser automation
- **Flask**: Web server
- **trafilatura**: Article extraction fallback
- **requests**: API calls
- **PyYAML**: Config parsing
- **loguru**: Logging

### Frontend
- **HTML**: Structure
- **CSS**: Styling (Chinese UI)
- **JavaScript**: Interactions
- **Language**: All Chinese text

### Storage
- **JSON**: All data formats
- **File System**: Local storage
- **MD5 Hash**: Cache key

---

## Config File Example

```yaml
scrapers:
  youtube:
    headless: false
    timeout: 15000
    num_workers: 3
  
  bilibili:
    headless: false
    use_kedou_fallback: true
    language: 'zh-CN'
    num_workers: 3
  
  article:
    headless: true
    method_preference: 'playwright'
    min_content_words: 50
    num_workers: 3

storage:
  format: 'json'
  cache_enabled: true
  cache_dir: 'data/cache'

web:
  host: '127.0.0.1'
  port: 5000
  title: '智能研究工具'

qwen:
  api_key: ''  # User configuration
  model: 'qwen-turbo'
  language: 'zh-CN'
```

---

## Key Features

✅ **Three Link Types Supported**
- YouTube (transcript extraction)
- Bilibili (subtitle extraction + Kedou fallback)
- Articles (Playwright + trafilatura)

✅ **Parallel Processing**
- Multiple URLs extracted simultaneously
- Independent browser contexts
- Crash prevention

✅ **Smart Caching**
- URL hash fast lookup
- Avoid repeated extraction
- JSON format storage

✅ **Rich Metadata**
- Title, author, date
- Source, language, word count
- Extraction method and timestamp

✅ **Qwen3 Integration**
- API calls
- Chinese research output
- Source reference tracking

✅ **Web Interface**
- Fully Chinese UI
- Real-time progress
- Visual feedback

✅ **Easy Packaging**
- .exe format
- Single-file distribution
- Works out-of-the-box

---

## Next Steps

Please confirm if this plan meets your requirements. Once confirmed, we'll start Phase 1 implementation:
1. Create project structure
2. Implement BaseScraper
3. Implement YouTube Scraper

Ready to start? 🚀
