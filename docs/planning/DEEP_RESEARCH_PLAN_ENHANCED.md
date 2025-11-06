# Deep Research Agent - Enhanced Plan with Streaming Support

## Overview

This enhanced plan extends the original 4-phase research workflow with **Qwen3-max streaming API (流式输出)** integration to provide real-time feedback during AI agent processing. The agent analyzes transcripts, articles, and comments from multiple sources (YouTube, Bilibili, Reddit, Articles) to perform deep research.

---

## Key Enhancements

### 1. **Streaming API Integration (流式输出)**
- Use Qwen3-max streaming API for all phases
- Real-time token-by-token output display
- Progress indicators and status updates
- User can see agent "thinking" in real-time

### 2. **Multi-Source Data Handling**
- Support YouTube, Bilibili, Reddit, and Article sources
- Handle different comment formats:
  - YouTube: Array of comment strings
  - Bilibili: Array of objects with `content` and `likes`
  - Reddit: Embedded in article content
- Unified data abstraction layer

### 3. **Batch-Based Research Sessions**
- Work with scraped data from `tests/results/run_{batch_id}/`
- Support multiple content items per research session
- Aggregate findings across multiple sources

---

## Data Structure Analysis

### Current Scraped Data Format

#### YouTube Transcript (e.g., `251029_150500_YT_yt_demo1_tsct.json`)
```json
{
  "success": true,
  "video_id": "NLPJ_8GTg6c",
  "url": "https://www.youtube.com/watch?v=NLPJ_8GTg6c",
  "content": "Full transcript text...",
  "title": "Video Title",
  "author": "Channel Name",
  "source": "YouTube",
  "word_count": 3721,
  "batch_id": "251029_150500",
  "link_id": "yt_demo1"
}
```

#### YouTube Comments (e.g., `251029_150500_YT_yt_demo1_cmts.json`)
```json
{
  "success": true,
  "video_id": "NLPJ_8GTg6c",
  "comments": ["Comment 1", "Comment 2", ...],
  "num_comments": 38,
  "batch_id": "251029_150500",
  "link_id": "yt_demo1"
}
```

#### Bilibili Comments (e.g., `251029_150500_BILI_bili_req1_cmt.json`)
```json
{
  "success": true,
  "bv_id": "BV18UxNzLE8K",
  "comments": [
    {
      "content": "评论内容",
      "likes": 10
    },
    ...
  ],
  "batch_id": "251029_150500",
  "link_id": "bili_req1"
}
```

#### Reddit/Article Content
```json
{
  "success": true,
  "url": "...",
  "content": "Full article/post text with embedded comments",
  "title": "Post Title",
  "source": "Reddit",
  "word_count": 4986,
  "batch_id": "251029_150500",
  "link_id": "rd_case1"
}
```

---

## Enhanced 4-Phase Workflow with Streaming

### **Phase 0: Data Loading & Preparation (Python Controller)**

**Goal:** Load and normalize data from scraped results

#### Step 0.1: Load Batch Data
```python
# Load all files from tests/results/run_{batch_id}/
# Group by link_id:
#   - transcript/content files: *_tsct.json, *_article.json
#   - comments files: *_cmts.json, *_cmt.json
# Create unified data structure per link_id
```

#### Step 0.2: Data Abstraction
**For each content item (video/article):**
1. Extract transcript/article content
2. Extract comments (format depends on source)
3. Create `data_abstract`:
   - First ~500-800 words from transcript/content
   - Random sample of 20-30 comments (or all if < 30)
   - Include metadata: title, author, source, word_count

#### Step 0.3: Multi-Source Aggregation
If multiple sources available for the same research topic:
- Combine abstracts from all sources
- Create source index mapping
- Prepare unified context for agent

---

### **Phase 1: Discover & Suggest (Streaming API Call #1)**

**Goal:** Generate research goal suggestions with real-time streaming feedback

#### Step 1: API Call - Generate Research Goals (Streaming)

**Python Controller Actions:**
1. Display status: "正在分析内容，生成研究目标..."
2. Initiate streaming API call to Qwen3-max
3. Stream tokens in real-time to user interface
4. Parse completed JSON response

