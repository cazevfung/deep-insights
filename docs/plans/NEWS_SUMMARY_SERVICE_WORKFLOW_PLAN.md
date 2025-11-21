# News Summary Service Workflow Plan

## Overview

This plan describes the implementation of a new workflow service that orchestrates the complete news article generation pipeline. The service integrates channel scraping, content scraping with Phase 0 summarization, outline generation, and article generation into a single automated workflow.

**Status**: Planning phase - not yet implemented

**Date**: 2025-11-20

---

## Objectives

1. **Create a unified workflow service** that links channel scraping, content scraping, Phase 0 summarization, outline generation, and article generation
2. **Session-based processing** with unique session IDs for tracking workflows
3. **Date range filtering** for channel video scraping
4. **Adapted research workflow** that saves to news directories instead of research directories
5. **Automated pipeline** from channel links to final news articles
6. **Configuration-driven approach**: All paths, models, and settings from `config.yaml`
7. **Dedicated prompts**: All workflow-specific prompts stored in dedicated files

---

## Architecture

### Service Components

```
backend/app/
├── services/
│   ├── channel_scraper_service.py      # Existing - Scrapes channel video links
│   ├── news_outline_service.py         # Existing - Generates article outlines
│   ├── news_article_service.py         # Existing - Generates full articles
│   ├── workflow_service.py             # Existing - Research workflow orchestration
│   └── news_summary_workflow_service.py  # NEW - Main workflow orchestrator
└── routes/
    └── news.py                         # Extend existing - Add workflow endpoints
```

### High-Level Data Flow

```
User Trigger (date range)
    │
    ├─ Create Session ID
    │
    ▼
Step 1: Channel Scraping
    │
    ├─ Load channels from data/news/channels
    ├─ Scrape video links within date range
    ├─ Save batch file to data/news/sessions/{session_id}/channel_batch_{batch_id}.txt
    │
    ▼
Step 2: Content Scraping + Phase 0 Summarization
    │
    ├─ Load links from channel batch file
    ├─ Run scraping service (adapted for news directory)
    ├─ Run Phase 0 summarization (adapted for news directory)
    ├─ Save to data/news/sessions/{session_id}/batches/run_{batch_id}/
    │   └─ Files: {batch_id}_{link_id}_complete.json (with Phase 0 summaries)
    │
    ▼
Step 3: Outline Generation
    │
    ├─ Load Phase 0 files from news session batch
    ├─ Generate outline using NewsOutlineService
    ├─ Save to data/news/sessions/{session_id}/outlines/{outline_id}.json
    │
    ▼
Step 4: Article Generation
    │
    ├─ Load outline from news session
    ├─ Load full content from Phase 0 batch files
    ├─ Generate article using NewsArticleService
    ├─ Save to data/news/sessions/{session_id}/articles/{article_id}.md
    │
    ▼
Complete: Return session summary with all artifacts
```

---

## Directory Structure

### New Directories

```
data/
└── news/
    ├── channels                      # Existing - Channel definitions
    ├── outlines/                     # Existing - Generated outlines (standalone)
    ├── articles/                     # Existing - Generated articles (standalone)
    └── sessions/                     # NEW - Session-based workflow artifacts
        └── {session_id}/
            ├── session_metadata.json  # Session info, date range, status, timestamps
            ├── channel_batch_{batch_id}.txt  # Channel scraping results
            ├── batches/               # Scraped content + Phase 0 summaries
            │   └── run_{batch_id}/
            │       └── {batch_id}_{link_id}_complete.json
            ├── outlines/             # Generated outlines (session-specific)
            │   └── {outline_id}.json
            └── articles/             # Generated articles (session-specific)
                ├── {article_id}.md
                └── {article_id}.json

news/                                 # Existing - News-specific prompts
└── prompts/
    ├── article_outline/              # Existing - Outline generation prompts
    ├── article_generation/           # Existing - Article generation prompts
    └── workflow/                     # NEW - Workflow orchestration prompts
        ├── system.md                 # System prompt for workflow orchestration
        └── instructions.md           # Detailed workflow instructions
```

