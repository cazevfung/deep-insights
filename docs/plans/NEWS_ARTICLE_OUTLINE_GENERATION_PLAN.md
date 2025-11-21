# News Article Outline Generation Service Plan

## Overview

This plan describes the implementation of a new backend service that generates news article outlines from Phase 0 summarized points. The service reads summarized data from previous research phases, sends it to Qwen (qwen-plus model) to create news article outlines, and outputs structured JSON containing article title, description, and related link IDs.

**Status**: Planning phase - not yet implemented

**Date**: 2025-11-20

---

## Objectives

1. **Create a new backend service** for news article outline generation (separate from research functions)
2. **Read Phase 0 summarized points** from JSON files in batch directories
3. **Generate news article outlines** using Qwen (qwen-plus model)
4. **Output structured JSON** with:
   - Article title
   - Article description
   - List of related link IDs (e.g., `bili_req1`, `yt_req2`)
5. **Use configuration-driven approach**: All paths and model settings from `config.yaml`
6. **Dedicated prompts**: All prompts stored in dedicated files (not hardcoded)

---

## Architecture

### Service Components

```
backend/app/
├── services/
│   └── news_outline_service.py      # Main service logic
└── routes/
    └── news.py                       # API endpoints for news functions
```

### Data Flow

```
Phase 0 JSON Files (data/research/batches/)
    │
    ├─ Read summarized points (key_facts, key_opinions, key_datapoints, topic_areas)
    │
    ▼
News Outline Service
    │
    ├─ Load prompt from dedicated file
    ├─ Format summarized points for Qwen
    ├─ Call Qwen API (qwen-plus model)
    │
    ▼
Generate Article Outline
    │
    ├─ Parse JSON response from Qwen
    ├─ Extract: title, description, related_link_ids
    │
    ▼
Save to data/news/outlines/
```

---

## Directory Structure

### New Directories

```
data/
└── news/
    ├── channels                      # Existing
    └── outlines/                     # NEW - Store generated outlines
        └── {outline_id}.json

news/                                 # NEW - News-specific prompts (parallel to research/)
└── prompts/
    └── article_outline/
        ├── system.md                 # System prompt for outline generation
        └── instructions.md           # Detailed instructions for AI

docs/
└── plans/
    └── NEWS_ARTICLE_OUTLINE_GENERATION_PLAN.md  # This file
```

---

## Configuration (config.yaml)

### New Configuration Sections

```yaml
news:
  # Path configuration for news functions
  paths:
    outlines_dir: 'data/news/outlines'      # Where outline JSON files are saved
    batch_source_dir: 'data/research/batches'  # Source for Phase 0 data
  
  # AI model configuration for news outline generation
  outline_generation:
    model: 'qwen-plus'                      # Use qwen-plus model
    temperature: 0.7
    max_tokens: 4000
    api_key: null                           # Falls back to qwen.api_key if null
    language: 'zh-CN'                       # Output language
  
  # Prompt configuration
  prompts:
    base_dir: 'news/prompts'                # Base directory for news prompts
    article_outline:
      system_prompt_path: 'news/prompts/article_outline/system.md'
      instructions_path: 'news/prompts/article_outline/instructions.md'
```

### Configuration Access Pattern

```python
# Service initialization
config = Config()
news_config = config.get('news', {})
outline_config = news_config.get('outline_generation', {})
paths_config = news_config.get('paths', {})
prompts_config = news_config.get('prompts', {})

# Get model settings
model = outline_config.get('model', 'qwen-plus')
temperature = outline_config.get('temperature', 0.7)
max_tokens = outline_config.get('max_tokens', 4000)

# Get paths
outlines_dir = Path(paths_config.get('outlines_dir', 'data/news/outlines'))
batch_source_dir = Path(paths_config.get('batch_source_dir', 'data/research/batches'))

# Get prompt paths
system_prompt_path = Path(prompts_config.get('article_outline', {}).get('system_prompt_path'))
```

---

## Phase 0 Data Format

### Input JSON Structure

Reference: `data/research/batches/run_{batch_id}/{batch_id}_{link_id}_complete.json`

```json
{
  "batch_id": "20251120_120414",
  "link_id": "bili_req1",
  "source": "bilibili",
  "metadata": {
    "title": "...",
    "author": "...",
    "url": "...",
    "word_count": 7762,
    "publish_date": ""
  },
  "transcript": "...",
  "comments": null,
  "summary": {
    "transcript_summary": {
      "key_facts": [
        "事实点1",
        "事实点2",
        ...
      ],
      "key_opinions": [
        "观点1",
        "观点2",
        ...
      ],
      "key_datapoints": [
        "数据点1",
        "数据点2",
        ...
      ],
      "topic_areas": [
        "主题1",
        "主题2",
        ...
      ],
      "word_count": 6,
      "total_markers": 83
    },
    "comments_summary": {},
    "created_at": "2025-11-20T20:05:53.347094",
    "model_used": "qwen-flash"
  },
  "completed_at": 1763640365.5558236
}
```