**Streaming Prompt:**
```prompt
**System Role:**
你是一位专业的研究策略专家。你的任务是快速分析提供的资料摘要，并针对用户提出的研究主题，提出三个不同的、有洞察力的研究目标。

**提供的资料摘要:**
{{data_abstract}}

**可选的研究主题（如果用户未指定则省略）:**
{{user_topic}}

**任务:**
基于提供的资料摘要，生成三个不同的研究目标。目标应明确、可操作，最好以问题的形式呈现。你必须以JSON格式输出，包含一个键"suggested_goals"，每个目标包含"id"和"goal_text"。

**输出格式（必须是有效的JSON）:**
{
  "suggested_goals": [
    {"id": 1, "goal_text": "分析视频作者提出的核心论点是什么？"},
    {"id": 2, "goal_text": "观众对视频主要观点的反应如何？识别共鸣点和争议点。"},
    {"id": 3, "goal_text": "分析最受点赞的评论，了解哪些观点最能引起观众共鸣。"}
  ]
}
```

**User Interface (Streaming):**
```
[实时显示] 正在生成研究目标...

[流式输出] 我正在分析提供的资料内容...
[流式输出] 基于视频转录本和评论样本，我发现了几个有趣的研究方向...
[流式输出] 
{
  "suggested_goals": [
    {"id": 1, "goal_text": "..."
    ...
```

**Post-Processing:**
1. Parse JSON from completed stream
2. Display goals to user
3. Prompt user to select goal ID (1, 2, or 3, or custom)
4. Store `selected_goal` and `goal_id`

---

### **Phase 2: Plan (Streaming API Call #2)**

**Goal:** Create detailed execution plan with real-time visibility

#### Step 2: API Call - Create Detailed Plan (Streaming)

**Prompt:**
```prompt
**System Role:**
你是一位世界级的研究助手。你的任务是为特定的研究目标创建一个详细的、逐步的执行计划。你必须逐步思考，并以JSON格式响应。

**上下文:**
我拥有结构化的数据，包括：
- 转录本/文章内容（来自 {{sources}}）
- 评论数据（来自 {{comment_sources}}）
- 元数据（标题、作者、发布日期等）

用户选择的研究目标是："{{selected_goal}}"

**可用数据概览:**
- 转录本总字数: {{total_transcript_words}}
- 评论总数: {{total_comments}}
- 数据来源: {{source_list}}

**任务:**
基于选择的研究目标，创建一个逐步的研究计划。将目标分解为更小的、可管理的分析任务。对于每个步骤，指定：
- "step_id": 步骤编号
- "goal": 该步骤的具体目标描述
- "required_data": 需要的数据类型（'transcript', 'comments', 'metadata', 或 'previous_findings'）
- "chunk_strategy": 数据分块策略（'sequential', 'random_sample', 'semantic_chunks', 'all'）
- "estimated_tokens": 估计需要处理的token数量

**输出必须是JSON对象，包含键"research_plan":**
{
  "research_plan": [
    {
      "step_id": 1,
      "goal": "识别转录本中的主要话题和主题",
      "required_data": "transcript",
      "chunk_strategy": "sequential",
      "chunk_size": 2000,
      "estimated_tokens": 3000
    },
    {
      "step_id": 2,
      "goal": "根据步骤1识别的话题，对评论进行分类",
      "required_data": "comments",
      "chunk_strategy": "all",
      "estimated_tokens": 2000
    },
    {
      "step_id": 3,
      "goal": "综合发现，识别争议点",
      "required_data": "previous_findings",
      "chunk_strategy": "all",
      "estimated_tokens": 1500
    }
  ]
}
```

**User Interface (Streaming):**
```
[实时显示] 正在创建研究计划...

[流式输出] 分析研究目标：{{selected_goal}}
[流式输出] 我将把这个目标分解为几个关键步骤...
[流式输出] 
{
  "research_plan": [
    {
      "step_id": 1,
      "goal": "..."
    ...
```

**Post-Processing:**
1. Parse `research_plan` JSON
2. Display plan summary to user
3. Allow user to confirm or modify plan
4. Store plan for execution phase

---

### **Phase 3: Execute (Multiple Streaming API Calls)**

