# Advanced Detail Preservation Plan

## Problem Analysis

After implementing the initial detail preservation improvements, articles are better but still need:
- **More comprehensive detail coverage** - more quotes, examples, and specific data points
- **Even less truncation** - very large transcripts may still lose content
- **More professional appearance** - higher detail density, better integration of evidence
- **Better utilization of transcript content** - currently estimated at 30-40%, target 60-70%+

### Current State After First Round of Improvements

**What's Working:**
- ✅ 50K character limit for transcripts (vs previous 8K)
- ✅ Better Phase 2 planning with size-based guidance
- ✅ Enhanced quote extraction instructions in Phase 3
- ✅ Balance instructions in Phase 4 for detail vs brevity
- ✅ Sequential chunking context tracking with quotes

**Remaining Issues:**

#### 1. **Sequential Chunking Still Summarizes Too Much**
**Problem**: Even with 50K limit, large transcripts get split. Each chunk is processed independently, and only summaries/quotes from previous chunks are passed forward, not the full detail-rich content.

**Impact**: 
- Later chunks lose context from earlier chunks
- Important details from early chunks may be summarized away
- Cross-chunk connections and quotes may be lost

**Evidence**: Reports show good quotes but could have more specific examples and data points from across the full transcript.

#### 2. **Scratchpad May Filter Details During Synthesis**
**Problem**: Scratchpad stores structured findings (JSON), but when Phase 4 accesses it via `get_scratchpad_summary()`, the summary format might condense detailed quotes and examples.

**Location**: `research/session.py:145-209`

**Current Format**:
- JSON dumps of findings
- Counts of points of interest
- Insights summaries

**Issue**: Detailed quotes within `points_of_interest.specific_examples` or `notable_evidence.quote` might not be fully preserved or emphasized in the summary.

#### 3. **Phase 3 May Still Prioritize Summary Over Detail Extraction**
**Problem**: Even with enhanced instructions, Phase 3's primary goal is to complete the step objective, with detail extraction as secondary. The AI may complete the goal first, then add details if "there's space," rather than prioritizing detailed extraction.

#### 4. **No Dedicated Detail Collection Phase**
**Problem**: There's no specialized step type or phase that focuses EXCLUSIVELY on collecting detailed quotes, examples, and data points without other analytical goals. Phase 2 may create general analysis steps, but not dedicated "quote harvesting" steps.

#### 5. **Phase 4 Instructions Could Require Higher Detail Density**
**Problem**: Phase 4 instructions balance detail with narrative, but could be more explicit about:
- Minimum quote density (e.g., "aim for 1-2 quotes per 100 words")
- Minimum example density (e.g., "every major claim should have at least one specific example")
- Evidence-to-claim ratio (e.g., "support every analytical statement with at least one concrete detail")

#### 6. **Very Large Transcripts May Still Get Truncated**
**Problem**: 50K character limit is good, but for extremely large transcripts (>100K characters), even sequential chunks of 50K each may not be enough, or the transcript may be split in ways that lose context.

#### 7. **Phase 2 Might Not Create Enough Steps for Large Transcripts**
**Problem**: Phase 2 planning might create too few steps, assuming fewer larger chunks. For very detailed articles, we might need MORE steps, each focusing on extracting specific detail types.

---

## Proposed Solutions

### Solution 1: Multi-Pass Detail Collection (HIGH IMPACT)

**Concept**: After initial analysis steps, add a dedicated "detail collection pass" that re-processes transcripts with the SINGLE goal of extracting maximum quotes, examples, and data points.

#### 1.1. Add "detail_collection" Step Type to Phase 2

**File**: `research/prompts/phase2_plan/instructions.md`

**Add Step Type**:
```
- `'detail_collection'`：专门收集详细引述、例子和数据点（用于最终报告的详细素材）
  * 专注于提取清晰的引述、具体例子、统计数据
  * 不需要完成分析目标，只需要收集素材
  * 建议在主要分析步骤之后、综合步骤之前添加
```

**Update Planning Guidance**:
```
**详细素材收集步骤建议：**

对于大转录本或需要详细报告的研究，考虑添加专门步骤：

- **步骤类型**: 使用"detail_collection"作为required_data（或作为goal描述中的关键词）
- **时机**: 在完成主要分析步骤后、综合步骤前
- **目标**: 不是分析，而是收集
  * 提取可直接引用的完整语句（清理但完整）
  * 收集具体数据点、统计数字、时间、地点
  * 识别生动的例子和场景描述
  * 记录支撑论点的所有细节
- **策略**: 使用"all"或"sequential"但focus on extraction over analysis
```

