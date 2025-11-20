# Content Detail Preservation Plan

## Problem Analysis

The article style is excellent, but content is truncated - important details from video transcripts are being lost.

### Root Causes Identified

#### 1. **Hard Character Limit on Data Chunks (CRITICAL)**
**Location**: `research/phases/phase3_execute.py:405`
```python
safe_data_chunk = data_chunk[:8000] if len(data_chunk) > 8000 else data_chunk
```

**Problem**: 
- Hard truncation at 8,000 characters regardless of chunk strategy
- Even with "all" strategy, transcripts are cut off
- Sequential chunks are also limited to 8K each
- No warning or logging when truncation occurs

**Impact**: 
- Large transcripts lose significant content
- Later parts of transcripts never analyzed
- Key quotes and examples from transcripts missing

#### 2. **Scratchpad Summary Format May Filter Details**
**Location**: `research/session.py:145-209`

**Current Format**:
- Only includes JSON dumps of findings
- Points of interest are counted, not detailed
- Full transcript quotes/context may not be preserved in structured findings

**Problem**:
- Phase 4 only sees summaries and structured data, not raw quotes/context
- Important nuanced details from transcripts might be lost in summarization

#### 3. **Phase 3 Instructions May Encourage Summarization**
**Location**: `research/prompts/phase3_execute/instructions.md`

**Current Instructions**: 
- Focus on extracting "points of interest" as structured data
- May encourage AI to summarize rather than preserve detailed quotes
- Emphasis on "key claims" may filter out supporting detail

#### 4. **Phase 4 Instructions Emphasize Brevity**
**Location**: `research/prompts/phase4_synthesize/instructions.md`

**Current Instructions**:
- "故事节奏：保持叙事节奏，避免冗长的分析段落"
- "段落长度：2-4句为宜，避免冗长段落"
- May cause AI to skip detailed examples/quotes in favor of brevity

#### 5. **Sequential Chunking Without Full Context**
**Location**: `research/phases/phase3_execute.py`

**Problem**:
- Sequential chunks processed independently
- Previous chunks summarized, not fully available
- Cross-chunk connections and context may be lost

---

## Proposed Solutions

### Solution 1: Increase/Remove Character Limit (HIGH IMPACT)

#### Option 1A: Increase Limit Based on API Capacity
- Current: 8,000 characters hard limit
- Proposed: Check API context window and increase accordingly
- For Qwen3-max: Context window is large (likely 128K+ tokens)
- **New limit**: 50,000 characters (conservative) or remove limit entirely for transcripts

#### Option 1B: Dynamic Limit Based on Content Type
- Transcripts: Higher limit (50K-100K chars) - they're the primary anchor
- Comments: Lower limit (10K-20K chars) - supplementary data
- Metadata: No limit needed

#### Implementation:
**File**: `research/phases/phase3_execute.py`

**Change**:
```python
# Current
safe_data_chunk = data_chunk[:8000] if len(data_chunk) > 8000 else data_chunk

# Proposed
def _safe_truncate_data_chunk(
    self, 
    data_chunk: str, 
    required_data: str,
    chunk_strategy: str
) -> str:
    """
    Truncate data chunk safely based on content type and strategy.
    
    Args:
        data_chunk: Full data chunk
        required_data: Type of data (transcript, comments, etc.)
        chunk_strategy: Chunking strategy used
        
    Returns:
        Safely truncated (or full) data chunk
    """
    # For transcript-based data, use higher limit
    if required_data in ["transcript", "transcript_with_comments"]:
        # Transcripts are primary anchor - allow much more
        MAX_TRANSCRIPT_CHARS = 50000  # Configurable
        if len(data_chunk) > MAX_TRANSCRIPT_CHARS:
            self.logger.warning(
                f"Transcript chunk truncated from {len(data_chunk)} to {MAX_TRANSCRIPT_CHARS} chars"
            )
            return data_chunk[:MAX_TRANSCRIPT_CHARS] + "\n\n[内容被截断，可能遗漏细节...]"
        return data_chunk
    
    # For comments-only, use moderate limit
    elif required_data == "comments":
        MAX_COMMENTS_CHARS = 15000
        if len(data_chunk) > MAX_COMMENTS_CHARS:
            return data_chunk[:MAX_COMMENTS_CHARS] + "\n\n[评论内容被截断...]"
        return data_chunk
    
    # Default: keep current limit for edge cases
    return data_chunk[:8000] if len(data_chunk) > 8000 else data_chunk
```

