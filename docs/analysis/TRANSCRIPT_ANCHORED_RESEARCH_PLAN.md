# Transcript-Anchored Research Method: Implementation Plan

## Overview

This document outlines a plan to restructure the deep research tool so that **transcripts/articles serve as the primary anchor data source**, with **comments used to augment and supplement** the transcript-based analysis. This change aligns with the principle that transcripts contain the core authored content, while comments provide contextual reactions, discussions, and alternative perspectives.

## Current State Analysis

### Current Implementation

1. **Data Structure** (`data_loader.py`):
   - Each content item has separate `transcript` and `comments` fields
   - Both are loaded and available in `batch_data`
   - Abstract creation samples from both independently

2. **Phase 2 Planning** (`phase2_plan.py`):
   - LLM generates plan with `required_data` field
   - `required_data` can be: `"transcript"`, `"comments"`, `"metadata"`, or `"previous_findings"`
   - These are **mutually exclusive** choices per step

3. **Phase 3 Execution** (`phase3_execute.py`):
   - `_prepare_data_chunk()` checks `required_data` and processes ONLY that type
   - Lines 132-163: Processes transcripts when `required_data == "transcript"`
   - Lines 165-199: Processes comments when `required_data == "comments"`
   - **No mechanism to combine both with hierarchical importance**

4. **Current Prompts**:
   - `phase2_plan/instructions.md`: Lists data types as equal options
   - `phase3_execute/instructions.md`: Receives `data_chunk` without clear indication of primary vs. secondary data

### Current Problems

1. ❌ **Transcripts and comments treated as equal alternatives**, not primary vs. augmenting
2. ❌ **No prioritization of transcript content** over comments in analysis
3. ❌ **Separate steps for transcript vs. comments** prevents holistic understanding
4. ❌ **Phase 2 may generate comment-only steps**, missing core content
5. ❌ **Comments may dominate analysis** if plan prioritizes them

---

## Proposed Changes

### Principle: Transcripts as Anchors, Comments as Augmentation

**Core Philosophy**:
- Transcripts/articles contain the **primary, authored content** — this is the core narrative
- Comments provide **reactions, discussions, alternative perspectives** — these augment understanding
- Analysis should **anchor on transcripts** and use comments to:
  - Validate or contradict transcript claims
  - Add emotional reactions and community sentiment
  - Identify controversial points
  - Surface counter-examples or exceptions
  - Provide real-world application contexts

### Changes by Phase

---

## Phase 0: Data Preparation (`phase0_prepare.py`)

### Changes Required

**Minimal changes** — Phase 0 already loads both transcripts and comments correctly.

**Optional Enhancement**:
- Add metadata flag `has_transcript` and `has_comments` for better planning
- Store ratio of transcript words to comment count for quality assessment

**Implementation**:
```python
# In data_loader.py:load_batch()
link_data[link_id]["data_availability"] = {
    "has_transcript": bool(transcript),
    "has_comments": bool(comments),
    "transcript_word_count": len(transcript.split()) if transcript else 0,
    "comment_count": len(comments) if comments else 0
}
```

---

## Phase 2: Research Planning (`phase2_plan.py`)

### Changes Required

1. **Modify Planning Instructions** (`research/prompts/phase2_plan/instructions.md`):
   - Emphasize that **transcripts are primary** — steps should primarily use transcript data
   - Comments should be included as **augmentation** when available
   - Remove `required_data == "comments"` as standalone option
   - Update `required_data` options to:
     - `"transcript"` (primary anchor, may include comments as context)
     - `"transcript_with_comments"` (explicitly include comments as augmentation)
     - `"metadata"` (for planning/context)
     - `"previous_findings"` (for synthesis steps)

2. **Update Planning Prompt**:
   - Instruct LLM to prioritize transcript-based steps
   - Guide LLM to use comments only as supplementary context
   - Add examples showing transcript-first planning

3. **Data Summary Enhancement**:
   - Include transcript/comment availability ratios in context
   - Highlight when transcripts are missing (require alternative strategies)

### New Prompt Structure (Example)

```markdown
**数据优先级:**
- **主要数据源**: 转录本/文章内容（包含核心观点和主要叙述）
- **补充数据源**: 评论数据（用于验证、补充情感反应和争议点）
- **必须**: 所有分析步骤应基于转录本作为主要锚点
- **可选**: 当评论可用时，将其作为补充上下文包含在分析中

**required_data 选项:**
- `"transcript"`: 使用转录本作为主要数据（推荐，注释将自动作为上下文添加）
- `"transcript_with_comments"`: 明确要求包含评论作为增强
- `"metadata"`: 仅元数据（用于上下文了解）
- `"previous_findings"`: 之前的发现（用于综合步骤）
```

### Schema Changes

