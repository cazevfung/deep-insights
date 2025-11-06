# Interactive Retrieval-Augmented Research Plan

## Overview

This document analyzes the feasibility and implementation plan for an **interactive retrieval-augmented research method** where Qwen can dynamically request specific content from transcripts/articles during analysis, enabling a back-and-forth dialogue to access deeper context without sending everything upfront.

## Current State Analysis

### Current Flow

1. **Phase 2**: Creates research plan with steps
2. **Phase 3 Execution**:
   - For each step, prepares a data chunk (possibly truncated to 50K chars)
   - Sends entire chunk to Qwen in single API call
   - Qwen returns findings as JSON
   - Finds saved to scratchpad
   - Move to next step

### Current Limitations

1. **Content Truncation**: Transcripts truncated from 162K→50K chars (losing 69%) or 291K→50K (losing 83%)
2. **Static Context**: All context sent upfront, no way to get more details if needed
3. **Single Shot Analysis**: One request per step, no iterative refinement
4. **No Targeted Retrieval**: Can't request specific sections, topics, or keywords
5. **Sequential Chunking Limitation**: Even with sequential chunks, each chunk is independent - can't dynamically expand a previous chunk

### Data Structure

Currently available:
- **Transcripts**: Simple string content, no indexing
- **Metadata**: link_id, source, title, author, word_count
- **Comments**: Array of comment objects/strings
- **Chunking Info**: For sequential chunks, has `chunk_info` with `start_word`, `end_word`, `chunk_index`

