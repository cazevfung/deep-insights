# Working Code Patterns Reference

Quick reference for the proven, working code patterns in the `tests/` folder that should be used in the simplified backend.

## Key Working Functions

### 1. Complete Workflow (`test_full_workflow_integration.py`)

**Function**: `run_all_scrapers()`
```python
from tests.test_full_workflow_integration import run_all_scrapers

result = run_all_scrapers()
# Returns: Dict with batch_id, passed, total, success
```

**Function**: `verify_scraper_results(batch_id: str) -> bool`
```python
from tests.test_full_workflow_integration import verify_scraper_results

verified = verify_scraper_results(batch_id)
# Also creates manifest.json in results directory
```

**Function**: `run_research_agent(batch_id: str) -> Optional[Dict]`
```python
from tests.test_full_workflow_integration import run_research_agent

result = run_research_agent(batch_id)
# Returns: Result dict with status, session_id, report_path, etc.
# Uses: DeepResearchAgent, ConsoleInterface/MockConsoleInterface
```

**Dependencies**:
- `research.agent.DeepResearchAgent`
- `research.ui.console_interface.ConsoleInterface`
- `research.ui.mock_interface.MockConsoleInterface`
- `core.config.Config`
- `tests.test_links_loader.TestLinksLoader`

---

### 2. Scraper Orchestration (`test_all_scrapers_and_save_json.py`)

**Function**: `test_all_scrapers_and_save() -> List[Dict]`
```python
from tests.test_all_scrapers_and_save_json import test_all_scrapers_and_save

results = test_all_scrapers_and_save()
# Returns: List of result dicts with script, returncode, duration_seconds
# Runs all scrapers in parallel with work-stealing
```

**Key Features**:
- Parallel execution (4 production lines)
- Work-stealing for load balancing
- Progress tracking
- Waits for transcript files to be saved

**Dependencies**:
- All `scrapers.*` modules
- `tests.test_links_loader.TestLinksLoader`

---

### 3. Link and Batch Management (`test_links_loader.py`)

**Class**: `TestLinksLoader`
```python
from tests.test_links_loader import TestLinksLoader

loader = TestLinksLoader()  # or TestLinksLoader(file_path="custom/path.json")
batch_id = loader.get_batch_id()
youtube_links = loader.get_links('youtube')
bilibili_links = loader.get_links('bilibili')
reddit_links = loader.get_links('reddit')
article_links = loader.get_links('article')

# Iterate all links
for link_type, link in loader.iter_links():
    print(f"{link_type}: {link['url']}")
```

**Data Structure** (`tests/data/test_links.json`):
```json
{
  "batchId": "20251104_023548",
  "links": [
    {
      "id": "yt_001",
      "type": "youtube",
      "url": "https://youtube.com/watch?v=..."
    },
    {
      "id": "bili_001",
      "type": "bilibili",
      "url": "https://www.bilibili.com/video/..."
    }
  ]
}
```

---

### 4. Individual Scraper Usage Pattern

**Pattern used in all `test_*_scraper.py` files:**

```python
from scrapers.youtube_scraper import YouTubeScraper
from tests.test_links_loader import TestLinksLoader

# Initialize
loader = TestLinksLoader()
batch_id = loader.get_batch_id()
scraper = YouTubeScraper(headless=False)

# Extract content
for link in loader.get_links('youtube'):
    result = scraper.extract(
        url=link['url'],
        batch_id=batch_id,
        link_id=link['id']
    )
    # result contains: success, title, content, word_count, etc.

# Cleanup
scraper.close()
```

**Available Scrapers**:
- `scrapers.youtube_scraper.YouTubeScraper`
- `scrapers.bilibili_scraper.BilibiliScraper`
- `scrapers.bilibili_comments_scraper.BilibiliCommentsScraper`
- `scrapers.youtube_comments_scraper.YouTubeCommentsScraper`
- `scrapers.reddit_scraper.RedditScraper`
- `scrapers.article_scraper.ArticleScraper`

**Common Result Structure**:
```python
{
    "success": bool,
    "title": str,
    "content": str,
    "word_count": int,
    "batch_id": str,
    "link_id": str,
    "error": Optional[str],
    # ... scraper-specific fields
}
```

---

### 5. Research Agent Usage (`test_research_agent_full.py`)

**Pattern for running research agent:**