**Goal:** Execute plan with real-time progress feedback

#### Step 3: Execution Loop with Streaming

**Controller Actions:**
1. Initialize `scratchpad = {}` (stores all findings)
2. Initialize `progress_tracker = {}` (tracks execution status)
3. Display execution dashboard
4. For each step in `research_plan`:
   - Display step progress: `[Step 1/3] 正在执行：识别主要话题...`
   - Prepare data chunk based on `chunk_strategy`
   - Stream API call with progress updates
   - Parse response and update `scratchpad`
   - Update progress tracker

#### Data Chunking Strategies

**For 'transcript' data:**
- `sequential`: Split transcript into ~2000-word chunks, process in order
- `semantic_chunks`: Split by paragraphs/topics (if available)
- `all`: Send entire transcript (if within token limits)

**For 'comments' data:**
- `all`: Send all comments (if < 100)
- `random_sample`: Random sample of 50-100 comments
- `top_by_likes`: Top N comments by likes (for Bilibili)
- `sequential`: Process in batches of 50

**Streaming Prompt (Per Execution Step):**
```prompt
**System Role:**
你是一位数据分析专家。你的任务是执行特定的分析步骤，并以结构化的JSON格式返回结果。

**上下文和之前的发现（你的记忆）:**
到目前为止，我们收集了以下发现：
{{SCRATCHPAD_CONTENTS}}

**当前分析数据块:**
{{DATA_CHUNK}}

**元数据（如果相关）:**
- 来源: {{source}}
- 标题: {{title}}
- 作者: {{author}}

**任务:**
你的具体目标是："{{STEP_GOAL}}"

分析"当前分析数据块"以实现此目标，必要时使用"之前的发现"作为上下文。你的输出必须是一个JSON对象，直接表示此分析的结果。JSON结构应该清晰、层次化，便于后续综合。

**输出格式:**
{
  "step_id": {{step_id}},
  "findings": {
    // 结构化的发现内容，根据步骤目标定制
    // 例如：如果是主题识别，可能是 {"topics": [...], "keywords": [...]} 
    // 如果是评论分析，可能是 {"sentiment": {...}, "categories": [...]} 
  },
  "insights": "关键洞察的简要总结",
  "confidence": 0.0-1.0  // 对分析结果的置信度
}
```

**User Interface (During Execution):**
```
[实时显示] 
═══ 执行研究计划 ═══
进度: [████████░░] 67% (2/3 步骤完成)

[Step 1/3] ✓ 已完成：识别主要话题
[Step 2/3] → 进行中：分析评论情感...
  
[流式输出] 正在分析评论数据...
[流式输出] 我发现评论主要集中在以下几个主题：
[流式输出] 1. 游戏机制讨论 (45%)
[流式输出] 2. 社区反馈 (30%)
[流式输出] 3. 与其他游戏对比 (25%)
...

[Step 3/3] ⏳ 等待中：综合所有发现
```

**Scratchpad Structure:**
```python
scratchpad = {
  "step_1": {
    "step_id": 1,
    "goal": "识别主要话题",
    "findings": {...},
    "insights": "...",
    "confidence": 0.9,
    "timestamp": "2025-10-29T15:30:00Z"
  },
  "step_2": {
    ...
  },
  "metadata": {
    "total_steps": 3,
    "completed_steps": 2,
    "start_time": "...",
    "current_step_start": "..."
  }
}
```

---

### **Phase 4: Synthesize (Final Streaming API Call)**

**Goal:** Generate final report with streaming output

#### Step 4: Sent - Generate Final Report (Streaming)

**Prompt:**
```prompt
**System Role:**
你是一位专业的研究报告撰写专家。你的工作是将一系列结构化数据点综合成最终、连贯、书写良好的Markdown格式报告。

**原始用户目标:**
用户选择的研究目标是："{{selected_goal}}"

**结构化发现（你的完整笔记）:**
以下是分析的所有结构化发现：
{{FINAL_SCRATCHPAD_CONTENTS}}

**任务:**
使用所有提供的"结构化发现"，撰写一份综合报告，直接回答"原始用户目标"。报告应：
1. 以高级执行摘要开始
2. 详细阐述，包含证据
3. 从发现中引用直接内容（如适用）
4. 使用Markdown格式（标题、列表、引用等）
5. 结构清晰，便于阅读

**不要输出JSON，输出纯Markdown文本报告。**

**报告结构建议:**
# 研究报告：{{selected_goal}}

## 执行摘要
...

## 主要发现
...

## 详细分析
...

## 结论
...
```