**Pros**:
- Quick implementation
- Preserves much more transcript content
- Configurable limits

**Cons**:
- Still has limits (but much higher)
- May increase API costs slightly
- Need to ensure API can handle larger context

#### Option 1C: Remove Limit Entirely with Overflow Protection
- Only truncate if truly necessary (approaching API limits)
- Use token counting instead of character counting
- Let API handle context limits naturally

---

### Solution 2: Emphasize Clean Quote Extraction in Phase 3 (MEDIUM IMPACT)

#### Problem:
Current Phase 3 instructions focus on extracting "key claims" which may lead to summarization rather than preserving specific, quotable statements.

#### Proposed Enhancement:
**File**: `research/prompts/phase3_execute/instructions.md`

**Add Section**:
```
**引述和具体例子的提取要求：**

在提取兴趣点时，请特别注意：

1. **可引用语句 (Quotable Statements)**：
   - 提取清晰的、可引用的原话（但可以稍作清理，去除"嗯"、"那个"等填充词）
   - 记录完整的句子，不要只记片段
   - 包含说话者的立场或情境上下文
   - 重点：提取表达清晰、有力量的原话

2. **具体例子和细节 (Specific Details)**：
   - 记录具体的数据、统计数字、时间、地点等
   - 保留生动的描述和场景细节
   - 包括能让论点更具体、更可信的细节
   - 不要过度概括，保留足够的特异性

3. **上下文信息 (Context)**：
   - 记录支撑论点的重要背景
   - 说明引述出现的场景或情境

**注意**：引述应该是清理过的、可读的原文（去除口语填充词和不必要的重复），但保持原意和原话的风格。
```

---

### Solution 3: Emphasize Detail Preservation in Phase 4 (MEDIUM-HIGH IMPACT)

#### Update Phase 4 Instructions:

**File**: `research/prompts/phase4_synthesize/instructions.md`

**Current Problem**:
```
- "故事节奏：保持叙事节奏，避免冗长的分析段落"
- "段落长度：2-4句为宜，避免冗长段落"
```

**These may cause AI to skip details in favor of brevity.**

**Proposed Change**:
```
**详细度与叙事性的平衡：**

- 保持叙事节奏，但不要为了简洁而牺牲重要细节
- 段落可以稍长（4-6句），如果包含重要的例子、引述或数据
- 使用具体的例子和引述让抽象概念具体化
- **重要原则**：宁可稍微详细，也不要过于概括而失去关键信息
- 如果转录本中有生动的细节、具体的例子或重要的引述，请尽量融入文章
- 每段应该聚焦一个观点，但可以包含支撑的细节（引述、数据、例子）

**示例**：
❌ 过于简略："玩家对游戏的挫败感很高"
✅ 包含细节："一位玩家描述，他在游戏中'最快一把37秒就被打死'，这种完全不可控的挫败感让他'红温一整周'"
```

---

### Solution 4: Improve Sequential Chunking Context (MEDIUM IMPACT)

**Problem**: Sequential chunks lose context from previous chunks.

**Current**: Each chunk analyzed independently with only summary from scratchpad.

**Proposed Enhancement**:
**File**: `research/phases/phase3_execute.py`