**No changes needed** to JSON schema structure, but update validation to:
- Accept `"transcript"` and `"transcript_with_comments"` (deprecate standalone `"comments"`)
- Warn if plan has steps with `required_data == "comments"` (should be migrated to transcript-based)

---

## Phase 3: Execute Plan (`phase3_execute.py`)

### Major Changes Required

#### 1. **Modify `_prepare_data_chunk()` Method**

**Current Behavior**:
- Separate if-elif blocks for `"transcript"` vs `"comments"`
- Returns single data type only

**New Behavior**:
- **Always prioritize transcripts** when available
- **Automatically include comments** as augmentation when present
- Structure data chunk with clear sections: Primary Content vs. Supplementary Context

**New Implementation Structure**:
```python
def _prepare_data_chunk(...):
    if required_data in ["transcript", "transcript_with_comments"]:
        # PRIMARY: Get transcript content
        transcript_content = self._get_transcript_content(batch_data, required_data, ...)
        
        # AUGMENTATION: Get comments (if available and requested)
        comments_content = None
        if required_data == "transcript_with_comments" or comments_available:
            comments_content = self._get_comments_content(batch_data, ...)
        
        # Structure combined chunk with clear hierarchy
        combined_chunk = self._structure_combined_chunk(
            transcript_content,  # Primary anchor
            comments_content,     # Augmentation (optional)
            source_info
        )
        
        return combined_chunk, source_info
```

#### 2. **New Helper Method: `_structure_combined_chunk()`**

**Purpose**: Create clear data structure that shows transcript as primary, comments as supplementary

**Structure**:
```python
def _structure_combined_chunk(
    self,
    transcript_content: str,
    comments_content: Optional[str],
    source_info: Dict[str, Any]
) -> str:
    """
    Structure data chunk with transcript as primary anchor,
    comments as augmentation.
    
    Returns formatted string with clear sections.
    """
    parts = []
    
    # PRIMARY SECTION: Transcript content
    parts.append("=" * 80)
    parts.append("主要内容（转录本/文章）")
    parts.append("=" * 80)
    parts.append(transcript_content)
    
    # AUGMENTATION SECTION: Comments (if available)
    if comments_content:
        parts.append("\n\n")
        parts.append("-" * 80)
        parts.append("补充数据（评论）")
        parts.append("-" * 80)
        parts.append("以下评论数据可用于验证、补充情感反应或识别争议点：")
        parts.append(comments_content)
    
    return "\n".join(parts)
```

#### 3. **Update Phase 3 Instructions** (`research/prompts/phase3_execute/instructions.md`)

**Changes**:
- Clarify that `data_chunk` contains **primary content (transcripts)** and optional **comment augmentation**
- Instruct LLM to:
  - **Anchor analysis in transcript content**
  - Use comments to validate, contradict, or add emotional context
  - Not let comments override transcript claims unless strongly supported
  - Clearly indicate when findings come from comments vs. transcripts in source attribution

**New Instructions Section**:
```markdown
**数据优先级说明:**
- "主要内容（转录本/文章）"部分包含核心观点和叙述，应作为分析的主要锚点
- "补充数据（评论）"部分包含社区反应，应用于：
  * 验证或反驳转录本中的声明
  * 识别争议点和对立观点
  * 添加情感反应和社区情绪
  * 提供具体的反例或例外情况

**分析要求:**
- 所有主要发现应基于转录本内容
- 评论数据用于增强和验证，不应成为主要论点的唯一来源
- 在兴趣点提取中，明确区分来源（转录本 vs. 评论）
```

#### 4. **Migration Strategy for Existing Plans**

**Backward Compatibility**:
- If step has `required_data == "comments"`:
  - Check if transcript is available → migrate to `"transcript_with_comments"`
  - If no transcript → log warning and proceed with comments only (edge case)
- If step has `required_data == "transcript"`:
  - Automatically include comments as augmentation if available
  - No behavior change, but enhanced with comment context

**Implementation**:
```python
def _migrate_legacy_required_data(self, required_data: str, batch_data: Dict[str, Any]) -> str:
    """
    Migrate legacy data requirements to transcript-anchored approach.
    """
    if required_data == "comments":
        # Check if transcripts available
        has_transcripts = any(
            data.get("transcript") for data in batch_data.values()
        )
        if has_transcripts:
            self.logger.info("Migrating comment-only step to transcript_with_comments")
            return "transcript_with_comments"
        else:
            self.logger.warning("No transcripts available, using comments only (edge case)")
            return "comments"  # Fallback for edge cases
    
    return required_data
```

---

## Phase 4: Synthesize Report (`phase4_synthesize.py`)

### Changes Required

**Minimal changes** — Phase 4 already synthesizes from scratchpad which contains Phase 3 findings.

**Optional Enhancement**:
- Update synthesis prompt to emphasize that findings should be transcript-anchored
- Add instruction to distinguish between findings from transcripts vs. comments in final report

