# Key Info Markers Integration Plan: Phase 1-3
## Comprehensive Strategy for Marker-Based Context Provision and Full Content Retrieval

## Problem Statement

**Current Issue**: The existing Phase 3 flow of sending truncated transcript/comments to Qwen doesn't work well with the new key info markers system:
- Qwen receives truncated data chunks (e.g., 15,000 chars max for comments, windowed transcripts)
- Qwen doesn't see what information is actually available in each content item
- Key info markers created in Phase 0 are not being utilized effectively
- Qwen can't make informed decisions about which content items to request because it doesn't see the marker overview
- Truncation wastes valuable data and prevents comprehensive research

**Root Cause**:
- Phase 3 sends initial truncated chunks instead of marker summaries
- Qwen is expected to work with incomplete information
- The retrieval system exists but Qwen doesn't know what's available to request
- No systematic way to provide markers to Qwen across all phases

## Solution Overview

**Core Principle**: **Always show markers, retrieve full content on demand**

1. **Markers First**: Always provide key info markers to Qwen in every phase (1-3) before any truncated content
2. **Informed Requests**: Qwen sees what's available via markers and can make intelligent requests for full content items
3. **No Truncation**: Never truncate content when Qwen requests it - provide full content items or structured chunks
4. **Multi-Round Retrieval**: Support multiple rounds of retrieval within context window limits, but without truncation
5. **Marker-Based Retrieval**: Qwen can request content by marker relevance, not just by keywords or word ranges

---

## Architecture: Marker Flow Across Phases

### Phase 0: Marker Generation (Already Implemented)
- Creates structured summaries with key_facts, key_opinions, key_datapoints for each content item
- Saves summaries in JSON files
- Summary structure per content item:
  ```json
  {
    "transcript_summary": {
      "key_facts": ["FACT: ...", ...],
      "key_opinions": ["OPINION: ...", ...],
      "key_datapoints": ["DATA: ...", ...],
      "topic_areas": [...],
      "word_count": 12345,
      "total_markers": 15
    },
    "comments_summary": {
      "key_facts_from_comments": [...],
      "key_opinions_from_comments": [...],
      "key_datapoints_from_comments": [...],
      "major_themes": [...],
      "sentiment_overview": "mostly_positive|mixed|mostly_negative",
      "top_engagement_markers": [...],
      "total_comments": 1000,
      "total_markers": 25
    }
  }
  ```

---

## Phase 1: Research Goal Discovery

### Current Flow
- Receives `data_abstract` (text samples from transcripts/comments)
- Generates research goal suggestions

### New Flow with Markers

#### Step 1.1: Prepare Marker Overview for Phase 1
**Location**: `research/phases/phase1_discover.py`

**Action**: Replace or augment `data_abstract` with **marker-based overview**

**Structure**:
```
**可用的内容项标记概览**

共 {num_items} 个内容项：

---
**内容项 1: {link_id}**
来源: {source} | 标题: {title}
字数: {word_count} | 评论数: {comment_count}

**转录摘要标记** ({total_markers} 个):
- 关键事实 ({len(key_facts)} 个):
  • FACT: 玩家留存率在赛季重置后下降了30%
  • FACT: 新排名系统影响了休闲玩家
  ...
  
- 关键观点 ({len(key_opinions)} 个):
  • OPINION: 新排名系统对休闲玩家不公平
  • OPINION: 赛季重置机制需要调整
  ...
  
- 关键数据点 ({len(key_datapoints)} 个):
  • DATA: 平均游戏时长从2.5小时增加到3.2小时
  • DATA: 日活跃用户从50万增长到65万
  ...

- 话题领域: {topic_areas}

**评论摘要标记** ({total_comments} 条评论):
- 关键事实 ({len(key_facts_from_comments)} 个):
  • FACT: 社区反馈表明新系统导致玩家流失
  ...
  
- 关键观点 ({len(key_opinions_from_comments)} 个):
  • OPINION: 大多数玩家认为更新过于激进
  ...
  
- 高参与度评论标记 ({len(top_engagement_markers)} 个):
  • High-engagement: 关于排名系统公平性的讨论（5000+ 点赞）
  ...
  
- 总体情感: {sentiment_overview}
- 主要讨论主题: {major_themes}

---
**内容项 2: {link_id}**
...
```