---

## Configuration (config.yaml)

### New Configuration Sections

Add to existing `news` section in `config.yaml`:

```yaml
news:
  # Path configuration for news functions
  paths:
    outlines_dir: 'data/news/outlines'              # Existing - Standalone outlines
    batch_source_dir: 'data/research/batches'       # Existing - For standalone services
    articles_dir: 'data/news/articles'              # Existing - Standalone articles
    sessions_dir: 'data/news/sessions'              # NEW - Session-based workflow artifacts
    channels_file: 'data/news/channels'             # Existing - Channel definitions
  
  # Workflow service configuration
  workflow:                                         # NEW - Workflow orchestration config
    # Session management
    session_id_format: 'news_session_{timestamp}_{sequence}'  # Format: news_session_20251120_120000_001
    session_metadata_file: 'session_metadata.json'  # Metadata file name in session dir
    
    # Workflow steps configuration
    steps:
      channel_scraping:
        enabled: true
        save_to_session: true                       # Save channel batch to session dir
        batch_file_format: 'channel_batch_{batch_id}.txt'
      
      content_scraping:
        enabled: true
        use_news_directory: true                    # Save to news/sessions instead of research/batches
        run_phase0_summarization: true              # Automatically run Phase 0
        batch_dir_format: 'batches/run_{batch_id}'  # Relative to session dir
      
      outline_generation:
        enabled: true
        auto_generate: true                         # Automatically generate after Phase 0
        save_to_session: true                       # Save to session/outlines
      
      article_generation:
        enabled: true
        auto_generate: true                         # Automatically generate after outline
        save_to_session: true                       # Save to session/articles
    
    # Error handling
    continue_on_error: true                         # Continue to next step if one fails
    save_partial_results: true                      # Save results even if workflow incomplete
  
  # AI model configuration (reuse existing)
  outline_generation:                               # Existing
    model: 'qwen-plus'
    temperature: 0.7
    max_tokens: 4000
    api_key: null
    language: 'zh-CN'
  
  article_generation:                               # Existing
    model: 'qwen-plus'
    temperature: 0.7
    max_tokens: 16000
    api_key: null
    language: 'zh-CN'
  
  # Prompt configuration
  prompts:
    base_dir: 'news/prompts'                        # Existing
    article_outline:                                # Existing
      system_prompt_path: 'news/prompts/article_outline/system.md'
      instructions_path: 'news/prompts/article_outline/instructions.md'
    article_generation:                             # Existing
      system_prompt_path: 'news/prompts/article_generation/system.md'
      instructions_path: 'news/prompts/article_generation/instructions.md'
    workflow:                                       # NEW - Workflow prompts
      system_prompt_path: 'news/prompts/workflow/system.md'
      instructions_path: 'news/prompts/workflow/instructions.md'
```

### Configuration Access Pattern

```python
# Service initialization
config = Config()
news_config = config.get('news', {})
workflow_config = news_config.get('workflow', {})
paths_config = news_config.get('paths', {})

# Get paths
sessions_dir = Path(paths_config.get('sessions_dir', 'data/news/sessions'))
channels_file = Path(paths_config.get('channels_file', 'data/news/channels'))

# Get workflow settings
steps_config = workflow_config.get('steps', {})
continue_on_error = workflow_config.get('continue_on_error', True)
```

---

## Service Implementation

### NewsSummaryWorkflowService Class