**Track Processed Chunk Content**:
```python
def execute(self, research_plan, batch_data):
    # Track processed transcript content
    processed_transcript_content = []  # NEW
    
    for step in research_plan:
        # ... existing code ...
        
        if chunk_strategy == "sequential" and required_data in ["transcript", "transcript_with_comments"]:
            # Store processed content for future reference
            processed_transcript_content.append({
                "step_id": step_id,
                "content_preview": data_chunk[:1000],  # First 1000 chars for context
                "key_quotes": findings.get("findings", {}).get("points_of_interest", {}).get("specific_examples", [])
            })
            
            # When processing later chunks, include context from previous chunks
            previous_chunks_summary = self._summarize_processed_chunks(processed_transcript_content)
            previous_chunks_context = previous_chunks_summary  # Enhanced context
```

**Update Instructions**:
**File**: `research/prompts/phase3_execute/instructions.md`

**Add**:
```
**顺序处理数据块时的注意事项：**

如果你看到"之前处理的数据块摘要"，请注意：
- 这些是之前分析过的转录本片段
- 虽然已有发现，但新的数据块可能包含补充细节、不同的角度或新的例子
- 不要假设之前的数据块已经涵盖了所有内容
- 对于新数据块中的具体例子、引述和数据，即使主题相似，也要记录，因为它们可能提供不同的细节
```

---

### Solution 5: Enhance Phase 2 Planning for Comprehensive Coverage (MEDIUM-HIGH IMPACT)

**Problem**: Phase 2 may not be aware of:
- The increased character limit (50K vs 8K) - can now use "all" strategy more often
- Need for comprehensive transcript coverage
- Importance of detail extraction vs summarization
- Need for synthesis steps that combine all chunks

**Proposed Enhancements**:

#### 5.1. Update Phase 2 Instructions for Comprehensive Planning

**File**: `research/prompts/phase2_plan/instructions.md`

**Add Section** (after line 33):
```
**数据块大小限制说明：**

- **转录本**：每个数据块最多可包含约50,000字符的内容（比之前的8,000字符大幅增加）
- **评论**：每个数据块最多可包含约15,000字符
- 这意味着：
  * 对于中等大小的转录本（<10,000字），可以直接使用"all"策略处理完整内容
  * 对于大型转录本（>10,000字），使用"sequential"策略，每个块可包含更多内容（建议chunk_size: 3000-5000字）
  * 不需要过度分块，尽量让每个块包含足够的上下文

**详细内容提取策略：**

在创建研究计划时，请确保：

1. **全面覆盖**：
   - 对于大转录本（>5,000字），必须使用"sequential"策略确保所有内容都被分析
   - 不要因为内容长而跳过某些部分
   - 每个sequential步骤应该处理足够的内容（建议chunk_size: 3000-5000字）

2. **细节提取**：
   - 创建步骤来提取具体的引述、例子、数据点（不要只总结）
   - 这些细节将用于最终报告，所以需要具体而非抽象
   - 考虑添加专门步骤来收集"可引用语句"和"具体例子"

3. **综合步骤**：
   - 如果使用了sequential分块，必须在最后添加"previous_findings"类型的综合步骤
   - 这个综合步骤应该整合所有块的发现，识别跨块的主题和连接
   - 确保所有块中的重要细节都被保留和整合

4. **策略选择指南**：
   - **小转录本（<5,000字）**: 使用"all"策略，一次性处理
   - **中等转录本（5,000-10,000字）**: 优先考虑"all"，如果接近限制则使用"sequential"（chunk_size: 4000-5000字）
   - **大转录本（>10,000字）**: 必须使用"sequential"（chunk_size: 3000-5000字），并在最后添加综合步骤
```

#### 5.2. Enhance Data Summary for Phase 2

**File**: `research/phases/phase2_plan.py`

**Add Context**:
```python
# Calculate transcript size distribution
transcript_sizes = []
for link_id, data in batch_data.items():
    transcript = data.get("transcript", "")
    if transcript:
        word_count = len(transcript.split())
        transcript_sizes.append(word_count)

if transcript_sizes:
    max_transcript_words = max(transcript_sizes)
    avg_transcript_words = sum(transcript_sizes) / len(transcript_sizes)
    large_transcript_count = sum(1 for s in transcript_sizes if s > 5000)
    
    size_guidance = f"""
**转录本大小分析：**
- 最大转录本: {max_transcript_words} 字
- 平均转录本: {int(avg_transcript_words)} 字
- 大型转录本（>5000字）: {large_transcript_count} 个

**策略建议：**
- 如果有大型转录本，必须使用"sequential"策略确保全面覆盖
- chunk_size建议：3000-5000字（充分利用新的50K字符限制）
"""
else:
    size_guidance = ""
```