### Data Extraction

The service should extract:
- **Summarized points**: `summary.transcript_summary.key_facts`, `key_opinions`, `key_datapoints`
- **Topic areas**: `summary.transcript_summary.topic_areas`
- **Link ID**: `link_id` (e.g., `bili_req1`)
- **Source metadata**: `metadata.title`, `metadata.url`, `source`
- **Batch ID**: `batch_id` (to group related outlines)

---

## Output Format

### Generated Outline JSON Structure

```json
{
  "outline_id": "outline_20251120_120414_001",
  "generated_at": "2025-11-20T20:15:30.123456",
  "batch_id": "20251120_120414",
  "article": {
    "title": "文章标题",
    "description": "文章描述/摘要",
    "related_link_ids": [
      "bili_req1",
      "yt_req2",
      "article_req3"
    ]
  },
  "metadata": {
    "model_used": "qwen-plus",
    "prompt_version": "v1.0",
    "source_batch": "20251120_120414",
    "total_sources": 3
  }
}
```

### Output File Naming

- Pattern: `{outline_id}.json`
- Location: `data/news/outlines/{outline_id}.json`
- Outline ID format: `outline_{timestamp}_{sequence}` (e.g., `outline_20251120_120415_001`)

---

## Service Implementation

### NewsOutlineService Class

```python
# backend/app/services/news_outline_service.py

class NewsOutlineService:
    """Service for generating news article outlines from Phase 0 summarized points."""
    
    def __init__(self, config: Config):
        self.config = config
        self._qwen_client = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from config.yaml."""
        news_config = self.config.get('news', {})
        self.outline_config = news_config.get('outline_generation', {})
        self.paths_config = news_config.get('paths', {})
        self.prompts_config = news_config.get('prompts', {})
        
        # Initialize paths
        self.outlines_dir = Path(self.paths_config.get('outlines_dir', 'data/news/outlines'))
        self.batch_source_dir = Path(self.paths_config.get('batch_source_dir', 'data/research/batches'))
        
        # Create directories if needed
        self.outlines_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_qwen_client(self) -> QwenStreamingClient:
        """Get or create Qwen client."""
        if self._qwen_client is None:
            api_key = self.outline_config.get('api_key') or self.config.get('qwen.api_key')
            model = self.outline_config.get('model', 'qwen-plus')
            self._qwen_client = QwenStreamingClient(api_key=api_key, model=model)
        return self._qwen_client
    
    def _load_prompt(self, prompt_type: str = 'system') -> str:
        """Load prompt from dedicated file."""
        # Implementation: Load from news/prompts/article_outline/
        pass
    
    def _extract_summarized_points(self, json_file: Path) -> Dict[str, Any]:
        """Extract summarized points from Phase 0 JSON file."""
        # Implementation: Read JSON and extract summary data
        pass
    
    def _format_summarized_points_for_prompt(self, summarized_points: Dict[str, Any]) -> str:
        """Format summarized points into prompt-friendly text."""
        # Implementation: Format key_facts, key_opinions, key_datapoints, topic_areas
        pass
    
    def _generate_outline(self, summarized_points_text: str, link_ids: List[str]) -> Dict[str, Any]:
        """Call Qwen API to generate article outline."""
        # Implementation: Build prompt, call Qwen, parse JSON response
        pass
    
    def generate_outline_from_batch(
        self, 
        batch_id: str, 
        link_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate article outline from a batch of Phase 0 files."""
        # Implementation: Main orchestration method
        pass
    
    def save_outline(self, outline: Dict[str, Any]) -> Path:
        """Save generated outline to JSON file."""
        # Implementation: Save to data/news/outlines/
        pass
```

---

## API Routes

### FastAPI Endpoint

```python
# backend/app/routes/news.py

router = APIRouter(prefix="/api/news", tags=["news"])

class GenerateOutlineRequest(BaseModel):
    batch_id: str
    link_ids: Optional[List[str]] = None  # If None, process all links in batch

class GenerateOutlineResponse(BaseModel):
    status: Literal["success", "error"]
    outline_id: Optional[str] = None
    outline: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@router.post("/outlines/generate", response_model=GenerateOutlineResponse)
async def generate_outline(request: GenerateOutlineRequest):
    """Generate news article outline from Phase 0 summarized points."""
    # Implementation
    pass

@router.get("/outlines/{outline_id}")
async def get_outline(outline_id: str):
    """Get a generated outline by ID."""
    # Implementation
    pass

@router.get("/outlines")
async def list_outlines(batch_id: Optional[str] = None):
    """List all generated outlines, optionally filtered by batch_id."""
    # Implementation
    pass
```

