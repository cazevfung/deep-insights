# Analysis & Plan: Extracting More Points of Interest

## Current System Limitations

### 1. **Phase 1 (Goal Discovery)**
**Current Behavior:**
- AI sees content abstracts (sampled text)
- Generates 3 research goals only
- No extraction of specific points of interest

**Limitation:**
- Only strategic goals, no tactical details
- Misses immediate interesting patterns
- No preliminary exploration phase

### 2. **Phase 2 (Planning)**
**Current Behavior:**
- Creates plan based on selected goal only
- Plan steps are goal-focused (narrow)
- No "exploratory" steps

**Limitation:**
- Plan doesn't include interest discovery steps
- Assumes all interesting points align with goal
- No general exploration before focused analysis

### 3. **Phase 3 (Execution)**
**Current Behavior:**
- Generic `findings` structure (unstructured dict)
- Only extracts what's needed for step goal
- No systematic interest extraction

**Limitation:**
- Findings structure too flexible (no guidance)
- AI doesn't know what "points of interest" means
- No structured fields for different interest types
- Each step operates in isolation

### 4. **Phase 4 (Synthesis)**
**Current Behavior:**
- Combines findings into report
- Only synthesizes goal-related content

**Limitation:**
- Doesn't highlight surprising/interesting findings
- No section for "interesting discoveries"
- Only goal-focused synthesis

---

## What Are "Points of Interest"?

### Categories to Extract:
1. **Key Claims & Arguments**
   - Main theses proposed
   - Supporting evidence
   - Counter-arguments mentioned

2. **Notable Patterns**
   - Repetitive themes
   - Unexpected connections
   - Trends across sources

3. **Controversial Points**
   - Disagreements in comments
   - Conflicting viewpoints
   - Debated claims

4. **Surprising Insights**
   - Unexpected facts
   - Counterintuitive findings
   - Novel perspectives

5. **Evidence & Examples**
   - Specific examples cited
   - Data points mentioned
   - Quotes worth highlighting

6. **Emotional Resonance**
   - High-engagement comments
   - Polarizing topics
   - Passionate responses

7. **Gaps & Questions**
   - Unanswered questions raised
   - Missing information
   - Areas needing more research

---

## Proposed Solutions

### Strategy 1: Enhance Phase 1 - Preliminary Interest Discovery

**Add Interest Extraction Step Before Goal Generation**

**Approach:**
- Add a new sub-phase: Phase 0.5 "Interest Discovery"
- Extract points of interest from abstracts first
- Use interests to inform goal generation

**Implementation:**
```python
# New phase: Phase0_5_DiscoverInterests
def execute(data_abstract: str) -> Dict[str, Any]:
    """
    Extract preliminary points of interest before goal generation.
    """
    # Prompt AI to extract:
    # - Key themes
    # - Notable claims
    # - Interesting patterns
    # - Questions raised
    # Returns structured interests
```

**Benefits:**
- More informed goal generation
- Captures interests that might be missed later
- Provides context for better planning

**Drawbacks:**
- Adds extra API call
- Might be redundant with Phase 1
- Delay before user sees goals

---

### Strategy 2: Enhance Phase 3 - Structured Findings with Interest Fields

**Make Findings Structure More Specific**

**Approach:**
- Define structured `findings` schema
- Include dedicated fields for points of interest
- Update prompts to encourage interest extraction

**Implementation:**
```json
{
  "step_id": 1,
  "findings": {
    "main_topics": ["topic1", "topic2"],
    "key_claims": [
      {
        "claim": "claim text",
        "source_hint": "transcript/comment",
        "evidence": "supporting text"
      }
    ],
    "notable_patterns": ["pattern1", "pattern2"],
    "controversial_points": [
      {
        "issue": "controversial topic",
        "opposing_views": ["view1", "view2"]
      }
    ],
    "surprising_insights": ["insight1", "insight2"],
    "specific_examples": ["example1", "example2"],
    "unanswered_questions": ["question1", "question2"]
  },
  "insights": "...",
  "confidence": 0.8
}
```

**Benefits:**
- Structured extraction
- Easier to aggregate across steps
- Clear guidance for AI
- Better for synthesis

**Drawbacks:**
- More complex schema
- Might constrain AI creativity
- Larger JSON outputs

---

### Strategy 3: Add Dedicated Interest Extraction Steps

**Add Optional Steps in Phase 2 Plan**

**Approach:**
- Phase 2 can include "exploratory" steps
- Steps specifically for finding interesting points
- Not tied to main goal

**Implementation:**
```python
# In Phase 2 planning prompt:
"""
You may include optional exploratory steps (step_id starting at 100) 
that focus on discovering interesting points regardless of the main goal.
These steps can extract:
- General themes and patterns
- Notable quotes and examples
- Controversial topics
- Unexpected connections
"""
```

**Benefits:**
- Flexible interest discovery
- Can be goal-related or general
- Natural fit in planning flow

**Drawbacks:**
- Relies on Phase 2 AI to add these steps
- Might not be included if AI doesn't think to add them
- Less predictable