**Rationale**: 
- Phase 2 now aware of transcript sizes
- Can make informed decisions about chunk strategies
- Ensures comprehensive coverage planning
- Encourages detail extraction steps

---

### Solution 6: Add Configuration for Content Limits (LOW IMPACT)

**File**: `config.yaml` or new configuration

**Add**:
```yaml
research:
  phase3:
    data_chunk_limits:
      transcript_max_chars: 50000  # Increase from 8000
      comments_max_chars: 15000
      metadata_max_chars: 10000
    preserve_raw_quotes: true
    preserve_detailed_context: true
```

**Implementation**:
Load limits from config instead of hardcoded values.

---

## Implementation Priority

### Phase 1: Critical Fixes (Highest Impact)
**Estimated Time**: 1-2 hours

1. ✅ **Solution 1**: Increase/remove character limit for transcripts
   - Implement dynamic limit based on content type
   - Remove hard 8K limit for transcripts
   - Add logging when truncation occurs

**Impact**: Immediately preserves much more transcript content

2. ✅ **Solution 3**: Update Phase 4 instructions to balance brevity with detail
   - Clarify that details are important
   - Emphasize using quotes and examples
   - Adjust paragraph length guidance

**Impact**: AI will preserve more details in final article

### Phase 2: Enhanced Planning & Preservation (Medium-High Impact)
**Estimated Time**: 2-3 hours

3. ✅ **Solution 5**: Enhance Phase 2 planning for comprehensive coverage
   - Update Phase 2 instructions with size-based strategy guidance
   - Add transcript size analysis to Phase 2 context
   - Emphasize comprehensive coverage and detail extraction
   - Guide chunk strategy and size selection

**Impact**: Plans will ensure all transcript content is processed comprehensively

4. ✅ **Solution 2**: Enhance Phase 3 quote extraction
   - Update Phase 3 instructions for clean, quotable statements
   - Emphasize preserving specific details and examples
   - Guide AI to clean quotes (remove fillers) while preserving meaning

**Impact**: Better quality, quotable statements preserved (cleaned but faithful)

5. ✅ **Solution 4**: Improve sequential chunking context
   - Track processed content
   - Provide better context between chunks
   - Update instructions for sequential processing

**Impact**: Better context preservation across chunks

### Phase 3: Configuration (Low Impact, Optional)
**Estimated Time**: 30 minutes

6. ✅ **Solution 6**: Add configuration (optional)
   - Make limits configurable
   - Allow easy adjustment

**Impact**: Flexibility for different use cases

---

## Success Metrics

### Before (Current):
- ❌ 8,000 character hard limit truncates transcripts
- ❌ Only structured summaries reach Phase 4
- ❌ Phase 4 emphasizes brevity, may skip details
- ❌ Sequential chunks lose context

### After (Target):
- ✅ 50,000+ character limit for transcripts (or removed)
- ✅ Clean, quotable statements preserved (cleaned but faithful to source)
- ✅ Phase 4 balances narrative with detail preservation
- ✅ Sequential chunks maintain better context
- ✅ Articles include specific quotes, examples, and data from full transcripts

### Qualitative Indicators:
- Articles reference specific, clean quotes from transcripts (cleaned of fillers but faithful)
- Detailed examples and data points appear in articles
- Longer, more substantive articles (2000+ words vs current ~900 words)
- More transcript content utilized (50%+ vs current estimated 20-30%)
- Quotes are readable and impactful, not raw/unfiltered

### Quantitative Indicators:
- Character limit increased: 8K → 50K for transcripts
- Article word count: ~900 words → 2000-3000+ words
- Quote density: ~5 quotes → 15-20+ clean, quotable statements
- Detail density: More specific examples, data points, and contextual information