```python
# backend/app/services/news_summary_workflow_service.py

class NewsSummaryWorkflowService:
    """Orchestrates the complete news summary workflow from channels to articles."""
    
    def __init__(self, config: Config):
        self.config = config
        self._load_config()
        self._initialize_services()
    
    def _load_config(self):
        """Load configuration from config.yaml."""
        news_config = self.config.get('news', {})
        self.workflow_config = news_config.get('workflow', {})
        self.paths_config = news_config.get('paths', {})
        
        # Initialize paths
        project_root = find_project_root() if find_project_root else Path.cwd()
        sessions_dir_str = self.paths_config.get('sessions_dir', 'data/news/sessions')
        
        if Path(sessions_dir_str).is_absolute():
            self.sessions_dir = Path(sessions_dir_str)
        else:
            self.sessions_dir = project_root / sessions_dir_str
        
        # Create directories if needed
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def _initialize_services(self):
        """Initialize dependent services."""
        from backend.app.services.channel_scraper_service import ChannelScraperService
        from backend.app.services.news_outline_service import NewsOutlineService
        from backend.app.services.news_article_service import NewsArticleService
        from backend.app.services.workflow_service import WorkflowService
        from backend.app.services.scraping_service import ScrapingService
        from backend.app.services.progress_service import ProgressService
        
        # Initialize services
        self.channel_scraper = ChannelScraperService()
        self.outline_service = NewsOutlineService(self.config)
        self.article_service = NewsArticleService(self.config)
        # Note: WorkflowService and ScrapingService will be adapted/used via wrapper
    
    def create_session(self, date_range: Dict[str, str]) -> str:
        """Create a new workflow session and return session ID."""
        # Implementation: Generate session ID, create session directory, save metadata
        pass
    
    def run_workflow(
        self,
        session_id: str,
        date_range: Dict[str, str],
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Run the complete workflow for a session."""
        # Implementation: Orchestrate all steps
        pass
    
    def _step_channel_scraping(self, session_id: str, date_range: Dict) -> Dict:
        """Step 1: Scrape channels for video links within date range."""
        # Implementation: Call ChannelScraperService, save to session dir
        pass
    
    def _step_content_scraping_and_phase0(
        self,
        session_id: str,
        channel_batch_file: Path
    ) -> Dict:
        """Step 2: Scrape links and run Phase 0 summarization (adapted for news directory)."""
        # Implementation: Adapt WorkflowService to save to news/sessions instead of research/batches
        pass
    
    def _step_outline_generation(self, session_id: str, batch_id: str) -> Dict:
        """Step 3: Generate news outline from Phase 0 summaries."""
        # Implementation: Call NewsOutlineService, save to session/outlines
        pass
    
    def _step_article_generation(self, session_id: str, outline_id: str) -> Dict:
        """Step 4: Generate news article from outline."""
        # Implementation: Call NewsArticleService, save to session/articles
        pass
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current status of a workflow session."""
        # Implementation: Load session metadata, check step completion
        pass
    
    def load_session_metadata(self, session_id: str) -> Dict[str, Any]:
        """Load session metadata JSON file."""
        # Implementation: Read session_metadata.json
        pass
    
    def save_session_metadata(self, session_id: str, metadata: Dict[str, Any]):
        """Save session metadata JSON file."""
        # Implementation: Write session_metadata.json
        pass
```

---

## Workflow Adaptation Strategy

### Adapting Research Workflow for News Directory

The key challenge is adapting the existing research workflow (which saves to `data/research/batches`) to save to `data/news/sessions/{session_id}/batches` instead.

**Approach 1: Configuration Override** (Preferred)
- Modify `WorkflowService` and related services to accept a custom `batches_dir` parameter
- Create wrapper functions that set the batches directory to the session directory
- Reuse existing code with path override

**Approach 2: Wrapper Service** (Alternative)
- Create a news-specific wrapper around `WorkflowService`
- Intercept file paths and redirect to news directory
- Copy/adapt Phase 0 summarization logic

**Implementation Details:**

```python
def _step_content_scraping_and_phase0(self, session_id: str, channel_batch_file: Path):
    """Run scraping + Phase 0 adapted for news directory."""
    session_dir = self.sessions_dir / session_id
    news_batches_dir = session_dir / 'batches'
    
    # Read links from channel batch file
    links = self._load_links_from_channel_batch(channel_batch_file)
    
    # Create batch ID
    batch_id = self._generate_batch_id()
    
    # Temporarily override config for batches directory
    # (or pass as parameter to WorkflowService)
    original_batches_dir = self.config.get('storage.paths.batches_dir')
    try:
        # Override batches directory
        self.config.set_override('storage.paths.batches_dir', str(news_batches_dir))
        
        # Run scraping + Phase 0 using existing workflow
        from backend.app.services.workflow_service import WorkflowService
        workflow_service = WorkflowService(...)
        result = await workflow_service.run_scraping_and_phase0(
            batch_id=batch_id,
            links=links,
            session_id=session_id  # New parameter
        )
        
        return {
            'batch_id': batch_id,
            'status': 'completed',
            'result': result
        }
    finally:
        # Restore original config
        if original_batches_dir:
            self.config.remove_override('storage.paths.batches_dir')
```