### Route Registration

Register in `backend/app/main.py`:

```python
from app.routes import news as news_routes

app.include_router(news_routes.router)
```

---

## Prompt Design

### System Prompt (`news/prompts/article_outline/system.md`)

```markdown
你是一个专业的新闻文章大纲生成助手。你的任务是根据提供的内容摘要，生成新闻文章的大纲。

## 你的任务

1. 分析提供的内容摘要（包括关键事实、观点、数据点和主题领域）
2. 识别可以写成新闻文章的主题和角度
3. 生成一个吸引人的文章标题
4. 撰写一个简洁的文章描述/摘要
5. 识别与文章主题相关的所有链接ID

## 输出要求

- 必须以JSON格式输出
- JSON必须包含以下字段：
  - `title`: 文章标题（字符串）
  - `description`: 文章描述（字符串，100-300字）
  - `related_link_ids`: 相关链接ID列表（字符串数组）

## 注意事项

- 标题应该吸引人且准确反映内容
- 描述应该简洁地概括文章的核心内容和价值
- 相关链接ID应该包含所有与主题相关的来源链接
- 确保输出是有效的JSON格式
```

### Instructions Prompt (`news/prompts/article_outline/instructions.md`)

```markdown
# 新闻文章大纲生成详细说明

## 输入数据格式

你会收到以下结构化的内容摘要：

### 关键事实 (Key Facts)
- 事实点列表

### 关键观点 (Key Opinions)
- 观点列表

### 关键数据点 (Key Datapoints)
- 数据点列表

### 主题领域 (Topic Areas)
- 主题列表

### 相关链接ID (Link IDs)
- 来源链接的ID列表（如 bili_req1, yt_req2）

## 生成逻辑

1. **主题识别**：从主题领域和关键事实中识别最值得写成新闻文章的主题
2. **角度选择**：选择一个新颖、有价值的角度来撰写文章
3. **标题生成**：创建一个既能吸引读者又能准确反映内容的标题
4. **描述撰写**：用100-300字描述文章将涵盖的内容和价值
5. **链接关联**：确定哪些链接ID的内容与文章主题相关

## JSON输出示例

```json
{
  "title": "健康中国战略下的基层医疗重点突破",
  "description": "本文深入分析健康中国战略的核心要点，重点关注基层医疗在全民健康中的重要作用。文章将探讨以人民健康为中心的理念转变，以及预防为主、关口前移的健康管理新思路。",
  "related_link_ids": ["bili_req1", "yt_req2"]
}
```

## 质量标准

- 标题：准确、吸引人、不超过30字
- 描述：清晰、简洁、100-300字
- 链接关联：准确、完整、包含所有相关来源
```

---

## Implementation Steps

### Phase 1: Configuration Setup
1. ✅ Add `news` section to `config.yaml`
2. ✅ Define paths configuration for news functions
3. ✅ Define AI model configuration for outline generation
4. ✅ Define prompts configuration

### Phase 2: Directory Structure
1. ✅ Create `data/news/outlines/` directory
2. ✅ Create `news/prompts/article_outline/` directory
3. ✅ Create prompt files (`system.md`, `instructions.md`)

### Phase 3: Service Implementation
1. ✅ Create `NewsOutlineService` class
2. ✅ Implement configuration loading
3. ✅ Implement Phase 0 JSON reading and parsing
4. ✅ Implement summarized points extraction
5. ✅ Implement prompt loading from files
6. ✅ Implement Qwen API integration
7. ✅ Implement JSON parsing and validation
8. ✅ Implement outline saving

### Phase 4: API Routes
1. ✅ Create `backend/app/routes/news.py`
2. ✅ Implement `/api/news/outlines/generate` endpoint
3. ✅ Implement `/api/news/outlines/{outline_id}` endpoint
4. ✅ Implement `/api/news/outlines` listing endpoint
5. ✅ Register routes in `main.py`

### Phase 5: Error Handling & Validation
1. ✅ Handle missing Phase 0 files
2. ✅ Handle invalid JSON responses from Qwen
3. ✅ Validate output JSON structure
4. ✅ Add logging for debugging

### Phase 6: Testing
1. ✅ Unit tests for service methods
2. ✅ Integration tests for API endpoints
3. ✅ Test with real Phase 0 data
4. ✅ Test error scenarios

---

## Dependencies