**Missing for Retrieval**:
- No word-level indexing (can't say "words 5000-7000")
- No semantic indexing or embeddings
- No topic segmentation
- No keyword indices
- No timestamp mapping (for video transcripts)

---

## Proposed Interactive Retrieval System

### Core Concept

Enable Qwen to request specific content during analysis through a multi-turn conversation pattern:

```
[Initial Request] → Qwen analyzes provided context
                 → Qwen identifies what additional info needed
                 → Qwen requests: "I need transcript section about X" or "Show me comments mentioning Y"
[Retrieval]      → Python retrieves requested content
                 → Python provides additional context
[Follow-up]      → Qwen continues analysis with new context
                 → Can request more if needed OR finalize findings
```

### Architecture Options

#### Option 1: Request-Response Pattern Within Step (RECOMMENDED)

**How it works**:
- Modify `_execute_step()` to support multi-turn within a single step
- Qwen's response can include a `requests` field for additional data
- Python retrieves requested content and appends to conversation
- Continue until Qwen returns final findings (with empty `requests`)

**Implementation**:
```python
def _execute_step_iterative(self, step_id, goal, initial_data_chunk, ...):
    """Execute step with iterative retrieval capability."""
    messages = [initial_prompt_with_data]
    max_iterations = 5  # Prevent infinite loops
    
    for iteration in range(max_iterations):
        # Call Qwen
        response = self.client.stream_completion(messages)
        parsed = self._parse_response(response)
        
        # Check if Qwen needs more data
        if parsed.get("requests"):
            # Retrieve requested content
            retrieved_content = self._handle_retrieval_requests(
                parsed["requests"], 
                batch_data
            )
            # Append retrieval results to conversation
            messages.append({
                "role": "assistant",
                "content": response  # Qwen's analysis so far
            })
            messages.append({
                "role": "user", 
                "content": f"**请求的数据**:\n{retrieved_content}\n\n请继续分析..."
            })
        else:
            # Qwen has final findings
            return parsed
```

**Qwen Response Schema**:
```json
{
  "step_id": 1,
  "findings": {...},
  "requests": [  // Optional: if needs more data
    {
      "type": "transcript_section",
      "source_link_id": "yt_demo1",
      "query": "discussion about extraction mechanics",
      "method": "semantic_search"  // or "keyword", "word_range"
    },
    {
      "type": "comments",
      "source_link_id": "yt_demo1", 
      "keywords": ["frustration", "unfair"],
      "limit": 10
    }
  ],
  "analysis_status": "in_progress" | "complete"
}
```

**Advantages**:
- ✅ Enables targeted retrieval only when needed
- ✅ Reduces total token usage (only request what's needed)
- ✅ Allows Qwen to refine questions based on initial analysis
- ✅ Maintains step boundaries (one step can have multiple turns)

**Challenges**:
- Complexity: Need to parse and handle requests
- Cost: Multiple API calls per step (but more targeted)
- Request parsing: Qwen needs to format requests correctly

---

#### Option 2: Two-Phase Per Step (Initial Analysis + Deep Dive)

**How it works**:
- First call: Qwen analyzes provided chunk, identifies what's missing
- Second call: Python retrieves requested sections, sends to Qwen for final analysis

**Implementation**:
```python
def _execute_step(self, ...):
    # Phase 1: Initial analysis
    response1 = self._stream_with_callback(initial_messages)
    parsed1 = self._parse_response(response1)
    
    # Check if Qwen identified gaps
    if parsed1.get("missing_context"):
        # Phase 2: Retrieve and analyze
        retrieved = self._retrieve_content(parsed1["missing_context"], batch_data)
        followup_messages = [
            ...initial_messages,
            {"role": "assistant", "content": response1},
            {"role": "user", "content": f"Additional context:\n{retrieved}\n\nPlease finalize analysis."}
        ]
        response2 = self._stream_with_callback(followup_messages)
        return self._parse_response(response2)
    else:
        return parsed1
```

**Qwen Response Schema (Phase 1)**:
```json
{
  "step_id": 1,
  "initial_findings": {...},
  "missing_context": [
    {
      "type": "transcript",
      "source": "yt_demo1",
      "reason": "Need more details about weapon customization system",
      "search_hint": "gunsmith, customization, attachments"
    }
  ],
  "confidence": 0.7  // Lower confidence indicates need for more context
}
```

**Advantages**:
- ✅ Simpler than multi-turn (only 2 calls max per step)
- ✅ Clear separation: analysis → retrieval → finalization
- ✅ Easier to implement and debug

**Disadvantages**:
- ❌ Only one retrieval round per step
- ❌ Less flexible than true multi-turn

---

#### Option 3: Pre-Indexed Content Catalog

**How it works**:
- Before sending data, create an index/catalog of available content
- Send catalog summary to Qwen instead of full content
- Qwen requests specific items from catalog by ID/reference
- Python retrieves and sends requested items

**Implementation**:
```python
def _prepare_content_catalog(self, batch_data):
    """Create searchable index of content."""
    catalog = []
    for link_id, data in batch_data.items():
        transcript = data.get("transcript", "")
        # Split into semantic chunks (e.g., every 1000 words)
        chunks = self._chunk_transcript_semantically(transcript)
        for i, chunk in enumerate(chunks):
            catalog.append({
                "id": f"{link_id}_transcript_{i}",
                "source": link_id,
                "type": "transcript",
                "summary": self._summarize_chunk(chunk),  # Brief summary
                "word_range": (chunk.start, chunk.end),
                "keywords": self._extract_keywords(chunk)
            })
    return catalog

def _execute_step_with_catalog(self, step_id, goal, catalog, ...):
    """Send catalog, let Qwen request content."""
    initial_message = f"""
Available content catalog:
{catalog_summary}

Goal: {goal}

Please review the catalog and request the specific content sections you need.
"""
    # ... Qwen requests content → retrieve → continue
```

**Advantages**:
- ✅ Very efficient (only send summaries initially)
- ✅ Qwen sees full picture of available content
- ✅ Can implement smart pre-filtering

**Disadvantages**:
- ❌ Requires building indexing system
- ❌ More complex infrastructure
- ❌ Catalog creation adds preprocessing time

---

## Retrieval Methods to Implement

### Method 1: Word Range Retrieval

**Use Case**: Qwen says "I need words 5000-7000 from transcript yt_demo1"

**Implementation**:
```python
def retrieve_by_word_range(self, link_id: str, start_word: int, end_word: int, batch_data: Dict) -> str:
    """Retrieve specific word range from transcript."""
    data = batch_data.get(link_id)
    if not data:
        return f"Error: link_id {link_id} not found"
    
    transcript = data.get("transcript", "")
    words = transcript.split()
    
    if start_word < 0 or end_word > len(words):
        return f"Error: Range {start_word}-{end_word} out of bounds (0-{len(words)})"
    
    selected_words = words[start_word:end_word]
    return " ".join(selected_words)
```

**When to Use**: Qwen explicitly requests specific range, or when Qwen references "the section starting with X"

---

### Method 2: Keyword Search

**Use Case**: Qwen says "Show me parts mentioning 'extraction mechanics' or 'loot system'"

**Implementation**:
```python
def retrieve_by_keywords(self, link_id: str, keywords: List[str], batch_data: Dict, context_window: int = 500) -> str:
    """Retrieve sections containing keywords with context."""
    data = batch_data.get(link_id)
    transcript = data.get("transcript", "")
    words = transcript.split()
    
    matches = []
    for i, word in enumerate(words):
        # Check if any keyword appears near this word
        window_start = max(0, i - context_window)
        window_end = min(len(words), i + context_window)
        window_text = " ".join(words[window_start:window_end]).lower()
        
        if any(kw.lower() in window_text for kw in keywords):
            matches.append((window_start, window_end))
    
    # Merge overlapping matches
    merged = self._merge_ranges(matches)
    
    # Extract and return text
    result_parts = []
    for start, end in merged:
        result_parts.append(f"[Words {start}-{end}]:\n" + " ".join(words[start:end]))
    
    return "\n\n".join(result_parts)
```

**When to Use**: Qwen needs content about specific topics mentioned in initial context

---

### Method 3: Semantic Search (Advanced)

**Use Case**: Qwen says "I need content similar to 'weapon customization discussion' or related to that topic"

**Implementation** (requires embeddings):
```python
def retrieve_by_semantic_similarity(self, link_id: str, query: str, batch_data: Dict, top_k: int = 3):
    """Retrieve semantically similar sections using embeddings."""
    # Would require:
    # 1. Generate embeddings for transcript chunks
    # 2. Generate embedding for query
    # 3. Find top-k similar chunks
    # 4. Return matched content
    
    # Could use:
    # - Sentence transformers (e.g., all-MiniLM-L6-v2)
    # - OpenAI embeddings API
    # - Qwen's embedding capabilities (if available)
    pass
```

**When to Use**: Qwen needs content but doesn't know exact keywords

**Trade-offs**:
- More accurate than keyword search
- Requires embedding generation (cost/time)
- More complex implementation

---

### Method 4: Comment Filtering

**Use Case**: Qwen says "Show me comments that mention frustration or unfair mechanics"

**Implementation**:
```python
def retrieve_matching_comments(self, link_id: str, keywords: List[str], batch_data: Dict, limit: int = 10):
    """Filter comments by keywords."""
    data = batch_data.get(link_id)
    comments = data.get("comments", [])
    
    matches = []
    for comment in comments:
        content = comment.get("content", "") if isinstance(comment, dict) else str(comment)
        content_lower = content.lower()
        
        if any(kw.lower() in content_lower for kw in keywords):
            matches.append(comment)
            if len(matches) >= limit:
                break
    
    return self._format_comments(matches)
```

---

## Request Format Specifications

### Qwen Request Schema

```json
{
  "type": "retrieval_request",
  "requests": [
    {
      "id": "req_1",
      "content_type": "transcript" | "comments" | "metadata",
      "source_link_id": "yt_demo1",
      "method": "word_range" | "keyword" | "semantic" | "all",
      "parameters": {
        // For word_range:
        "start_word": 5000,
        "end_word": 7000,
        
        // For keyword:
        "keywords": ["extraction", "loot"],
        "context_window": 500,
        
        // For semantic:
        "query": "weapon customization discussion",
        "top_k": 3,
        
        // For comments:
        "filter_keywords": ["frustration"],
        "limit": 10,
        "sort_by": "relevance" | "likes" | "replies"
      },
      "reason": "Need more details about extraction mechanics to support analysis"
    }
  ]
}
```

---

## Implementation Plan

### Phase 1: Basic Retrieval Infrastructure (Foundation)

**Components**:
1. **Retrieval Handler Class** (`research/retrieval_handler.py`)
   - Methods for each retrieval type (word_range, keyword, comments)
   - Validation and error handling
   - Content formatting

2. **Request Parser** (within `phase3_execute.py`)
   - Parse Qwen's retrieval requests from response
   - Validate request format
   - Route to appropriate retrieval method

3. **Modified Step Execution**
   - Detect if Qwen needs more data
   - Handle retrieval → append to conversation → continue

**Files to Create/Modify**:
- `research/retrieval_handler.py` (NEW)
- `research/phases/phase3_execute.py` (MODIFY: add iterative execution)
- `research/prompts/phase3_execute/instructions.md` (UPDATE: explain retrieval capability)

**Timeline**: 4-6 hours

---

### Phase 2: Enhanced Retrieval with Catalog (Optional Enhancement)

**Components**:
1. **Content Indexer** (`research/content_indexer.py`)
   - Build searchable catalog of available content
   - Generate summaries for each chunk
   - Extract keywords/metadata

2. **Catalog-Aware Step Execution**
   - Send catalog summary to Qwen
   - Handle catalog-based requests

**Files**:
- `research/content_indexer.py` (NEW)
- `research/phases/phase3_execute.py` (UPDATE: catalog mode)

**Timeline**: 6-8 hours

---

### Phase 3: Semantic Search (Advanced)

**Components**:
1. **Embedding Generator** (optional, can use OpenAI/Qwen if available)
2. **Semantic Search Handler**
   - Generate embeddings for chunks
   - Query similarity search

**Timeline**: 8-12 hours (if using external embedding API)

---

## Prompt Engineering Requirements

### Update Phase 3 Instructions

Add section explaining retrieval capability:

```markdown
**动态内容检索能力：**

如果你在分析中发现需要更多信息，可以请求获取特定的内容：

1. **转录本片段**：如果你需要某个具体的转录本部分
   - 使用 `word_range` 方法：指定起始和结束单词位置
   - 使用 `keyword` 方法：搜索包含特定关键词的部分
   - 使用 `semantic` 方法：查找语义相似的内容（如果可用）

2. **评论筛选**：如果需要特定的评论
   - 使用 `keyword` 过滤：筛选包含特定关键词的评论
   - 可以指定排序方式：按相关性、点赞数等

3. **如何在响应中请求：**
   在你的 JSON 响应中添加 `requests` 字段：
   
   ```json
   {
     "step_id": 1,
     "findings": {...},
     "requests": [
       {
         "content_type": "transcript",
         "source_link_id": "yt_demo1",
         "method": "keyword",
         "parameters": {
           "keywords": ["weapon customization"],
           "context_window": 500
         },
         "reason": "Need more details about weapon system"
       }
     ],
     "analysis_status": "in_progress"
   }
   ```

4. **分析状态：**
   - `"analysis_status": "in_progress"` - 需要更多数据，将继续分析
   - `"analysis_status": "complete"` - 分析完成，不需要更多数据（或没有 `requests` 字段）

**重要**：
- 只在真正需要更多信息时请求，避免不必要的检索
- 明确说明请求的原因，以便系统理解你的意图
- 请求成功后，系统会提供额外的上下文，你可以基于新信息继续分析
```

---

## Benefits and Trade-offs

### Benefits ✅

1. **Context Preservation**: No more truncation - retrieve exactly what's needed when needed
2. **Efficiency**: Only retrieve relevant sections, not entire transcripts
3. **Flexibility**: Qwen can adapt questions based on initial analysis
4. **Targeted Analysis**: Focus on specific sections without noise
5. **Reduced Token Usage**: Potentially lower total tokens (targeted retrieval vs. sending everything)
6. **Better Findings**: More complete analysis with access to full content

### Trade-offs ⚠️

1. **Complexity**: More complex code, more potential failure points
2. **API Calls**: Multiple calls per step (but could be more efficient overall)
3. **Latency**: Multi-turn conversation takes longer than single call
4. **Qwen Prompting**: Need to train Qwen to use retrieval correctly
5. **Request Parsing**: Risk of malformed requests from Qwen
6. **Cost**: Could increase if Qwen makes many requests, but could decrease if more targeted

### Cost Analysis

**Current Approach** (with 50K truncation):
- Step 1: Send 50K chars + prompt → Analyze → Done
- Lost 112K chars (69% of content never analyzed)

**Interactive Approach**:
- Step 1: Send 10K summary → Qwen analyzes → Requests 30K relevant section → Finalize
- Total sent: ~40K chars, but 100% relevant content analyzed
- Multiple API calls, but potentially fewer total tokens if retrieval is targeted

**Break-even Point**: If retrieval allows analyzing full content with similar total tokens as truncated version, wins.

---

## Risk Mitigation

### Risk 1: Qwen Makes Too Many Requests
**Mitigation**: 
- Limit iterations per step (max 3-5 turns)
- Add cost tracking per step
- Fallback to static chunking if too many requests

### Risk 2: Malformed Requests
**Mitigation**:
- Robust parsing with fallbacks
- Validation layer before retrieval
- Default to keyword search if unclear
- Log warnings for unparseable requests

### Risk 3: Infinite Loops
**Mitigation**:
- Hard iteration limit per step
- Detect repetitive requests
- Force completion after max iterations

### Risk 4: Qwen Doesn't Use Retrieval
**Mitigation**:
- Clear prompting explaining when to use
- Examples in prompt showing retrieval usage
- Monitor and adjust prompts if Qwen rarely requests

---

## Testing Strategy

1. **Unit Tests**: Retrieval methods with various inputs
2. **Integration Tests**: Full step execution with retrieval
3. **Validation Tests**: Malformed request handling
4. **Cost Tracking**: Compare token usage vs. current approach
5. **Quality Tests**: Compare findings quality with vs. without retrieval

---

## Recommended Approach

### Start with Option 1 (Request-Response Pattern) - Phase 1 Only

**Rationale**:
- Balanced complexity vs. benefits
- Enables full content access
- Can be incrementally enhanced
- Clear path to Option 2 if needed

**Minimum Viable Implementation**:
1. Word range retrieval (simplest)
2. Keyword search (moderate complexity)
3. Two-turn per step (initial analysis → retrieval → finalization)
4. Robust error handling and fallbacks

**Later Enhancements**:
- Semantic search (if beneficial)
- Content catalog (if needed for efficiency)
- Multi-turn within step (if Qwen benefits from multiple retrievals)

---

## Success Metrics

1. **Context Preservation**: % of transcript content analyzed (target: >95%)
2. **Efficiency**: Total tokens used per step (compare to current)
3. **Request Accuracy**: % of requests successfully fulfilled (target: >90%)
4. **Findings Quality**: Compare depth/completeness of findings with vs. without retrieval
5. **User Satisfaction**: Quality of final article (subjective, but measurable via comparison)

---

## Questions to Answer Before Implementation

1. **Should retrieval be opt-in or always-on per step?**
   - Opt-in: Step explicitly enables retrieval mode
   - Always-on: Every step can request if needed
   - **Recommendation**: Always-on, but step can disable if not needed

2. **How many iterations per step?**
   - 2 (analysis → retrieval → done)?
   - 3-5 (multiple retrievals possible)?
   - **Recommendation**: Max 3, default 2 (if retrieval needed)

3. **Should we cache retrieved content?**
   - Yes: If same section requested multiple times
   - **Recommendation**: Yes, per step session

4. **Should Phase 2 planning account for retrieval?**
   - Yes: Can plan steps expecting retrieval to be used
   - No: Keep planning static, enable retrieval at execution time
   - **Recommendation**: No (for now), enable at execution time for flexibility

5. **Backward compatibility?**
   - Should old plans (without retrieval) still work?
   - **Recommendation**: Yes, retrieval is optional enhancement

---

## Next Steps

1. ✅ **Analysis Complete** - This document
2. ⏳ **Review & Confirm Plan** - Stakeholder review
3. ⏳ **Implement Phase 1** - Basic retrieval infrastructure
4. ⏳ **Test & Validate** - Compare with current approach
5. ⏳ **Iterate** - Add enhancements based on results