#### Step 1.2: Update Phase 1 Prompt
**Location**: `research/prompts/phase1_discover/instructions.md`

**Changes**:
- Replace `data_abstract` context variable with `marker_overview`
- Update prompt instructions to explain that markers represent available information
- Instruct Qwen to consider markers when generating research goals
- Emphasize that goals should leverage the rich information indicated by markers

**Prompt Section**:
```
**可用内容标记概览**
{marker_overview}

**任务**
基于上述标记概览，这些标记代表了所有可用内容项中的关键信息点。每个标记对应：
- 关键事实：具体的事实性陈述
- 关键观点：观点、论证、解释
- 关键数据点：统计数据、数字、指标

请分析这些标记，识别：
1. 哪些研究目标可以充分利用这些标记中体现的信息？
2. 哪些话题领域有足够的信息支持深入研究？
3. 哪些内容项的组合对特定研究目标最有价值？

基于标记概览生成研究目标建议。
```

#### Step 1.3: Data Flow
```
Phase 0 Output (batch_data with summaries)
    ↓
Phase 1: Format marker overview
    ↓
Qwen sees: Marker overview (not truncated content)
    ↓
Qwen generates: Research goals based on available markers
```

**Benefits**:
- Qwen sees complete overview of available information
- Research goals are informed by actual available data
- No truncated content in Phase 1
- Fast (markers are concise)

---

## Phase 2: Research Plan Generation

### Current Flow
- Receives selected goal and `data_abstract`
- Generates detailed research plan with steps

### New Flow with Markers

#### Step 2.1: Provide Marker Overview + Selected Goal Context
**Location**: `research/phases/phase2_plan.py`

**Action**: Provide marker overview + context about selected goal

**Structure**:
```
**选定的研究目标**
{selected_goal}

**相关内容的标记概览**

[Same marker overview format as Phase 1, but optionally filtered by relevance]

**标记与目标的相关性**
- 内容项 {link_id}: {relevance_score} 相关标记
  • 相关事实: FACT: X, FACT: Y
  • 相关观点: OPINION: Z
  • 相关数据: DATA: A
  ...
```

#### Step 2.2: Update Phase 2 Prompt
**Location**: `research/prompts/phase2_plan/instructions.md`

**Changes**:
- Include marker overview in context
- Instruct Qwen to create research plan steps that reference specific markers
- Each plan step should identify which content items (by link_id) and which markers are relevant
- Plan steps should specify what type of content retrieval is needed (transcript, comments, or both)

**Prompt Section**:
```
**任务**
基于选定的研究目标和标记概览，制定详细的研究计划。

**标记说明**
- 每个标记对应内容项中的具体信息点
- 你可以通过标记快速判断哪些内容项对每个研究步骤最有价值
- 在研究计划中，请明确指定：
  * 每个步骤需要哪些内容项 (link_id)
  * 需要哪些类型的标记信息 (facts/opinions/datapoints)
  * 是否需要完整的转录/评论内容，还是仅需标记已足够

**输出要求**
每个研究步骤应包含：
- step_id: 步骤编号
- goal: 步骤目标
- required_content_items: ["link_id1", "link_id2", ...]  # 需要的内容项
- required_data: "transcript" | "comments" | "transcript_with_comments"
- marker_relevance: ["FACT: X", "OPINION: Y", ...]  # 相关的标记（可选）
- retrieval_strategy: "markers_only" | "full_content" | "selective_by_markers"
```

#### Step 2.3: Data Flow
```
Phase 1 Output (selected goal)
    ↓
Phase 2: Format marker overview + goal context
    ↓
Qwen sees: Marker overview + selected goal
    ↓
Qwen generates: Research plan with marker-aware steps
    ↓
Plan includes: Which content items and markers each step needs
```