---

## Data Chunk Structure Examples

### Example 1: Transcript with Comments Augmentation

```
================================================================================
主要内容（转录本/文章）
================================================================================

[Full transcript content here...]

--------------------------------------------------------------------------------
补充数据（评论）
--------------------------------------------------------------------------------
以下评论数据可用于验证、补充情感反应或识别争议点：

- [评论1: 高点赞数，支持转录本观点]
- [评论2: 提出质疑]
- [评论3: 提供补充例子]
...
```

### Example 2: Transcript Only (No Comments Available)

```
================================================================================
主要内容（转录本/文章）
================================================================================

[Full transcript content here...]

(注: 无可用评论数据)
```

### Example 3: Comments Only (Edge Case - No Transcript)

```
⚠️ 警告: 无转录本数据，仅基于评论进行分析

--------------------------------------------------------------------------------
可用数据（评论）
--------------------------------------------------------------------------------

[Comments content here...]
```

---

## Implementation Steps

### Step 1: Update Phase 2 Planning Instructions
- **File**: `research/prompts/phase2_plan/instructions.md`
- **Action**: Rewrite section on `required_data` options to emphasize transcript-first approach
- **Impact**: Future plans will prioritize transcripts

### Step 2: Modify Phase 3 Data Preparation
- **File**: `research/phases/phase3_execute.py`
- **Actions**:
  - Update `_prepare_data_chunk()` to always include transcripts as primary
  - Add `_structure_combined_chunk()` helper method
  - Add `_migrate_legacy_required_data()` for backward compatibility
  - Update `_get_transcript_content()` and `_get_comments_content()` for clear separation

### Step 3: Update Phase 3 Execution Instructions
- **File**: `research/prompts/phase3_execute/instructions.md`
- **Action**: Add section explaining data hierarchy and how to use comment augmentation

### Step 4: Enhance Data Loading (Optional)
- **File**: `research/data_loader.py`
- **Action**: Add data availability metadata for better planning

### Step 5: Testing & Validation
- Test with existing batches to ensure backward compatibility
- Verify that transcript-anchored analysis produces better results
- Check that comment augmentation enhances rather than overrides transcript findings

---

## Expected Benefits

1. ✅ **Clearer Analysis Hierarchy**: Transcripts provide consistent anchor points
2. ✅ **Better Source Attribution**: Findings clearly linked to primary vs. supplementary data
3. ✅ **Improved Research Quality**: Core content (transcripts) prioritized over reactive content (comments)
4. ✅ **More Holistic Understanding**: Comments augment transcripts rather than replace them
5. ✅ **Reduced Noise**: Less chance of comment-only steps missing core content

---

## Potential Risks & Mitigation

### Risk 1: Existing Plans May Fail
- **Mitigation**: Backward compatibility layer migrates old plans automatically
- **Fallback**: If migration fails, log warning and proceed with legacy behavior

### Risk 2: Performance Impact
- **Mitigation**: Only combine comments when explicitly requested or when comments are small
- **Optimization**: Use smart sampling for large comment sets

### Risk 3: Context Window Limits
- **Mitigation**: Use intelligent chunking - prioritize transcript, sample comments strategically
- **Strategy**: Limit comment augmentation to top N (by engagement) when transcript is long

---

## Migration Checklist

- [ ] Update `phase2_plan/instructions.md` with transcript-first guidance
- [ ] Modify `phase3_execute.py` `_prepare_data_chunk()` method
- [ ] Add `_structure_combined_chunk()` helper
- [ ] Add `_migrate_legacy_required_data()` for compatibility
- [ ] Update `phase3_execute/instructions.md` with data hierarchy explanation
- [ ] (Optional) Enhance `data_loader.py` with availability metadata
- [ ] Test with existing batch data
- [ ] Verify backward compatibility with old plans
- [ ] Update documentation

---

## Open Questions

1. **Should we completely remove standalone `"comments"` option?**
   - Recommendation: Keep for edge cases (no transcript available), but log warning

2. **How to handle very large comment sets?**
   - Recommendation: Use engagement-based sampling when including as augmentation

3. **Should Phase 1 goal generation also emphasize transcripts?**
   - Recommendation: Consider updating Phase 1 abstract weighting (transcript samples > comment samples)

4. **How to handle articles (no comments available)?**
   - Recommendation: No change needed - articles work as transcript-only content

---

## Summary

This plan restructures the research tool to treat **transcripts/articles as primary anchors** and **comments as augmentation**. The key changes are:

1. **Phase 2**: Instructions updated to prioritize transcript-based steps
2. **Phase 3**: Data preparation automatically combines transcripts (primary) with comments (augmentation) when available
3. **Prompts**: Updated to guide LLM to anchor analysis in transcripts, use comments for validation/enrichment

This ensures research is anchored in core authored content while leveraging community reactions for deeper understanding.