#### 1.2. Create Dedicated Detail Collection Handler in Phase 3

**File**: `research/phases/phase3_execute.py`

**Add Handler**:
```python
def _execute_detail_collection_step(
    self,
    step_id: int,
    data_chunk: str,
    scratchpad_summary: str,
    required_data: str,
    chunk_strategy: str,
    previous_chunks_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute a detail collection step - focus ONLY on extracting detailed quotes,
    examples, and data points.
    """
    # Use specialized prompt or add context flag
    context = {
        "step_id": step_id,
        "goal": "收集详细的引述、例子和数据点，用于最终报告。重点是提取而非分析。",
        "data_chunk": safe_data_chunk,
        "scratchpad_summary": scratchpad_summary,
        "previous_chunks_context": previous_chunks_context,
        "detail_collection_mode": True  # Flag for specialized handling
    }
    # ... rest of execution
```

**Alternative**: Add flag to existing `_execute_step` to switch to "detail collection mode" when goal contains "detail_collection" keywords.

#### 1.3. Enhanced Detail Collection Instructions

**File**: `research/prompts/phase3_execute/instructions.md`

**Add Section** (to be included when detail_collection_mode is active):
```
**详细素材收集模式：**

如果你的目标是"收集详细的引述、例子和数据点"，请遵循以下原则：

1. **优先提取，而非分析**：
   - 不要总结或概括
   - 提取完整的、可直接使用的原文（清理后）
   - 宁可多记录，也不要遗漏

2. **引述要求**：
   - 提取所有清晰、有力量的原话
   - 包括必要的上下文（说话者、情境）
   - 记录完整的句子，不要片段
   - 目标：收集至少15-20条可直接引用的语句

3. **例子和细节**：
   - 提取所有具体的数据（数字、统计、时间、地点）
   - 收集所有生动的描述和场景
   - 记录所有能让论点更具体的细节
   - 目标：确保每个主要话题都有至少3-5个具体例子

4. **不要过滤**：
   - 即使是看似次要的细节，如果可能支撑论点，也要记录
   - 让Phase 4决定如何使用，不要在这里筛选
   - 重点是完整性，不是精炼性
```

---

### Solution 2: Enhanced Scratchpad Detail Preservation (MEDIUM-HIGH IMPACT)

**Problem**: Scratchpad summary format may condense detailed quotes and examples.

#### 2.1. Enhance Scratchpad Summary Format

**File**: `research/session.py`

**Current**: `get_scratchpad_summary()` formats JSON findings into text.

**Enhancement**: Ensure detailed quotes and examples are prominently featured, not buried.

**Proposed Format Enhancement**:
```python
def get_scratchpad_summary(self) -> str:
    """Enhanced to preserve detailed quotes and examples."""
    # ... existing code ...
    
    # For each step, explicitly extract and format quotes/examples
    for step_data in scratchpad:
        points_of_interest = step_data.get("findings", {}).get("points_of_interest", {})
        
        # Extract and format quotes prominently
        if points_of_interest:
            quotes_section = "\n**重要引述和例子**:\n"
            
            # Key claims with quotes
            for claim in points_of_interest.get("key_claims", [])[:5]:
                if isinstance(claim, dict) and claim.get("claim"):
                    quotes_section += f"- \"{claim['claim']}\""
                    if claim.get("supporting_evidence"):
                        quotes_section += f" (证据: {claim['supporting_evidence'][:100]})"
                    quotes_section += "\n"
            
            # Notable evidence quotes
            for evidence in points_of_interest.get("notable_evidence", [])[:5]:
                if isinstance(evidence, dict) and evidence.get("quote"):
                    quotes_section += f"- \"{evidence['quote']}\""
                    if evidence.get("description"):
                        quotes_section += f" ({evidence['description'][:80]})"
                    quotes_section += "\n"
            
            # Specific examples
            for example in points_of_interest.get("specific_examples", [])[:5]:
                if isinstance(example, dict) and example.get("example"):
                    quotes_section += f"- 例子: {example['example']}"
                    if example.get("context"):
                        quotes_section += f" (上下文: {example['context'][:80]})"
                    quotes_section += "\n"
            
            step_summary += quotes_section + "\n"
```

**Rationale**: Make quotes and examples highly visible in scratchpad summary, not buried in JSON structure.

#### 2.2. Store Raw Extracted Details Separately

**Alternative Approach**: Store detailed quotes/examples in a separate field that's explicitly included in Phase 4 context.

**File**: `research/session.py`