**User Interface (Streaming Report Generation):**
```
[实时显示] 
═══ 生成最终报告 ═══

[流式输出] # 研究报告：{{selected_goal}}
[流式输出]
[流式输出] ## 执行摘要
[流式输出]
[流式输出] 基于对视频转录本和评论的深入分析...
[流式输出] 
[流式输出] ## 主要发现
[流式输出]
[流式输出] ### 1. 核心论点
[流式输出] 作者在视频中提出了三个主要论点...
...
```

**Post-Processing:**
1. Save complete Markdown report to file
2. Display report in user interface
3. Offer export options (PDF, DOCX, etc.)
4. Save research session metadata

---

## Technical Implementation Details

### Streaming API Integration

**Qwen3-max Streaming Client (Python) - Based on Official Documentation:**

```python
import os
from openai import OpenAI
from typing import Iterator, Dict, Any, List, Optional, Callable
import json
import re

class QwenStreamingClient:
    """
    Qwen3-max Streaming API Client
    
    Uses OpenAI-compatible SDK with DashScope endpoints.
    Protocol: Server-Sent Events (SSE)
    Documentation: https://help.aliyun.com/zh/model-studio/stream
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: str = "qwen-max"
    ):
        """
        Initialize Qwen streaming client.
        
        Args:
            api_key: API key (defaults to DASHSCOPE_API_KEY env var)
            base_url: Base URL for API (Beijing or Singapore region)
            model: Model name (qwen-max, qwen-plus, etc.)
        """
        # API key: from parameter, env var, or config
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided or set in DASHSCOPE_API_KEY/QWEN_API_KEY env var")
        
        self.base_url = base_url
        self.model = model
        
        # Initialize OpenAI client with DashScope endpoint
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # Token tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
    
    def stream_completion(
        self, 
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream_options: Optional[Dict] = None,
        callback: Optional[Callable[[str], None]] = None,
        enable_thinking: bool = False
    ) -> Iterator[str]:
        """
        Stream completion from Qwen API using SSE protocol.
        
        Args:
            messages: List of message dicts [{"role": "user", "content": "..."}]
            model: Model name (overrides default)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens (32K limit for qwen-max)
            stream_options: Optional stream options (e.g., {"include_usage": True})
            callback: Optional callback for each token chunk
            enable_thinking: Enable thinking mode (returns reasoning_content)
            
        Yields:
            String tokens from the stream
        """
        model = model or self.model
        stream_options = stream_options or {"include_usage": True}
        
        # Create completion request with streaming
        try:
            completion_params = {
                "model": model,
                "messages": messages,
                "stream": True,
                "temperature": temperature,
                "stream_options": stream_options
            }
            
            # Add max_tokens if specified (respect 32K limit)
            if max_tokens:
                completion_params["max_tokens"] = min(max_tokens, 32000)
            
            # Add thinking mode if enabled
            if enable_thinking:
                completion_params["extra_body"] = {"enable_thinking": True}
            
            # Stream the completion
            completion = self.client.chat.completions.create(**completion_params)
            
            # Process stream chunks
            for chunk in completion:
                # Handle usage information (last chunk)
                if hasattr(chunk, 'usage') and chunk.usage:
                    self.total_input_tokens = chunk.usage.prompt_tokens
                    self.total_output_tokens = chunk.usage.completion_tokens
                    continue
                
                # Extract content from chunk
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    
                    # Thinking mode: check reasoning_content first
                    if enable_thinking and hasattr(delta, 'reasoning_content'):
                        if delta.reasoning_content:
                            if callback:
                                callback(delta.reasoning_content)
                            # Note: We yield reasoning_content for display, but it's separate from main content
                            yield delta.reasoning_content
                    
                    # Regular content
                    if hasattr(delta, 'content') and delta.content:
                        if callback:
                            callback(delta.content)
                        yield delta.content
                        
        except Exception as e:
            raise Exception(f"Streaming API error: {str(e)}")
    
    def stream_and_collect(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> tuple[str, Dict]:
        """
        Stream completion and collect full response.
        
        Returns:
            (full_response, usage_info)
        """
        content_parts = []
        usage_info = {}
        
        for chunk in self.stream_completion(messages, **kwargs):
            content_parts.append(chunk)
        
        full_response = "".join(content_parts)
        usage_info = {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens
        }
        
        return full_response, usage_info
    
    def parse_json_from_stream(
        self, 
        stream: Iterator[str],
        max_wait_time: float = 60.0
    ) -> Dict[str, Any]:
        """
        Parse complete JSON from streaming output.
        
        Handles partial JSON during streaming by buffering until complete JSON detected.
        Attempts to find JSON object boundaries.
        
        Args:
            stream: Iterator of string chunks
            max_wait_time: Maximum time to wait for complete JSON (seconds)
            
        Returns:
            Parsed JSON dictionary
            
        Raises:
            ValueError: If valid JSON cannot be parsed
        """
        buffer = ""
        json_started = False
        brace_count = 0
        
        # Collect all chunks
        for chunk in stream:
            buffer += chunk
            
            # Try to find JSON boundaries
            # Look for first '{' as JSON start
            if not json_started and '{' in buffer:
                start_idx = buffer.index('{')
                buffer = buffer[start_idx:]
                json_started = True
                brace_count = 0
            
            # Count braces to detect complete JSON
            if json_started:
                for char in buffer:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                
                # Try parsing when braces are balanced
                if brace_count == 0:
                    try:
                        return json.loads(buffer)
                    except json.JSONDecodeError:
                        # Continue collecting if parsing fails
                        continue
        
        # Final attempt: try to extract JSON from buffer
        # Look for JSON object pattern
        json_match = re.search(r'\{.*\}', buffer, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Try parsing entire buffer
        try:
            return json.loads(buffer)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse JSON from stream. Buffer preview: {buffer[:200]}... Error: {str(e)}")
    
    def get_usage_info(self) -> Dict[str, int]:
        """Get current token usage information."""
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens
        }
```