**Benefits**:
- Research plan is marker-aware from the start
- Each step knows which content items are relevant
- Clear retrieval strategy per step
- Avoids requesting irrelevant content

---

## Phase 3: Research Execution

### Current Flow (Problematic)
- Sends truncated data chunks to Qwen
- Qwen requests more context via keywords/word_ranges
- Limited visibility of available content

### New Flow with Markers

#### Step 3.1: Initial Context: Marker Overview + Step Goal
**Location**: `research/phases/phase3_execute.py`

**Action**: Instead of sending truncated content, send marker overview first

**For Each Step**:

**Initial Context Structure**:
```
**步骤 {step_id}: {goal}**

**相关内容的标记概览**

[Marker overview for content items relevant to this step, as specified in plan]

**已检索的完整内容**
[Initially empty - will be populated based on Qwen's requests]

**检索能力说明**
你可以通过以下方式请求更多内容：
1. 请求完整内容项: 指定 link_id 和内容类型 (transcript/comments/both)
2. 基于标记检索: 指定相关标记，系统会检索包含该标记的完整上下文
3. 按话题检索: 指定话题领域，系统会检索相关内容

请分析可用的标记，然后：
- 如果需要更多上下文来完成分析，请明确请求
- 如果标记已足够，直接进行分析
```

#### Step 3.2: Updated Request Format for Qwen
**Location**: `research/prompts/phase3_execute/instructions.md` and `output_schema.json`

**New Request Schema**:
```json
{
  "step_id": 1,
  "findings": {...},
  "insights": "...",
  "confidence": 0.8,
  "requests": [
    {
      "id": "req_1",
      "request_type": "full_content_item",
      "source_link_id": "link_id_1",
      "content_types": ["transcript", "comments"],
      "reason": "需要完整内容以深入分析标记 'FACT: 玩家留存率下降30%' 的相关证据链",
      "priority": "high"
    },
    {
      "id": "req_2",
      "request_type": "by_marker",
      "marker_text": "FACT: 玩家留存率在赛季重置后下降了30%",
      "source_link_id": "link_id_1",
      "content_type": "transcript",
      "context_window": 2000,
      "reason": "需要该事实标记的完整上下文以了解细节"
    },
    {
      "id": "req_3",
      "request_type": "by_topic",
      "topic": "排名系统",
      "source_link_ids": ["link_id_1", "link_id_2"],
      "content_types": ["transcript", "comments"],
      "limit_items": 2,
      "reason": "需要所有关于排名系统的讨论内容"
    },
    {
      "id": "req_4",
      "request_type": "selective_markers",
      "marker_types": ["key_facts", "key_datapoints"],
      "source_link_ids": ["link_id_1"],
      "content_type": "transcript",
      "reason": "仅需要事实和数据点标记的完整上下文"
    }
  ]
}
```

#### Step 3.3: Retrieval Handler Enhancements
**Location**: `research/retrieval_handler.py`

**New Methods**:

1. **`retrieve_full_content_item(link_id, content_types, batch_data)`**
   - Returns full, untruncated transcript and/or comments
   - No truncation - returns complete content
   - Format: Structured with clear sections

2. **`retrieve_by_marker(marker_text, link_id, content_type, context_window, batch_data)`**
   - Finds the marker in summary
   - Retrieves full context around that information point
   - Returns surrounding content (context_window words) plus full relevant sections

3. **`retrieve_by_topic(topic, source_link_ids, content_types, batch_data)`**
   - Filters content by topic areas
   - Returns full content items that match the topic
   - No truncation - full content

4. **`retrieve_by_marker_types(marker_types, link_id, content_type, batch_data)`**
   - Retrieves full context for specific types of markers (e.g., all facts)
   - Returns structured sections per marker

**Key Principle**: All retrieval methods return **full content**, not truncated chunks.

#### Step 3.4: Multi-Round Retrieval Without Truncation