```python
def update_scratchpad(
    self,
    step_id: int,
    findings: Dict[str, Any],
    insights: str = "",
    confidence: float = 0.0,
    sources: Optional[List[str]] = None,
    extracted_details: Optional[Dict[str, List[str]]] = None  # NEW
):
    """
    extracted_details format:
    {
        "quotes": ["quote1", "quote2", ...],
        "examples": ["example1", "example2", ...],
        "data_points": ["data1", "data2", ...]
    }
    """
    # Store in scratchpad entry
    scratchpad_entry = {
        # ... existing fields ...
        "extracted_details": extracted_details or {}
    }
```

Then in `get_scratchpad_summary()`, append all `extracted_details` prominently.

---

### Solution 3: Increase Detail Density Requirements in Phase 4 (MEDIUM IMPACT)

#### 3.1. Add Explicit Detail Density Targets

**File**: `research/prompts/phase4_synthesize/instructions.md`

**Add Section**:
```
**详细度标准：**

为了生成专业、详细的文章，请遵循以下密度标准：

1. **引述密度**：
   - 目标：每100-150字至少包含1条引述或直接引用
   - 文章总长度目标：2000-3500字（对于详细报告）
   - 直接引述应该：具体、生动、支撑论点
   - 间接引用或转述也需要具体细节，不只是概括

2. **例子和数据密度**：
   - 每个主要论点应该包含至少1-2个具体例子或数据点
   - 使用具体数字、时间、地点、名称
   - 优先使用生动的、可感知的描述

3. **证据支撑**：
   - 避免"很多玩家认为"这样的概括
   - 使用"一位Reddit用户指出"、"B站评论区中"等具体引用
   - 每个分析性陈述应该至少有一个支撑细节

4. **专业文章的长度**：
   - 目标长度：2000-3500字（中等长度深度报道）
   - 不要为了简洁而牺牲细节
   - 如果素材丰富，文章应该长一些而不是短一些

**示例对比**：
❌ 概括性："玩家对挫败感的反应各有不同"
✅ 详细性："一位玩家描述他在游戏中'最快一把37秒就被打死'，这种完全不可控的挫败感让他'红温一整周'。而另一位Reddit用户则写道：'虽然死了，但我知道是我站位失误，这让我想再试一次。'"
```

#### 3.2. Require Detail Audit

**Add Checklist**:
```
**文章自检清单：**

在完成文章前，检查：
- [ ] 每个主要段落至少包含1条具体引述或例子
- [ ] 每个分析性陈述都有至少1个支撑细节
- [ ] 文章总长度至少2000字（除非数据确实有限）
- [ ] 没有过度概括的地方（如"很多玩家"应改为具体引用）
- [ ] 所有关键数据点、统计数字、时间、地点都已包含
```

---

### Solution 4: Remove or Increase Limits Further for Very Large Transcripts (MEDIUM IMPACT)

**Problem**: 50K might still truncate extremely large transcripts, or sequential chunks might lose cross-chunk context.

#### 4.1. Dynamic Limit Based on Actual Transcript Size

**File**: `research/phases/phase3_execute.py`

**Enhancement**:
```python
def _calculate_dynamic_limit(
    self,
    data_chunk: str,
    required_data: str,
    full_transcript_size: Optional[int] = None
) -> int:
    """
    Calculate dynamic limit based on transcript size and API capacity.
    
    For very large transcripts, use higher limits if we're not splitting too many ways.
    """
    if required_data in ["transcript", "transcript_with_comments"]:
        # Base limit
        base_limit = 50000
        
        # If transcript is very large but we're processing a single chunk,
        # allow more to avoid splitting
        if full_transcript_size:
            if full_transcript_size > 100000 and len(data_chunk) > 80000:
                # Very large transcript, allow up to 100K for single "all" strategy
                return 100000
            elif full_transcript_size > 80000:
                # Large transcript, allow 75000
                return 75000
        
        return base_limit
    # ... rest
```

**Rationale**: For single-chunk "all" strategy on very large transcripts, allow higher limits to avoid unnecessary splitting.

#### 4.2. Pre-analyze Transcript Size Before Chunking

**File**: `research/phases/phase3_execute.py`

**Enhancement**: Before chunking, analyze transcript size. If it's "borderline" (e.g., 55K characters), prefer single larger chunk over splitting if API can handle it.

---

### Solution 5: Enhance Phase 2 to Create More Detail-Focused Steps (MEDIUM IMPACT)

#### 5.1. Explicitly Guide Phase 2 to Create Detail Collection Steps