### Data Loading Module

**Unified Data Loader:**
```python
class ResearchDataLoader:
    """Load and normalize scraped data from batch results."""
    
    def load_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Load all scraped files for a batch.
        
        Returns:
            {
                "link_id_1": {
                    "transcript": {...},  # or "article"
                    "comments": [...],
                    "metadata": {...}
                },
                ...
            }
        """
        pass
    
    def create_abstract(
        self, 
        data: Dict[str, Any],
        transcript_sample_words: int = 500,
        comment_sample_size: int = 30
    ) -> str:
        """Create data abstract for Phase 1."""
        pass
    
    def chunk_data(
        self,
        data: Dict[str, Any],
        strategy: str,
        chunk_size: int = 2000
    ) -> List[Dict[str, Any]]:
        """Chunk data based on strategy."""
        pass
```

### Progress Tracking

```python
class ProgressTracker:
    """Track execution progress with real-time updates."""
    
    def __init__(self, total_steps: int):
        self.total_steps = total_steps
        self.completed_steps = 0
        self.current_step = None
        self.status_callbacks = []
    
    def start_step(self, step_id: int, goal: str):
        """Mark step as started."""
        pass
    
    def complete_step(self, step_id: int, findings: Dict):
        """Mark step as completed."""
        pass
    
    def stream_update(self, token: str):
        """Update streaming progress."""
        pass
```

---

## User Interface Flow

### Console-Based (Initial Implementation)
```
╔══════════════════════════════════════════════╗
║         Deep Research Agent                  ║
╚══════════════════════════════════════════════╝

[1] 选择批次数据: tests/results/run_251029_150500/
[2] 加载数据... 完成 (7 个内容项)

═══ Phase 1: 生成研究目标 ═══
[流式输出显示区域]
正在分析内容...

═══ Phase 2: 创建研究计划 ═══
...

═══ Phase 3: 执行刚划 ═══
[进度条 + 流式输出]
...

═══ Phase 4: 生成报告 ═══
[流式报告输出]
...

[保存] 报告已保存到: research_report_20251029_153000.md
```