**Flow**:
```
Turn 1:
  Qwen receives: Marker overview for step
  Qwen analyzes: Sees what's available via markers
  Qwen requests: Full content items based on marker relevance
  System retrieves: Full, untruncated content
  Qwen receives: Requested full content (may be multiple items)

Turn 2:
  Qwen analyzes: Full content from Turn 1
  Qwen requests: Additional content items if needed (based on new insights)
  System retrieves: Additional full content items
  Qwen receives: Additional full content

Turn N:
  Continue until Qwen completes analysis or context window limit

Context Window Management:
- Track total content sent to Qwen
- If approaching context window limit:
  * Don't truncate individual items
  * Instead: Prioritize requests, send most relevant items first
  * If still over limit: Ask Qwen to prioritize which items are most critical
  * Never truncate - always full content items
```

**Config Options**:
```yaml
research:
  retrieval:
    max_followups_per_step: 5  # Increased from 2
    max_content_items_per_turn: 3  # Limit items per retrieval turn
    context_window_limit: 200000  # Total chars across all turns
    prioritize_by_marker_relevance: true
    never_truncate_items: true  # New flag
```

#### Step 3.5: Updated Prompt Instructions
**Location**: `research/prompts/phase3_execute/instructions.md`

**Key Changes**:
```
**上下文提供策略**

初始提供：
- 标记概览（所有相关内容项的标记）
- 不提供截断的内容块

你的任务：
1. 首先分析标记概览，理解可用的信息
2. 识别哪些标记与当前步骤目标最相关
3. 基于标记相关性，请求完整的相关内容项

请求内容时：
- 可以请求完整的内容项（不会截断）
- 可以基于特定标记请求上下文
- 可以按话题检索相关内容
- 系统会提供完整内容，不会截断

如果上下文窗口有限：
- 系统会优先发送你请求的标记相关度最高的内容项
- 如果仍超限，系统会询问你的优先级
- 永远不会截断内容项 - 只有完整内容或完整内容项的子集

输出格式：
- 如果需要更多内容，在 `requests` 字段中明确指定
- 请求应基于标记的相关性
- 如果标记已足够，直接给出分析
```

#### Step 3.6: Data Flow
```
Phase 2 Output (research plan with marker-aware steps)
    ↓
Phase 3 Step Start:
    ↓
Send to Qwen: Marker overview for step (NOT truncated content)
    ↓
Qwen analyzes markers
    ↓
Qwen requests: Full content items based on marker relevance
    ↓
System retrieves: Full, untruncated content
    ↓
Send to Qwen: Requested full content
    ↓
Qwen analyzes: Full content
    ↓
[Optional Turn 2+]: Qwen requests more if needed
    ↓
Qwen completes: Analysis with full context
```

---

## Implementation Details

### 1. Marker Formatting Utilities
**Location**: `research/utils/marker_formatter.py` (new file)

**Functions**:
- `format_marker_overview(batch_data, link_ids=None) -> str`: Format markers for phases
- `format_markers_for_content_item(link_id, summary) -> str`: Format single item markers
- `filter_markers_by_relevance(summary, keywords) -> dict`: Filter markers by relevance
- `get_marker_relevance_score(marker, goal) -> float`: Score marker relevance to goal

### 2. Enhanced Retrieval Handler
**Location**: `research/retrieval_handler.py`

**New Methods** (as specified in 3.3):
- All methods return full content, structured clearly
- No truncation logic in retrieval methods

### 3. Phase 1 Updates
**File**: `research/phases/phase1_discover.py`

**Changes**:
- Replace `data_abstract` preparation with `marker_overview` preparation
- Use `marker_formatter.format_marker_overview()` instead of `create_abstract()`
- Update context variable name in prompt

### 4. Phase 2 Updates
**File**: `research/phases/phase2_plan.py`

**Changes**:
- Include marker overview in context
- Update prompt to reference markers
- Output schema includes marker references in plan steps

### 5. Phase 3 Updates
**File**: `research/phases/phase3_execute.py`