---

### Strategy 4: Post-Processing Interest Aggregation

**Extract Interests After All Steps Complete**

**Approach:**
- After Phase 3, add Phase 3.5
- Analyze all findings together
- Extract cross-cutting points of interest

**Implementation:**
```python
# New phase: Phase3_5_AggregateInterests
def execute(all_findings: List[Dict], scratchpad: Dict) -> Dict[str, Any]:
    """
    Analyze all findings to extract:
    - Recurring themes
    - Cross-source patterns
    - Most interesting discoveries
    - Unexpected connections
    """
```

**Benefits:**
- Holistic view of all content
- Finds patterns across steps
- Dedicated interest focus
- Works with existing findings

**Drawbacks:**
- Adds extra phase
- Another API call
- Might duplicate some extraction

---

### Strategy 5: Enhanced Prompting in Existing Phases

**Improve Prompts Without Structure Changes**

**Approach:**
- Update Phase 3 prompt to explicitly request interests
- Use examples of what "points of interest" means
- Encourage diverse extraction

**Implementation:**
```markdown
# In phase3_execute/instructions.md:
**分析要求:**
在分析数据块时，请特别关注并提取以下类型的兴趣点：
1. **关键论点**: 作者提出的主要观点和主张
2. **支持证据**: 用于支持论点的具体例子、数据、引用
3. **争议点**: 存在不同意见的话题
4. **意外发现**: 与预期不符或令人惊讶的洞察
5. **具体例子**: 值得引用的具体事例或引用
6. **未解问题**: 内容中提出的开放性问题

在findings中，尽可能详细地记录这些兴趣点。
```

**Benefits:**
- Minimal code changes
- Backward compatible
- Guides AI without constraining
- Works with current structure

**Drawbacks:**
- No enforcement (AI might still skip)
- Less structured output
- Harder to aggregate automatically

---

## Recommended Hybrid Approach

### Combination: Strategy 2 + Strategy 5

**Why This Combination:**
1. **Structured findings** (Strategy 2) provides clear guidance
2. **Enhanced prompting** (Strategy 5) ensures AI understands intent
3. Works within existing phase structure
4. Minimal disruption to current flow
5. Maximum extraction coverage

### Implementation Plan

#### Step 1: Define Interest Extraction Schema
```json
{
  "findings": {
    "summary": "Main analysis summary",
    "points_of_interest": {
      "key_claims": [...],
      "notable_evidence": [...],
      "controversial_topics": [...],
      "surprising_insights": [...],
      "specific_examples": [...],
      "open_questions": [...]
    },
    "analysis_details": {
      // Other step-specific findings
    }
  }
}
```

#### Step 2: Update Phase 3 Prompt
- Add explicit section on interest extraction
- Include examples
- Emphasize importance of diverse extraction

#### Step 3: Update Phase 3 Output Schema
- Make schema more specific
- Include points_of_interest structure
- Keep backward compatible (optional fields)

#### Step 4: Update Phase 2 Prompt
- Suggest including interest-extraction steps
- Mention different types of interests
- Encourage diverse analysis angles

#### Step 5: Update Phase 4 Prompt
- Encourage highlighting interesting points
- Include "Key Discoveries" section
- Reference points_of_interest from findings

---

## Detailed Implementation Specification

### Phase 3 Output Schema (Enhanced)
```json
{
  "type": "object",
  "properties": {
    "step_id": { "type": "integer" },
    "findings": {
      "type": "object",
      "properties": {
        "summary": { 
          "type": "string",
          "description": "Main analysis summary for this step"
        },
        "points_of_interest": {
          "type": "object",
          "properties": {
            "key_claims": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "claim": { "type": "string" },
                  "supporting_evidence": { "type": "string" },
                  "relevance": { "type": "string", "enum": ["high", "medium", "low"] }
                }
              }
            },
            "notable_evidence": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "evidence_type": { "type": "string", "enum": ["example", "data", "quote", "anecdote"] },
                  "description": { "type": "string" },
                  "quote": { "type": "string" }
                }
              }
            },
            "controversial_topics": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "topic": { "type": "string" },
                  "opposing_views": { "type": "array", "items": { "type": "string" } },
                  "intensity": { "type": "string", "enum": ["high", "medium", "low"] }
                }
              }
            },
            "surprising_insights": {
              "type": "array",
              "items": { "type": "string" }
            },
            "specific_examples": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "example": { "type": "string" },
                  "context": { "type": "string" },
                  "source_indicator": { "type": "string" }
                }
              }
            },
            "open_questions": {
              "type": "array",
              "items": { "type": "string" }
            }
          },
          "description": "Structured points of interest extracted from this analysis"
        },
        "analysis_details": {
          "type": "object",
          "description": "Step-specific detailed analysis (flexible structure)"
        }
      },
      "required": ["summary"]
    },
    "insights": { "type": "string" },
    "confidence": { "type": "number" }
  },
  "required": ["step_id", "findings", "insights", "confidence"]
}
```