### Web-Based (Future Enhancement)
- Real-time WebSocket updates
- Interactive progress dashboard
- Live streaming text display
- Export/download options

---

## Error Handling & Edge Cases

### Streaming JSON Parsing
- Handle partial JSON during streaming
- Buffer tokens until complete JSON detected
- Validate JSON structure before proceeding
- Retry with adjusted prompt if JSON invalid

### Large Data Handling
- Implement token counting
- Split large chunks automatically
- Use summarization for very long content
- Cache intermediate results

### Multi-Source Data Mismatch
- Handle missing transcripts
- Handle missing comments
- Fallback strategies (e.g., use article content only)

---

## Configuration & Settings

### API Configuration
```yaml
qwen:
  # API Key: Can be set via environment variable DASHSCOPE_API_KEY or QWEN_API_KEY
  # Or directly configured here (less secure)
  api_key: "${DASHSCOPE_API_KEY}"  # or "${QWEN_API_KEY}"
  
  # Base URL: Region-specific
  # Beijing region (default):
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  # Singapore region:
  # base_url: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
  
  model: "qwen-max"  # or "qwen-plus", "qwen3-max", etc.
  streaming: true  # Always use streaming for better UX
  max_tokens: 32000  # Maximum token limit for qwen-max
  temperature: 0.7
  enable_thinking: false  # Set to true for reasoning models
```

**Environment Variable Setup:**
```bash
# Windows PowerShell
$env:DASHSCOPE_API_KEY="your-api-key-here"

# Windows CMD
set DASHSCOPE_API_KEY=your-api-key-here

# Linux/Mac
export DASHSCOPE_API_KEY="your-api-key-here"
```

**Note:** API key should be stored securely. Avoid committing keys to version control.

### Data Processing Settings
```yaml
research:
  transcript_sample_words: 500
  comment_sample_size: 30
  default_chunk_size: 2000
  max_tokens_per_call: 8000
  enable_caching: true
```

---

## Project Folder Structure

**All deep research agent code will be organized in a dedicated `research/` folder.**

See `docs/implementation/RESEARCH_FOLDER_STRUCTURE.md` for complete folder structure details.

**Quick Overview:**
```
research_tool/
├── research/                    # Deep Research Agent Module
│   ├── agent.py                 # Main orchestrator
│   ├── client.py                # QwenStreamingClient
│   ├── data_loader.py           # ResearchDataLoader
│   ├── progress_tracker.py      # ProgressTracker
│   ├── session.py               # Session management
│   ├── phases/                  # Phase implementations
│   │   ├── phase0_prepare.py
│   │   ├── phase1_discover.py
│   │   ├── phase2_plan.py
│   │   ├── phase3_execute.py
│   │   └── phase4_synthesize.py
│   └── ui/                      # UI components
│       ├── console_interface.py
│       └── formatters.py
├── tests/research/              # Tests for research agent
└── scripts/run_research.py      # CLI entry point
```

---

## Next Steps for Implementation

1. **Setup**: Create `research/` folder structure (see `RESEARCH_FOLDER_STRUCTURE.md`)
2. **Phase 0**: Implement data loading module (`research/data_loader.py`)
3. **Core Client**: Implement streaming API client (`research/client.py`)
4. **Phase 1**: Implement goal generation (`research/phases/phase1_discover.py`)
5. **Phase 2**: Implement planning (`research/phases/phase2_plan.py`)
6. **Phase 3**: Implement execution loop (`research/phases/phase3_execute.py`)
7. **Phase 4**: Implement report generation (`research/phases/phase4_synthesize.py`)
8. **Orchestrator**: Create main agent (`research/agent.py`)
9. **UI**: Create console interface (`research/ui/console_interface.py`)
10. **Testing**: Test with actual scraped data from `run_251029_150500`

---

## Notes

- All prompts are in Chinese to match UI language preference
- Streaming provides real-time feedback, making long-running operations feel responsive
- The scratchpad accumulates findings incrementally, allowing the agent to build context
- Multi-source support enables cross-platform research (YouTube + Bilibili comparison, etc.)