---

## Session Metadata Format

### Session Metadata JSON

Saved as: `data/news/sessions/{session_id}/session_metadata.json`

```json
{
  "session_id": "news_session_20251120_120000_001",
  "created_at": "2025-11-20T12:00:00.123456",
  "date_range": {
    "start_date": "2025-11-01",
    "end_date": "2025-11-15"
  },
  "status": "completed",
  "current_step": "article_generation",
  "steps": {
    "channel_scraping": {
      "status": "completed",
      "completed_at": "2025-11-20T12:05:00.123456",
      "batch_id": "channel_batch_20251120_120500",
      "total_videos": 150,
      "channels_scraped": 25
    },
    "content_scraping": {
      "status": "completed",
      "completed_at": "2025-11-20T13:30:00.123456",
      "batch_id": "20251120_133000",
      "total_links": 150,
      "successful_scrapes": 145,
      "failed_scrapes": 5,
      "phase0_completed": true
    },
    "outline_generation": {
      "status": "completed",
      "completed_at": "2025-11-20T14:00:00.123456",
      "outline_id": "outline_20251120_140000_001",
      "batch_id": "20251120_133000"
    },
    "article_generation": {
      "status": "completed",
      "completed_at": "2025-11-20T14:30:00.123456",
      "article_id": "article_20251120_143000_001",
      "outline_id": "outline_20251120_140000_001"
    }
  },
  "artifacts": {
    "channel_batch_file": "channel_batch_20251120_120500.txt",
    "content_batch_dir": "batches/run_20251120_133000",
    "outline_file": "outlines/outline_20251120_140000_001.json",
    "article_file": "articles/article_20251120_143000_001.md"
  },
  "errors": [],
  "metadata": {
    "model_used": "qwen-plus",
    "prompt_version": "v1.0"
  }
}
```

---

## API Routes

### FastAPI Endpoint Extensions

Extend existing `backend/app/routes/news.py`:

```python
# backend/app/routes/news.py

# NEW: Workflow models
class CreateWorkflowSessionRequest(BaseModel):
    start_date: str  # Format: YYYY-MM-DD
    end_date: str    # Format: YYYY-MM-DD
    channel_ids: Optional[List[str]] = None  # Optional: filter specific channels
    options: Optional[Dict[str, Any]] = None  # Workflow options

class CreateWorkflowSessionResponse(BaseModel):
    status: Literal["success", "error"]
    session_id: Optional[str] = None
    error: Optional[str] = None

class RunWorkflowRequest(BaseModel):
    session_id: str
    options: Optional[Dict[str, Any]] = None

class RunWorkflowResponse(BaseModel):
    status: Literal["success", "error", "in_progress"]
    session_id: str
    current_step: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    current_step: Optional[str] = None
    metadata: Dict[str, Any]

# NEW: Workflow endpoints
@router.post("/workflow/sessions", response_model=CreateWorkflowSessionResponse)
async def create_workflow_session(request: CreateWorkflowSessionRequest):
    """Create a new workflow session."""
    # Implementation
    pass

@router.post("/workflow/sessions/{session_id}/run", response_model=RunWorkflowResponse)
async def run_workflow(session_id: str, request: Optional[RunWorkflowRequest] = None):
    """Run the complete workflow for a session."""
    # Implementation
    pass

@router.get("/workflow/sessions/{session_id}/status", response_model=SessionStatusResponse)
async def get_workflow_session_status(session_id: str):
    """Get current status of a workflow session."""
    # Implementation
    pass

@router.get("/workflow/sessions")
async def list_workflow_sessions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None
):
    """List all workflow sessions, optionally filtered by date range or status."""
    # Implementation
    pass

@router.get("/workflow/sessions/{session_id}/metadata")
async def get_workflow_session_metadata(session_id: str):
    """Get full session metadata."""
    # Implementation
    pass

@router.get("/workflow/sessions/{session_id}/artifacts")
async def get_workflow_session_artifacts(session_id: str):
    """Get all artifacts for a session (links to files)."""
    # Implementation
    pass
```