### Existing Dependencies (Already Available)
- `fastapi` - API framework
- `pydantic` - Data validation
- `loguru` - Logging
- `research.client.QwenStreamingClient` - Qwen API client
- `core.config.Config` - Configuration management

### No New Dependencies Required
All necessary dependencies are already available in the project.

---

## Error Handling

### Common Error Scenarios

1. **Missing Phase 0 Files**
   - Error: Batch directory or link files not found
   - Handling: Return error with clear message, suggest checking batch_id

2. **Invalid JSON from Qwen**
   - Error: Qwen returns non-JSON or malformed JSON
   - Handling: Log raw response, return error, optionally retry with reformatted prompt

3. **Missing Summary Data**
   - Error: Phase 0 file exists but missing `summary.transcript_summary`
   - Handling: Return error, indicate which link_id has incomplete data

4. **Configuration Errors**
   - Error: Missing required config values
   - Handling: Use sensible defaults, log warnings

5. **File System Errors**
   - Error: Cannot create directories or write files
   - Handling: Check permissions, return error with actionable message

---

## Logging

### Log Points

```python
logger.info(f"Loading Phase 0 data from batch: {batch_id}")
logger.debug(f"Extracted summarized points: {len(key_facts)} facts, {len(key_opinions)} opinions")
logger.info(f"Generating outline with Qwen ({model})")
logger.info(f"Generated outline saved: {outline_id}")
logger.error(f"Failed to generate outline: {error}")
```

---

## Future Enhancements (Out of Scope)

These are potential future improvements but not part of the initial implementation:

1. **Batch Processing**: Process multiple batches in parallel
2. **Outline Versioning**: Track different versions of outlines
3. **Outline Comparison**: Compare outlines generated from different batches
4. **Caching**: Cache generated outlines to avoid regeneration
5. **Outline Templates**: Support different outline templates/styles
6. **Multi-language Support**: Generate outlines in different languages
7. **Outline Refinement**: Allow users to refine generated outlines
8. **Related Articles**: Suggest related articles based on outlines

---

## Testing Strategy

### Unit Tests

```python
# tests/test_news_outline_service.py

def test_extract_summarized_points():
    """Test extraction of summarized points from Phase 0 JSON."""
    pass

def test_format_summarized_points_for_prompt():
    """Test formatting of summarized points into prompt text."""
    pass

def test_load_prompt():
    """Test loading prompts from dedicated files."""
    pass

def test_generate_outline():
    """Test outline generation with mock Qwen response."""
    pass

def test_save_outline():
    """Test saving outline to JSON file."""
    pass
```

### Integration Tests

```python
# tests/test_news_api.py

def test_generate_outline_endpoint():
    """Test API endpoint for outline generation."""
    pass

def test_get_outline_endpoint():
    """Test API endpoint for retrieving outline."""
    pass

def test_list_outlines_endpoint():
    """Test API endpoint for listing outlines."""
    pass
```

### Manual Testing Steps

1. **Prepare Test Data**
   - Ensure Phase 0 JSON files exist in `data/research/batches/run_{batch_id}/`
   - Verify files contain `summary.transcript_summary` data

2. **Test Service**
   - Call `generate_outline_from_batch()` with a valid batch_id
   - Verify outline JSON is generated correctly
   - Verify outline is saved to `data/news/outlines/`

3. **Test API**
   - POST to `/api/news/outlines/generate` with batch_id
   - Verify response contains valid outline
   - GET `/api/news/outlines/{outline_id}` to retrieve outline
   - GET `/api/news/outlines?batch_id={batch_id}` to list outlines

---

## Notes

1. **Separation from Research Functions**: This service is intentionally separate from research functions. It uses Phase 0 data as input but is part of the news workflow, not research workflow.

2. **Configuration-Driven**: All paths, model settings, and prompt paths are configurable via `config.yaml` to maintain flexibility and avoid hardcoding.

3. **Prompt Files**: All prompts are stored in dedicated markdown files in `news/prompts/` directory, following the same pattern as `research/prompts/`.

4. **Link ID Format**: Link IDs follow the pattern `{source}_{request_id}` (e.g., `bili_req1`, `yt_req2`). The service should preserve these IDs exactly as they appear in the Phase 0 files.

5. **Batch Processing**: The initial implementation processes one batch at a time. Future enhancements could support processing multiple batches or filtering by link_ids.

---

## Approval Checklist

Before implementation begins, confirm:

- [x] Plan document created
- [ ] Architecture reviewed
- [ ] Configuration structure approved
- [ ] Output format confirmed
- [ ] Prompt design reviewed
- [ ] API endpoints approved
- [ ] Directory structure confirmed
- [ ] Error handling strategy approved

---

**Next Steps**: Once this plan is approved, proceed with implementation following the phases outlined above.