**Major Changes**:
- **Remove**: `_prepare_data_chunk()` with truncation logic
- **Add**: `_prepare_marker_overview_for_step()` - prepares marker overview
- **Update**: `_execute_step()` - sends markers first, then full content on request
- **Update**: `_handle_retrieval_request()` - support new request types
- **Update**: `_run_followups_with_retrieval()` - handle full content retrieval
- **Remove**: All truncation logic (MAX_COMMENTS_CHARS, etc.)

### 6. Prompt Updates
**Files**:
- `research/prompts/phase1_discover/instructions.md`
- `research/prompts/phase2_plan/instructions.md`
- `research/prompts/phase3_execute/instructions.md`
- `research/prompts/phase3_execute/output_schema.json`

**Changes**:
- Update to reference markers instead of abstract samples
- Update request schema to support new request types
- Emphasize marker-based retrieval

### 7. Configuration Updates
**File**: `config.yaml`

**New Settings**:
```yaml
research:
  summarization:
    # ... existing settings ...
  
  retrieval:
    # ... existing settings ...
    max_followups_per_step: 5  # Increased for multi-round retrieval
    max_content_items_per_turn: 3  # Limit concurrent items
    context_window_limit: 200000  # Total chars across all turns
    prioritize_by_marker_relevance: true
    never_truncate_items: true  # Enforce no truncation
    
  phases:
    use_marker_overview: true  # Enable marker-based flow
    marker_overview_max_items: 20  # Max items to show in overview
```

---

## Benefits

1. **Complete Information Visibility**: Qwen always sees what's available via markers
2. **Informed Requests**: Qwen can make intelligent requests based on marker relevance
3. **No Data Loss**: Full content items are retrieved, never truncated
4. **Efficient**: Markers are small but informative, reducing initial token usage
5. **Targeted Retrieval**: Only retrieve what's needed based on marker relevance
6. **Better Research Quality**: Qwen has complete context when needed

---

## Migration Strategy

### Phase 1: Core Infrastructure
1. Create `marker_formatter.py` utility
2. Enhance `retrieval_handler.py` with new methods
3. Update configuration

### Phase 2: Phase 1 & 2 Updates
4. Update Phase 1 to use marker overview
5. Update Phase 2 to include markers in planning
6. Update prompts for Phase 1 & 2

### Phase 3: Phase 3 Overhaul
7. Completely refactor Phase 3 to use marker-first approach
8. Remove all truncation logic
9. Implement new request types
10. Update Phase 3 prompts and schema

### Phase 4: Testing & Refinement
11. Test with various batch sizes
12. Verify context window management
13. Refine marker formatting and relevance scoring

---

## Success Criteria

1. ✅ Phase 1 receives marker overview instead of text samples
2. ✅ Phase 2 creates marker-aware research plans
3. ✅ Phase 3 sends marker overview first, retrieves full content on demand
4. ✅ No truncation of content items when requested
5. ✅ Qwen can request content by marker relevance
6. ✅ Multi-round retrieval works without truncation
7. ✅ Context window managed by prioritizing items, not truncating
8. ✅ All phases consistently use markers

---

## Open Questions / Decisions Needed

1. **Marker Filtering**: Should Phase 2/3 filter markers by relevance to goal, or always show all?
   - **Recommendation**: Show all markers, but highlight relevant ones

2. **Marker Count Limits**: Should we limit number of markers shown per item?
   - **Recommendation**: Show all markers (they're concise), but limit items in overview if too many

3. **Fallback Strategy**: What if markers are missing for some items?
   - **Recommendation**: Fall back to existing abstract method, log warning

4. **Context Window Strategy**: When approaching limit, how to prioritize?
   - **Recommendation**: Ask Qwen to prioritize, or use marker relevance scores

5. **Performance**: Will marker overview be too large for very large batches?
   - **Recommendation**: Limit overview to top N most relevant items per step

---

## Next Steps

1. Review and approve this plan
2. Create detailed implementation tasks
3. Implement Phase 1 (marker formatting utilities)
4. Implement Phase 2 (retrieval handler enhancements)
5. Implement Phase 3 (phase updates)
6. Test end-to-end flow
7. Refine based on testing