**File**: `research/prompts/phase2_plan/instructions.md`

**Add Guidance**:
```
**详细素材收集步骤要求：**

对于需要详细、专业报告的研究，必须添加专门步骤来收集详细素材：

1. **何时添加**：
   - 如果转录本总字数 > 5,000字
   - 如果研究目标是深度分析或详细报道
   - 如果最终输出需要大量具体例子和引述

2. **如何添加**：
   - 在主要分析步骤（step_id 1-N）之后
   - 在综合步骤（previous_findings）之前
   - 使用goal描述如："收集详细的引述、例子和数据点，用于支撑最终报告"
   - 使用required_data: "transcript"或"transcript_with_comments"
   - 使用chunk_strategy: "all"（如果可以）或"sequential" with larger chunk_size

3. **多少个步骤**：
   - 如果转录本 < 10,000字：添加1个detail collection步骤
   - 如果转录本 >= 10,000字：添加2-3个detail collection步骤（覆盖不同方面）
```

#### 5.2. Calculate Detail Collection Step Requirements

**File**: `research/phases/phase2_plan.py`

**Enhancement**: After receiving plan from AI, analyze it and potentially add detail collection steps if:
- Transcript size is large
- Plan has few detail-focused steps
- Plan doesn't have explicit detail collection

**Approach**: Could either:
- Guide AI more explicitly in instructions
- Or post-process plan to add detail steps
- Or use a two-stage planning (main analysis + detail collection)

---

### Solution 6: Two-Pass Processing for Large Transcripts (LOW-MEDIUM IMPACT)

**Concept**: For very large transcripts, use two-pass approach:
1. **Pass 1**: Analysis (existing flow)
2. **Pass 2**: Detail extraction (dedicated detail collection on full transcript)

#### 6.1. Optional Two-Pass Mode

**File**: `research/phases/phase3_execute.py`

**Enhancement**: If transcript is very large (>100K chars) and research goal requires high detail, execute two passes:

```python
def execute(self, research_plan, batch_data):
    # Pass 1: Execute main research plan
    all_findings = []
    for step in research_plan:
        # ... existing execution ...
    
    # Pass 2: Detail extraction (if needed)
    if self._needs_detail_pass(research_plan, batch_data):
        detail_findings = self._execute_detail_pass(batch_data)
        all_findings.extend(detail_findings)
    
    return result
```

**Rationale**: Ensures all transcript content is analyzed for details even if main analysis focuses on specific topics.

---

### Solution 7: Improve Cross-Chunk Context in Sequential Processing (LOW-MEDIUM IMPACT)

**Problem**: Sequential chunks lose detailed context from previous chunks.

#### 7.1. Store More Complete Previous Chunk Summaries

**File**: `research/phases/phase3_execute.py`

**Current**: `_track_chunk()` stores: preview + insights + top 3 quotes

**Enhancement**: For sequential processing, store more:
- Full extracted quotes list (not just top 3)
- All key examples from the chunk
- Summary of claims and themes

```python
def _track_chunk(self, step_id, data_chunk, findings):
    # Extract ALL quotes, not just top 3
    all_quotes = []
    # ... extract all quotable statements ...
    
    chunk_summary = {
        # ... existing fields ...
        "all_quotes": all_quotes[:10],  # Top 10 quotes
        "all_examples": all_examples[:8],  # Top 8 examples
        "key_themes": extracted_themes  # Themes covered in this chunk
    }
```

#### 7.2. Enhanced Previous Chunks Context

**File**: `research/phases/phase3_execute.py`

**Enhancement**: `_get_previous_chunks_context()` should include:
- More quotes (5-8 per previous chunk, not 2)
- Themes so AI knows what was covered
- Examples so AI can build on them

---

## Implementation Priority

### Phase 1: High-Impact Quick Wins (2-3 hours)

1. ✅ **Solution 3**: Add detail density requirements to Phase 4
   - Explicit targets (quotes per 100 words, minimum length)
   - Detail audit checklist
   - Clear examples of detail vs. summary

2. ✅ **Solution 2.1**: Enhance scratchpad summary format
   - Make quotes/examples prominently visible
   - Don't bury them in JSON structure
   - Extract and format explicitly

**Impact**: Immediate improvement in detail visibility and requirements

### Phase 2: Medium-High Impact Enhancements (3-4 hours)

3. ✅ **Solution 1**: Multi-pass detail collection
   - Add detail_collection step type
   - Create dedicated handler
   - Enhanced instructions for detail mode