---

## Prompt Design

### System Prompt (`news/prompts/workflow/system.md`)

```markdown
你是一个专业的新闻工作流程编排助手。你的任务是协调和管理新闻文章生成的完整流程。

## 你的任务

1. 管理新闻工作流程的各个步骤
2. 跟踪每个步骤的完成状态
3. 处理步骤之间的数据传递
4. 记录工作流程的执行日志
5. 处理错误和异常情况

## 工作流程步骤

1. **频道抓取**: 从YouTube频道抓取指定日期范围内的视频链接
2. **内容抓取和摘要**: 抓取视频/文章内容并生成Phase 0摘要
3. **大纲生成**: 基于Phase 0摘要生成文章大纲
4. **文章生成**: 基于大纲和完整内容生成最终文章

## 注意事项

- 确保每个步骤的数据正确传递到下一步
- 记录详细的执行日志
- 处理部分失败的情况
- 保存中间结果以便调试和恢复
```

### Instructions Prompt (`news/prompts/workflow/instructions.md`)

```markdown
# 新闻工作流程编排详细说明

## 工作流程概览

这是一个端到端的新闻文章生成工作流程，包括以下步骤：

1. **频道抓取** (Channel Scraping)
   - 从配置的YouTube频道列表抓取视频链接
   - 按日期范围过滤视频
   - 生成频道批次文件

2. **内容抓取和Phase 0摘要** (Content Scraping + Phase 0)
   - 抓取所有链接的完整内容（视频转录、文章内容等）
   - 运行Phase 0摘要生成（快速摘要，提取关键事实、观点、数据点）
   - 保存到会话批次目录

3. **大纲生成** (Outline Generation)
   - 从Phase 0摘要中提取关键信息
   - 使用AI生成文章大纲（标题、描述、相关链接ID）
   - 保存大纲JSON文件

4. **文章生成** (Article Generation)
   - 从大纲中获取相关链接ID
   - 检索完整的转录/内容文本
   - 使用AI生成完整的Markdown格式文章
   - 保存文章文件和元数据

## 数据流

```
频道链接 → 内容抓取 → Phase 0摘要 → 大纲生成 → 文章生成
```

## 会话管理

- 每个工作流程实例都有一个唯一的会话ID
- 会话ID格式: `news_session_{timestamp}_{sequence}`
- 所有会话相关的文件都保存在 `data/news/sessions/{session_id}/`
- 会话元数据保存在 `session_metadata.json`

## 错误处理

- 如果某个步骤失败，根据配置决定是否继续
- 保存部分结果以便恢复和调试
- 记录详细的错误信息到会话元数据

## 配置驱动

- 所有路径、模型设置、提示路径都从 `config.yaml` 读取
- 工作流程步骤可以单独启用/禁用
- 支持自定义选项覆盖默认配置
```

---

## Implementation Steps

### Phase 1: Configuration Setup
1. Add `workflow` section to `news` config in `config.yaml`
2. Add `sessions_dir` to `news.paths` configuration
3. Add `workflow` to `news.prompts` configuration
4. Define workflow steps configuration
5. Define error handling settings

### Phase 2: Directory Structure
1. Create `data/news/sessions/` directory structure
2. Create `news/prompts/workflow/` directory
3. Create prompt files (`system.md`, `instructions.md`)