---

## Risks & Mitigation

### Risk 1: API Context Limits
**Concern**: Larger chunks may exceed API context windows.

**Mitigation**:
- Test with Qwen3-max to verify context limits
- Implement token counting (more accurate than character counting)
- Add graceful fallback to chunking if needed
- Monitor API usage

### Risk 2: Longer Processing Time
**Concern**: Larger chunks = longer API calls.

**Mitigation**:
- Acceptable trade-off for better content
- Can optimize later if needed
- Process is async/streaming anyway

### Risk 3: Too Much Detail (Information Overload)
**Concern**: Too many quotes/details might make article overwhelming.

**Mitigation**:
- Phase 4 instructions balance narrative with detail
- AI can still prioritize most relevant details
- Better to have too much than too little (can be refined)

### Risk 4: Increased API Costs
**Concern**: Larger context = more tokens = higher cost.

**Mitigation**:
- Acceptable for quality improvement
- Can add budget monitoring
- Much better ROI than losing content

### Risk 5: Clean Quotes May Lose Original Voice
**Concern**: Cleaning quotes might remove important nuances or speaker characteristics.

**Mitigation**:
- Instructions emphasize cleaning fillers, not changing meaning
- Preserve speaker's style and tone
- "Clean but faithful" - remove "um", "uh", repetitive words, but keep the essence

---

## Testing Strategy

### Test Case 1: Large Transcript Preservation
- Use batch with large transcript (10,000+ words)
- Verify all content processed (not truncated at 8K)
- Check that Phase 4 article includes content from later parts of transcript

### Test Case 2: Quote Quality
- Verify clean, quotable statements appear in findings
- Check that quotes make it to final article (cleaned but readable)
- Ensure quotes are specific and impactful, not just paraphrases
- Verify quotes are readable (no weird fillers or incomplete sentences)

### Test Case 3: Sequential Chunking
- Use sequential strategy with multi-chunk transcript
- Verify context preserved across chunks
- Check that final article synthesizes all chunks

### Test Case 4: Detail Density
- Compare article word count before/after
- Count quotes and specific examples
- Verify detailed data points preserved

---

## Alternative Approaches Considered

### Option A: Two-Pass Processing
**Approach**: First pass extracts details, second pass writes article.

**Pros**: Ensures all details extracted before writing

**Cons**: 
- More complex
- Slower
- May not be necessary if limits increased

**Verdict**: Not needed if other solutions work

### Option B: Pre-Processing Transcripts
**Approach**: Pre-extract all quotes and examples before Phase 3.

**Pros**: Guaranteed preservation

**Cons**:
- Requires significant refactoring
- May extract irrelevant details
- Better to let AI decide what's relevant

**Verdict**: Not recommended - too rigid

### Option C: Post-Processing Enhancement
**Approach**: Generate article, then add details in second pass.

**Pros**: Fast implementation

**Cons**:
- Details might not integrate naturally
- Two-stage process less elegant

**Verdict**: Prefer fixing root causes

---

## Conclusion

### Primary Issue
**Hard 8,000 character limit** is the main bottleneck truncating transcript content.

### Solution Priority
1. **Remove/increase character limit** for transcripts (immediate impact)
2. **Balance Phase 4 instructions** between brevity and detail (medium-high impact)
3. **Enhance Phase 2 planning** for comprehensive coverage (medium-high impact)
4. **Enhance Phase 3 quote extraction** for clean, quotable statements (medium impact)

### Expected Outcome
Articles that are:
- **More detailed** (2000-3000+ words vs current ~900)
- **Richer in quotes** (15-20+ specific quotes vs current ~5)
- **More comprehensive** (utilize 50%+ of transcript content vs current 20-30%)
- **Still narrative** (maintain journalistic style while including detail)

---

## Next Steps (After Approval)

1. Review and approve this plan
2. Implement Phase 1 (critical fixes)
3. Test with sample batch
4. Verify detail preservation
5. Implement Phase 2 if needed
6. Document final approach