4. ✅ **Solution 5**: Enhance Phase 2 to create detail collection steps
   - Guide Phase 2 to explicitly plan detail steps
   - Calculate when detail steps are needed

**Impact**: Systematic detail collection before synthesis

### Phase 3: Refinements (2-3 hours)

5. ✅ **Solution 4**: Dynamic limits for very large transcripts
   - Increase limits for single-chunk "all" strategy
   - Pre-analyze before chunking

6. ✅ **Solution 7**: Improve sequential chunking context
   - Store more complete previous chunk summaries
   - Include more quotes/examples in context

**Impact**: Better handling of edge cases

### Phase 4: Advanced (Optional, 2-3 hours)

7. ✅ **Solution 6**: Two-pass processing (optional)
   - Only for very large transcripts
   - Separate detail extraction pass

**Impact**: Maximum detail for very large transcripts (optional)

---

## Expected Outcomes

### Quantitative Improvements

- **Quote density**: 5-8 quotes → 15-25 quotes per article
- **Article length**: 900-1500 words → 2000-3500 words
- **Example density**: 1 example per 200 words → 1 example per 100 words
- **Transcript utilization**: 30-40% → 60-70%+

### Qualitative Improvements

- **Professional appearance**: Articles look like well-researched journalism with strong evidence
- **Less truncation**: All important transcript content represented
- **Better integration**: Quotes and examples naturally woven into narrative
- **Higher credibility**: Every claim supported by specific evidence

### Success Metrics

**Before (After First Round)**:
- ~1000-1500 word articles
- ~5-8 quotes
- 30-40% transcript utilization

**After (This Round)**:
- 2000-3500 word articles
- 15-25 quotes
- 60-70%+ transcript utilization
- Every major claim has supporting evidence
- Professional detail density

---

## Risks & Mitigation

### Risk 1: Articles Become Too Long
**Concern**: Higher detail requirements might create overly long articles.

**Mitigation**:
- Target is 2000-3500 words (professional length)
- AI can still prioritize most relevant details
- Better to have too much than too little (can be edited)

### Risk 2: Information Overload
**Concern**: Too many quotes/details might overwhelm readers.

**Mitigation**:
- Phase 4 instructions emphasize narrative integration
- AI can still choose most impactful quotes/examples
- Journalistic style naturally manages detail density

### Risk 3: Increased Processing Time
**Concern**: More steps and detail passes = longer processing.

**Mitigation**:
- Acceptable trade-off for quality
- Can optimize later if needed
- Users value quality over speed

### Risk 4: API Costs
**Concern**: Larger context and more passes = higher costs.

**Mitigation**:
- Acceptable for significantly better output
- Can add budget monitoring
- ROI much better than losing content

---

## Testing Strategy

### Test Case 1: Detail Collection Steps
- Verify Phase 2 creates detail collection steps for large transcripts
- Check that detail steps extract quotes/examples without analysis
- Verify detail findings appear in final article

### Test Case 2: Scratchpad Detail Preservation
- Check scratchpad summary prominently displays quotes/examples
- Verify Phase 4 receives detailed quotes, not just summaries
- Ensure no detail loss in scratchpad → Phase 4 handoff

### Test Case 3: Detail Density in Articles
- Count quotes per 100 words (target: 0.7-1.0)
- Count examples per claim (target: 1-2)
- Measure article length (target: 2000-3500 words)
- Verify transcript utilization (target: 60%+)

### Test Case 4: Very Large Transcripts
- Test with 100K+ character transcript
- Verify dynamic limits allow single-chunk processing when possible
- Check two-pass detail extraction if implemented
- Ensure all content represented

---

## Conclusion

### Key Strategy

The primary improvement strategy is **systematic detail collection before synthesis**:

1. **Plan for detail**: Phase 2 explicitly creates detail collection steps
2. **Collect systematically**: Phase 3 has dedicated detail extraction mode
3. **Preserve prominently**: Scratchpad highlights quotes/examples
4. **Require explicitly**: Phase 4 has clear density targets and checklist

### Expected Result

Articles that are:
- **More detailed** (2000-3500 words vs current 1000-1500)
- **Richer in evidence** (15-25 quotes vs current 5-8)
- **More professional** (high detail density, strong evidence-to-claim ratio)
- **Less truncated** (60-70%+ transcript utilization vs current 30-40%)
- **Better integrated** (quotes/examples naturally woven, not just listed)

### Next Steps (After Approval)

1. Implement Phase 1 (quick wins)
2. Test with sample batch
3. Verify detail improvements
4. Implement Phase 2 if needed
5. Iterate based on results