### Phase 3: Service Implementation
1. Create `NewsSummaryWorkflowService` class
2. Implement configuration loading
3. Implement session creation and management
4. Implement `_step_channel_scraping()` method
5. Implement `_step_content_scraping_and_phase0()` method (with directory adaptation)
6. Implement `_step_outline_generation()` method
7. Implement `_step_article_generation()` method
8. Implement `run_workflow()` orchestration method
9. Implement session status and metadata management

### Phase 4: Workflow Adaptation
1. Create wrapper/adapter for `WorkflowService` to save to news directory
2. Adapt Phase 0 summarization to use news session directory
3. Ensure file paths are correctly redirected
4. Test directory structure preservation

### Phase 5: API Routes
1. Extend `backend/app/routes/news.py` with workflow endpoints
2. Implement `/api/news/workflow/sessions` (POST - create session)
3. Implement `/api/news/workflow/sessions/{session_id}/run` (POST - run workflow)
4. Implement `/api/news/workflow/sessions/{session_id}/status` (GET - get status)
5. Implement `/api/news/workflow/sessions` (GET - list sessions)
6. Implement `/api/news/workflow/sessions/{session_id}/metadata` (GET - get metadata)
7. Implement `/api/news/workflow/sessions/{session_id}/artifacts` (GET - get artifacts)

### Phase 6: Error Handling & Validation
1. Handle missing channel files
2. Handle scraping failures
3. Handle Phase 0 summarization failures
4. Handle outline generation failures
5. Handle article generation failures
6. Implement partial result saving
7. Add comprehensive logging

### Phase 7: Testing
1. Unit tests for service methods
2. Integration tests for workflow steps
3. End-to-end tests for complete workflow
4. Test error scenarios
5. Test session management

---

## Dependencies

### Existing Dependencies (Already Available)
- `fastapi` - API framework
- `pydantic` - Data validation
- `loguru` - Logging
- `research.client.QwenStreamingClient` - Qwen API client
- `core.config.Config` - Configuration management
- `backend.app.services.ChannelScraperService` - Channel scraping
- `backend.app.services.NewsOutlineService` - Outline generation
- `backend.app.services.NewsArticleService` - Article generation
- `backend.app.services.WorkflowService` - Research workflow (to be adapted)
- `backend.app.services.ScrapingService` - Content scraping
- `research.phases.StreamingSummarizationManager` - Phase 0 summarization

### No New Dependencies Required
All necessary dependencies are already available in the project.

---

## Error Handling

### Common Error Scenarios

1. **Channel Scraping Failure**
   - Error: No channels found or scraping failed
   - Handling: Log error, return error status, optionally continue with manual links

2. **Content Scraping Failure**
   - Error: Some links fail to scrape
   - Handling: Continue with successful scrapes, log failures, save partial results

3. **Phase 0 Summarization Failure**
   - Error: Summarization fails for some items
   - Handling: Continue with successfully summarized items, log failures

4. **Outline Generation Failure**
   - Error: No Phase 0 files found or AI generation fails
   - Handling: Return error, allow manual retry

5. **Article Generation Failure**
   - Error: Outline not found or AI generation fails
   - Handling: Return error, allow manual retry

6. **Session Directory Errors**
   - Error: Cannot create directories or write files
   - Handling: Check permissions, return error with actionable message

7. **Configuration Errors**
   - Error: Missing required config values
   - Handling: Use sensible defaults, log warnings

---

## Logging

### Log Points

```python
logger.info(f"Creating workflow session: {session_id}")
logger.info(f"Session date range: {start_date} to {end_date}")
logger.info(f"Step 1: Channel scraping started for session {session_id}")
logger.info(f"Step 1: Channel scraping completed - {total_videos} videos found")
logger.info(f"Step 2: Content scraping started - {total_links} links to process")
logger.info(f"Step 2: Phase 0 summarization completed - {completed_count}/{total_links}")
logger.info(f"Step 3: Outline generation started for batch {batch_id}")
logger.info(f"Step 3: Outline generation completed - outline_id: {outline_id}")
logger.info(f"Step 4: Article generation started for outline {outline_id}")
logger.info(f"Step 4: Article generation completed - article_id: {article_id}")
logger.info(f"Workflow completed for session {session_id}")
logger.error(f"Workflow step failed: {step_name} - {error}")
logger.warning(f"Partial results saved for session {session_id} - step: {current_step}")
```