### Phase 3 Prompt Enhancement
```markdown
**兴趣点提取要求:**

在分析数据块时，除了完成步骤目标，请主动提取以下类型的兴趣点：

1. **关键论点 (Key Claims)**: 
   - 作者/发言者的主要观点
   - 核心主张和立场
   - 支持这些论点的证据

2. **具体证据 (Notable Evidence)**:
   - 值得引用的数据、统计数字
   - 生动的例子和案例
   - 权威性引用或名言

3. **争议话题 (Controversial Topics)**:
   - 存在明显分歧的话题
   - 评论区中的激烈讨论点
   - 对立观点的对比

4. **意外洞察 (Surprising Insights)**:
   - 与常识相悖的发现
   - 新颖的角度或观点
   - 意料之外的结论

5. **具体例子 (Specific Examples)**:
   - 可引用的具体事例
   - 生动的描述或故事
   - 重要的名称、日期、地点

6. **开放问题 (Open Questions)**:
   - 内容中提出的未解答问题
   - 值得进一步研究的方向
   - 讨论中遗留的疑问

**请在findings中创建"points_of_interest"对象，尽可能详细地记录这些内容。**
```

### Phase 2 Prompt Enhancement
```markdown
**可选探索步骤:**

在创建研究计划时，可以考虑添加探索性步骤（step_id > 10），专门用于：

- 广泛提取兴趣点（不限于主目标）
- 识别跨来源的模式
- 发现意外连接
- 收集值得注意的引述和例子

这些步骤可以帮助发现主目标之外的有价值见解。
```

### Phase 4 Prompt Enhancement
```markdown
**报告结构建议:**

除了常规章节，请考虑添加：

## 关键发现与兴趣点

基于所有步骤中提取的points_of_interest，总结：
- 最突出的论点
- 最有力的证据
- 最争议的话题
- 最意外的洞察
- 值得引用的例子
- 开放的研究问题

每个兴趣点应注明来源（根据发现中的来源信息）。
```

---

## Expected Outcomes

### Quantitative Improvements:
- **Before**: ~3-5 interest points per analysis step
- **After**: ~10-20 structured interest points per step
- **Coverage**: Multiple interest types (claims, evidence, controversies, etc.)
- **Aggregation**: Easier to collect and synthesize interests across steps

### Qualitative Improvements:
- More structured extraction
- Diverse interest types captured
- Better traceability (sources attached)
- Rich synthesis material for reports

---

## Implementation Complexity

### Low Complexity (Quick Win):
- ✅ Update Phase 3 prompt (5 min)
- ✅ Add interest extraction guidance (10 min)
- ✅ Update Phase 4 prompt to highlight interests (5 min)

### Medium Complexity:
- Update Phase 3 output schema (30 min)
- Update validation logic (20 min)
- Test with sample data (30 min)

### High Complexity (Optional):
- Add Phase 3.5 interest aggregation (2-3 hours)
- Update UI to display interests (1-2 hours)
- Add interest filtering/search (2-3 hours)

---

## Testing Strategy

1. **Test with diverse content:**
   - Long transcripts (10K+ words)
   - Multiple sources
   - Content with clear controversies
   - Content with data/statistics

2. **Validate extraction quality:**
   - Are all interest types captured?
   - Are sources properly attributed?
   - Are examples specific enough?
   - Are insights truly surprising?

3. **Compare before/after:**
   - Count interest points per step
   - Analyze diversity of types
   - Check synthesis quality improvement

---

## Recommended Implementation Order

### Phase 1: Quick Wins (1 hour)
1. Update Phase 3 prompt with interest extraction guidance
2. Update Phase 4 prompt to highlight interests section
3. Test with one sample research run

### Phase 2: Structured Schema (2 hours)
1. Design and update Phase 3 output schema
2. Update validation logic
3. Test schema with API responses

### Phase 3: Integration (1 hour)
1. Update Phase 2 prompt to suggest exploration steps
2. Update Phase 4 to aggregate interests
3. Full end-to-end test

### Phase 4: Enhancement (Optional, 3-4 hours)
1. Add Phase 3.5 interest aggregation
2. Update UI components
3. Add interest filtering capabilities

---

## Risk Assessment

### Low Risk:
- Prompt updates (backward compatible)
- Schema additions (optional fields)
- No breaking changes

### Medium Risk:
- AI might not follow new structure consistently
- Response parsing might need updates
- Validation needs to handle optional fields

### Mitigation:
- Keep new fields optional initially
- Add fallback handling
- Test extensively before full deployment

---

## Conclusion

**Best Approach**: Hybrid Strategy 2 + Strategy 5
- Provides structure without being too rigid
- Enhances prompts for better extraction
- Maintains backward compatibility
- Achieves maximum interest extraction coverage

**Implementation Priority**: 
1. Prompt enhancements (quick win)
2. Schema updates (structured output)
3. Optional aggregation phase (future enhancement)

This approach will significantly increase the variety and depth of points of interest extracted while working within the current system architecture.