```python
from research.agent import DeepResearchAgent
from research.ui.mock_interface import MockConsoleInterface
from core.config import Config

# Get API key
config = Config()
api_key = config.get("qwen.api_key")

# Create UI (interactive or mock)
ui = MockConsoleInterface(
    auto_select_goal_id=None,
    auto_confirm_plan=True,
    auto_role=None,  # or "journalist", "researcher", etc.
    verbose=True
)

# Initialize agent
agent = DeepResearchAgent(
    api_key=api_key,
    ui=ui,
    additional_output_dirs=[str(output_dir)]  # Where to save reports
)

# Run research
result = agent.run_research(
    batch_id=batch_id,
    user_topic=None  # Let AI discover goals naturally
)

# Result contains:
# - status: "completed"
# - session_id: str
# - report_path: str
# - additional_report_paths: List[str]
# - selected_goal: str
# - usage: Dict (token counts)
```

---

## File Paths and Data Locations

### Input Data
- **Test Links**: `tests/data/test_links.json`
- **Config**: `config.yaml` (root level)

### Output Data
- **Scraper Results**: `tests/results/run_{batch_id}/*.json`
- **Manifest**: `tests/results/run_{batch_id}/manifest.json`
- **Research Reports**: `tests/results/reports/*.md`
- **Sessions**: `data/research/sessions/*.json`

### Batch ID Format
- Format: `YYYYMMDD_HHMMSS` (e.g., `20251104_023548`)
- Generated from `test_links.json` `batchId` field

---

## Environment Variables

### Test Execution
- `TEST_LINKS_FILE` - Override path to test links JSON
- `FORCE_INTERACTIVE=1` - Use real ConsoleInterface instead of Mock
- `TEST_AUTO_ROLE=<role>` - Auto-provide role when using MockConsoleInterface
- `NON_INTERACTIVE=1` - Force non-interactive mode

### API Keys
- `DASHSCOPE_API_KEY` or `QWEN_API_KEY` - Qwen API key
- Falls back to `config.yaml` (`qwen.api_key`)

---

## Common Patterns for Backend Integration

### 1. Running Scrapers with Progress Updates

```python
async def run_scrapers_with_progress(batch_id: str, ws_manager):
    """Run scrapers and send progress updates via WebSocket."""
    
    # Send start message
    await ws_manager.broadcast(batch_id, {
        "type": "scraping:start",
        "batch_id": batch_id,
        "message": "开始抓取内容..."
    })
    
    # Run scrapers (using working test function)
    result = await asyncio.to_thread(test_all_scrapers_and_save)
    
    # Send completion message
    await ws_manager.broadcast(batch_id, {
        "type": "scraping:complete",
        "batch_id": batch_id,
        "result": result
    })
    
    return result
```

### 2. Running Research Agent with Progress Updates

```python
async def run_research_with_progress(batch_id: str, ws_manager):
    """Run research agent and send progress updates via WebSocket."""
    
    # Create WebSocket UI adapter
    from app.services.websocket_ui import WebSocketUI
    ui = WebSocketUI(ws_manager, batch_id)
    
    # Get API key
    config = Config()
    api_key = config.get("qwen.api_key")
    
    # Create output directory
    output_dir = Path("tests/results/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize agent with WebSocket UI
    agent = DeepResearchAgent(
        api_key=api_key,
        ui=ui,  # WebSocket adapter instead of ConsoleInterface
        additional_output_dirs=[str(output_dir)]
    )
    
    # Run research (blocking, so use asyncio.to_thread)
    result = await asyncio.to_thread(
        agent.run_research,
        batch_id=batch_id,
        user_topic=None
    )
    
    return result
```

### 3. Link Formatting

```python
from utils.link_formatter import format_links

# Format URLs
urls = ["https://youtube.com/watch?v=...", "https://bilibili.com/video/..."]
formatted = format_links(urls)

# Returns dict with batch_id and formatted links
# Can then save to tests/data/test_links.json
```

---

## Key Takeaways

1. **Use test functions directly** - Don't re-implement what already works
2. **Keep WebSocket integration thin** - Just add progress callbacks
3. **Test functions are synchronous** - Use `asyncio.to_thread()` for async APIs
4. **TestLinksLoader is the source of truth** - For batch_id and link management
5. **Results go to `tests/results/`** - Standard location for all output

---

## Related Files

- `tests/test_full_workflow_integration.py` - Complete workflow
- `tests/test_all_scrapers_and_save_json.py` - Scraper orchestration
- `tests/test_links_loader.py` - Link management
- `tests/test_research_agent_full.py` - Research agent usage
- `tests/test_*_scraper.py` - Individual scraper patterns