---

## Future Enhancements (Out of Scope)

These are potential future improvements but not part of the initial implementation:

1. **Parallel Step Execution**: Run multiple steps in parallel where possible
2. **Workflow Resume**: Resume interrupted workflows from last successful step
3. **Workflow Templates**: Pre-configured workflow templates for different use cases
4. **Scheduled Workflows**: Automatically run workflows on schedule (daily, weekly)
5. **Multi-Article Generation**: Generate multiple articles from one outline or session
6. **Workflow Versioning**: Track different versions of workflow configurations
7. **Progress WebSocket Updates**: Real-time progress updates via WebSocket
8. **Workflow Visualization**: Visual representation of workflow execution
9. **Batch Processing**: Process multiple date ranges in one workflow
10. **Custom Step Hooks**: Allow custom steps to be inserted into workflow

---

## Testing Strategy

### Unit Tests

```python
# tests/test_news_summary_workflow_service.py

def test_create_session():
    """Test session creation."""
    pass

def test_step_channel_scraping():
    """Test channel scraping step."""
    pass

def test_step_content_scraping_and_phase0():
    """Test content scraping and Phase 0 step."""
    pass

def test_step_outline_generation():
    """Test outline generation step."""
    pass

def test_step_article_generation():
    """Test article generation step."""
    pass

def test_run_workflow():
    """Test complete workflow execution."""
    pass

def test_session_status():
    """Test session status retrieval."""
    pass
```

### Integration Tests

```python
# tests/test_news_workflow_api.py

def test_create_workflow_session_endpoint():
    """Test API endpoint for creating workflow session."""
    pass

def test_run_workflow_endpoint():
    """Test API endpoint for running workflow."""
    pass

def test_get_workflow_status_endpoint():
    """Test API endpoint for getting workflow status."""
    pass

def test_list_workflow_sessions_endpoint():
    """Test API endpoint for listing sessions."""
    pass
```

### Manual Testing Steps

1. **Create Test Session**
   - POST to `/api/news/workflow/sessions` with date range
   - Verify session_id returned
   - Verify session directory created

2. **Run Complete Workflow**
   - POST to `/api/news/workflow/sessions/{session_id}/run`
   - Monitor logs for each step
   - Verify files created in session directory

3. **Check Session Status**
   - GET `/api/news/workflow/sessions/{session_id}/status`
   - Verify status and current_step

4. **Verify Artifacts**
   - GET `/api/news/workflow/sessions/{session_id}/artifacts`
   - Verify all expected files exist
   - Check file contents

---

## Notes

1. **Directory Separation**: News workflow uses separate directories from research workflow to avoid conflicts. Research artifacts stay in `data/research/batches`, news workflow artifacts go to `data/news/sessions`.

2. **Service Reuse**: The workflow service reuses existing services (ChannelScraperService, NewsOutlineService, NewsArticleService) but wraps them with session-specific paths and metadata.

3. **Configuration-Driven**: All paths, model settings, and prompt paths are configurable via `config.yaml` to maintain flexibility.

4. **Session Isolation**: Each workflow session has its own directory, ensuring isolation and easy cleanup.

5. **Error Resilience**: The workflow is designed to continue even if some steps fail, saving partial results for debugging and recovery.

6. **Metadata Tracking**: Comprehensive session metadata tracks the entire workflow execution, making it easy to debug and understand what happened.

7. **Future Frontend Integration**: The API is designed to be frontend-friendly, with clear status reporting and artifact access endpoints.

---

## Approval Checklist

Before implementation begins, confirm:

- [ ] Plan document created
- [ ] Architecture reviewed
- [ ] Configuration structure approved
- [ ] Directory structure confirmed
- [ ] Workflow adaptation strategy approved
- [ ] API endpoints approved
- [ ] Error handling strategy approved
- [ ] Session management approach confirmed

---

**Next Steps**: Once this plan is approved, proceed with implementation following the phases outlined above.

