# Prompt Improvement Implementation Guide

This document provides a step-by-step guide for implementing the prompt improvements. Each phase includes specific file changes with before/after snippets.

---

## 🚀 Quick Start - Priority Order

If you can only make a few changes, do these first for maximum impact:

1. **Phase 3 Simplification** - Biggest complexity reduction (132→50 lines)
2. **User Context Reordering** - Put user first in all phases
3. **Remove Role Rigidity** - Make Phase 0.5 advisory or remove
4. **Phase 4 Flexible Structure** - Remove mandatory outline requirements

---

## 📋 Implementation Phases

### Phase 1: Quick Wins (Week 1) - No Logic Changes

**Estimated effort:** 4-6 hours  
**Impact:** 30% complexity reduction

#### 1.1 Consolidate Language Instructions

**Files to modify:**
- All `instructions.md` files in each phase

**Current problem:** Each phase has 15-20 lines explaining Chinese language requirements

**Action:** 
1. Add to system-level configuration or each `system.md`:
```markdown
**语言说明:** 所有输出使用中文。引用非中文来源时，提供中文译文并用括号标注原文（例如："深度学习(deep learning)"）。
```

2. Remove language sections from all `instructions.md` files:
- `phase1_discover/instructions.md` (if present)
- `phase2_plan/instructions.md` (if present)
- `phase3_execute/instructions.md` (lines 34-51, ~17 lines)
- `phase4_synthesize/instructions.md` (if present)

**Lines saved:** ~40 lines across all phases

---

#### 1.2 Simplify Anti-Repetition System

**Files to modify:**
- `phase3_execute/instructions.md`

**Current problem:** Multiple overlapping systems for preventing repetition:
- `**禁止重复的内容**` section
- `**避免重复的特别指示**` section
- `novelty_guidance` variable
- Complex JSON fields tracking this

**Action:**
Replace lines 7-32 (26 lines) with:
```markdown
**已分析过的内容（避免重复）:**
{cumulative_digest}

分析时专注于新的洞察和未覆盖的角度。
```

**Lines saved:** ~20 lines

---

#### 1.3 Reorder All Prompts: User First

**Files to modify:** All `instructions.md` files

**Principle:** User context should always be the first substantive content the AI sees

**Template for all phases:**
```markdown
**用户的研究问题/主题:**
{user_topic}

**用户的具体关注点和优先事项:**
{user_guidance}

---

**[Current Phase Task]:**
...

---

**可用资源/数据:**
...

---

**任务指导:**
...
```

**Specific changes:**

**Phase 1 Discover (`phase1_discover/instructions.md`):**
- Move `{user_topic}` from line 10 to line 1
- Move `{user_guidance}` from context to line 3
- Move `{marker_overview}` down
- Result: User context is first thing AI sees

**Phase 2 Plan (`phase2_plan/instructions.md`):**
- Move synthesized goal to top
- Add user_guidance prominently
- Move marker_overview down

**Phase 3 Execute (`phase3_execute/instructions.md`):**
- Move user guidance from line 13 to line 1-5
- Move goal description to line 7
- Move retrieved_content down
- Result: User → Goal → Resources

**Phase 4 Synthesize (`phase4_synthesize/instructions.md`):**
- Already has `selected_goal` at top, but emphasize user_guidance more

**Impact:** Fundamental shift in AI's attention priority

---

#### 1.4 Simplify Role System

**Option A: Make Advisory (Recommended)**

**Files to modify:**
- `phase0_5_role_generation/system.md`
- `phase0_5_role_generation/instructions.md`
- All phase `system.md` files

**Current:** "你是{system_role_description}" - prescriptive role assignment

**Change to:**
```markdown
# phase0_5_role_generation/system.md
你是研究助理，帮助用户探索他们的话题。

根据可用数据和用户问题，考虑什么专业知识或视角对分析最有价值。
你不需要严格采用单一角色 - 根据需要灵活运用相关专业知识。

目标是提供直接满足用户需求的洞察，而不是完美体现某个专业角色。
```

```markdown
# phase0_5_role_generation/instructions.md
**用户的研究主题:**
{user_topic}

**用户的具体说明:**
{user_guidance}

**可用数据概览:**
{data_abstract}

**任务:**
基于用户问题和可用数据，建议一个或多个可能有用的研究视角或专业领域。

这是建议性的 - 后续研究过程中可以灵活调整视角。

**输出格式:**
{
  "suggested_perspectives": [
    "视角1: 简要说明为什么有用",
    "视角2: 简要说明为什么有用"
  ],
  "rationale": "为什么这些视角适合用户的问题"
}
```

**All other phase system.md files:**
Change from:
```markdown
你是{system_role_description}。你的任务是...
```

To:
```markdown
你是研究助理。{research_role_rationale}

你的任务是...
```

**Option B: Remove Entirely (More Aggressive)**

Delete `phase0_5_role_generation/` entirely and remove role references from all phases.

**Recommendation:** Start with Option A, test, then consider Option B if role isn't adding value

---

### Phase 2: Core Simplification (Week 2) - Major Changes

**Estimated effort:** 12-16 hours  
**Impact:** 50% complexity reduction

#### 2.1 Phase 3 Execute - Major Overhaul

**File:** `research/prompts/phase3_execute/instructions.md`

**Current:** 132 lines, highly complex  
**Target:** ~50 lines, focused

**Complete rewrite recommended.** New structure:

```markdown
**用户想要理解:**
{selected_goal}

**用户特别关心:**
{user_guidance_context}

---

**当前步骤目标:**
{goal}

---

**可用内容:**
{retrieved_content}

**之前发现的内容（避免重复）:**
{previous_chunks_context}

---

**你的任务:**
分析内容，提供有助于回答用户问题的洞察。

**分析重点:**
- 直接相关于用户的核心问题
- 新的洞察（避免重复上述已有发现）
- 基于证据的推理
- 用清晰、自然的中文表达

**分析方法:**
采用任何对回答问题有帮助的分析方法：
- 比较不同来源的观点
- 深入探讨因果关系
- 识别模式和趋势
- 发现矛盾和空白
- 提出假设和验证

让问题引导分析方法，而不是遵循固定框架。

**检索能力:**
如果需要更多内容才能完成分析，可以请求：
- 特定内容项的完整内容
- 与特定话题相关的内容
- 基于关键词或问题的语义搜索

在 `content_requests` 字段中说明需要什么以及为什么需要。

---

**输出格式:**

{
  "content_requests": [
    // 如果需要更多内容，在这里说明
    {
      "what": "需要什么内容",
      "why": "为什么需要",
      "priority": "high/medium/low"
    }
  ],
  "key_findings": [
    {
      "insight": "你发现了什么（用户能理解的语言）",
      "evidence": "支持这个发现的证据（引用具体内容）",
      "relevance": "这对回答用户问题为什么重要"
    }
  ],
  "deeper_analysis": "深入分析和推理（自由形式文字，充分展开）",
  "connections": "与之前发现或更大背景的联系",
  "open_questions": ["还有什么不清楚或需要进一步探索的？"],
  "confidence": 0.0
}

**注意:** 
- 所有输出使用中文
- 引用非中文来源时提供译文并标注原文
- key_findings 应该是明确的、独立的洞察（每个都能单独理解）
- deeper_analysis 是你深入思考和解释的地方，可以自由展开
```

**What to remove:**
- ❌ Lines 7-32: Redundant anti-repetition sections → Keep only cumulative_digest
- ❌ Lines 9-11: Research role section → Already in system.md
- ❌ Lines 24-32: Complex article requirement → Simplified to analysis field
- ❌ Lines 34-51: Language requirements → Now 2 lines in notes
- ❌ Lines 45-61: Detailed retrieval explanations → Simplified summary
- ❌ Lines 62-67: Prescribed methodology (5 Whys) → Flexible guidance
- ❌ Lines 70-130: Complex nested JSON → Simplified to 6 fields

**Result:** 132 lines → ~50 lines (62% reduction)

---

#### 2.2 Phase 2 Plan - Simplification

**File:** `research/prompts/phase2_plan/instructions.md`

**Current:** 74 lines with complex requirements  
**Target:** ~30 lines

**New version:**

```markdown
**用户想要理解:**
{selected_goal}

**用户的优先关注:**
{user_guidance}

**具体要探索的问题:**
{component_questions}

---

**可用资料:**
{marker_overview}

**之前的研究目标:**
{suggested_goals_list}

---

**你的任务:**
制定一个简单、清晰的研究计划来回答用户的问题。

**思考:**
1. 要回答用户的问题，首先需要了解什么？
2. 然后需要什么样的分析？
3. 最后需要综合什么？
4. 什么样的顺序最合理？

**创建3-7个研究步骤**

每个步骤应该:
- 有明确的目的，与用户问题相关
- 说明需要什么类型的资料
- 在逻辑上承接前面的步骤
- 最终有助于回答用户的核心问题

不需要规定具体的分析方法或技术细节 - 相信执行时你会知道如何有效分析。
专注于**发现什么**，而不是**如何发现**。

---

**输出格式:**

{
  "research_plan": [
    {
      "step_id": 1,
      "goal": "这一步要发现/理解什么",
      "needed_data": "transcript / transcript_with_comments / metadata / previous_findings",
      "purpose": "为什么这对回答用户问题很重要",
      "notes": "任何特殊考虑或与其他步骤的关系（可选）"
    }
  ]
}

**提示:**
- 不要创建太多步骤（3-7个足够）
- 每个步骤都应该产生有价值的洞察，不只是收集信息
- 考虑步骤之间的逻辑依赖（第2步应该建立在第1步的基础上）
- 最后的步骤应该能综合形成对用户问题的完整回答
```

**What to remove:**
- ❌ Lines 14-24: Detailed marker explanations → Brief mention
- ❌ Lines 37-43: Design philosophy section → Removed (trust AI)
- ❌ Lines 28-36: Complex JSON field requirements → Simplified to 5 fields
- ❌ Lines 45-74: Detailed example → Simple format description

**Result:** 74 lines → ~30 lines (60% reduction)

---

#### 2.3 Phase 1 Discover - User-Centric Refocus

**File:** `research/prompts/phase1_discover/instructions.md`

**Current:** 47 lines, marker-centric  
**Target:** ~20 lines, user-centric

**New version:**

```markdown
**用户想了解:**
{user_topic}

**用户的具体关注点:**
{user_guidance}

---

**可用的研究资料概览:**
{marker_overview}

**研究角色建议:**
{research_role_display}

---

**你的任务:**
提出7-10个具体的研究目标，直接回应用户的问题。

**思考过程:**
1. 用户真正想知道什么？
2. 什么样的发现对用户最有价值或最有趣？
3. 基于可用资料，什么是可以回答的？
4. 什么样的洞察会让用户觉得"这正是我想知道的！"？

**研究目标要求:**
- 清楚地与用户问题相关（不是为了研究而研究）
- 能用现有资料回答（检查资料概览）
- 提供真正的洞察（不只是描述事实）
- 用用户能理解的语言表达（不用专业术语除非必要）
- 互不重复，各有侧重

**可选约束:**
{avoid_list}

---

**输出格式:**

{
  "suggested_goals": [
    {
      "id": 1,
      "goal_text": "具体的研究目标（一句话）",
      "rationale": "为什么这能回答用户的问题，为什么用户会关心",
      "uses": ["transcript / transcript_with_comments / metadata"],
      "sources": ["youtube / bilibili / reddit / article 等"]
    }
  ]
}

根据资料的丰富程度和用户问题的复杂度，生成7-10个高质量目标。
质量比数量更重要。
```

**What to remove:**
- ❌ Lines 1-6: System role emphasis → Brief mention, user first
- ❌ Lines 13-22: Detailed marker analysis instructions → Brief mention
- ❌ Lines 23-27: Marker-centric thinking → User-centric thinking
- ❌ Lines 34-47: Complex JSON schema requirements → Simplified

**Result:** 47 lines → ~20 lines (57% reduction)

---

### Phase 3: Structural Changes (Week 3) - Architecture Changes

**Estimated effort:** 16-20 hours  
**Impact:** Remove rigid templates, enable natural outputs

#### 3.1 Phase 4 - Remove Separate Outline Generation

**Current:** Two-step process:
1. `outline.md` (49 lines) - Generate outline JSON
2. `instructions.md` (58 lines) - Write report following outline

**Proposed:** Single-step process:
- Combine into `instructions.md` (~40 lines)
- Remove `outline.md`
- Remove rigid structure requirements

**New `phase4_synthesize/instructions.md`:**

```markdown
你是研究助理。{research_role_rationale}

**用户的原始问题:**
{selected_goal}

**用户最关心的方面:**
{user_guidance}

---

**研究发现:**
{phase3_summary}

**Phase 3 步骤摘要:**
{phase3_step_synopsis}

**关键论点和证据:**
{phase3_key_claims}

**可用证据目录:**
{evidence_catalog}

**结构化发现详情:**
{scratchpad_digest}

---

**你的任务:**
写一份全面的研究报告来回答用户的问题。

## 报告结构（灵活）

你的报告应该包含以下部分，但具体组织方式应该适合你的发现：

**1. 核心发现概述**
- 用2-4个要点总结最重要的答案
- 回答用户最关心的问题
- 提供关键结论

**2. 主要分析**（按最合理的方式组织）

不要强行套用固定结构。根据你的发现，选择最自然的组织方式：

可能的组织方式：
- **按主题分组**: 如果有多个独立的话题
- **按时间顺序**: 如果展现演变过程很重要
- **按因果关系**: 如果解释原因和结果是重点
- **按问题-发现-影响**: 如果适合问题导向的探索
- **按对比观点**: 如果存在不同视角需要比较
- **混合方式**: 根据不同部分的特点灵活选择

无论选择什么结构：
- 每个章节都应该有明确的目的
- 章节之间应该有逻辑联系
- 所有分析都应该支持回答用户的问题
- 用 [EVID-##] 引用证据目录中的证据

**3. 局限与未解问题**
- 什么问题没能完全回答？
- 证据在哪些方面不足？
- 什么需要进一步研究？

**4. 证据索引**
列出报告中使用的证据及其来源

---

## 写作指导

**核心原则: 对用户有用**

写作时不断问自己：
- 这回答了用户想知道的吗？
- 用户读到这里会觉得有价值吗？
- 这是用户能理解的语言吗？

**具体要求:**

1. **清晰直接**: 用自然的中文，避免不必要的专业术语
2. **基于证据**: 重要观点用 [EVID-##] 支持
3. **有洞察**: 不只是总结信息，要分析、联系、解释
4. **诚实**: 如果证据有限或存在不确定性，明确说明
5. **结构服务内容**: 让发现决定结构，而不是强行套用模板

**不要做的事:**
- ❌ 不要强行套用预设的大纲
- ❌ 不要写成学术论文格式（除非用户想要）
- ❌ 不要用不相关的章节填充报告
- ❌ 不要让格式要求胜过内容实质
- ❌ 不要回避承认局限性

---

## 覆盖检查

确保报告回答了以下问题（如果相关）:
{component_questions_text}

如果某些问题无法充分回答，在"局限与未解问题"部分说明原因。

---

**输出: 纯 Markdown 格式的报告，无 JSON 包装。**
```

**Files to change:**
1. **Delete:** `phase4_synthesize/outline.md` (49 lines)
2. **Replace:** `phase4_synthesize/instructions.md` (58 lines → 40 lines)
3. **Update:** Backend code that calls outline generation (if separate call exists)

**Backend code changes:**
Look for code that:
1. Calls outline generation
2. Then calls report writing with outline as input

Change to:
1. Single call to report writing
2. Pass all context directly

**Result:** 107 lines → 40 lines (63% reduction), more flexible outputs

---

#### 3.2 Phase 1.5 & 2.5 Synthesize - Simplification

**Files:** 
- `phase1_synthesize/instructions.md`
- `phase2_synthesize/instructions.md`

**Current issues:**
- Rigid format requirements (20-character limit)
- Prescribed component_questions structure
- Over-specification

**Changes for both:**

```markdown
**研究目标 (共{goals_count}个):**
{goals_list}

**用户的问题和关注点:**
{user_topic}
{user_guidance}

**可用数据:**
{data_abstract}

---

**你的任务:**
将这些研究目标综合成一个统一的研究主题。

这个综合主题应该:
1. **清晰简洁**: 用用户能理解的语言（不是学术术语）
2. **覆盖所有目标**: 能够涵盖所有研究问题的核心
3. **保持可行性**: 仍然可以在一份研究报告中充分探讨
4. **尊重用户意图**: 反映用户想要了解的内容

---

**输出格式:**

{
  "synthesized_goal": {
    "comprehensive_topic": "统一的研究主题（简洁表述）",
    "unifying_theme": "将所有问题联系在一起的核心主题",
    "research_scope": "研究的范围和重点"
  }
}

**注意:** 
- 原始研究问题会被系统自动保留，你不需要重新生成它们
- 综合主题不需要严格限制字数 - 清晰比简短更重要
- 用用户的语言，不要使用不必要的学术术语
```

**What to remove:**
- ❌ Rigid 20-character limit
- ❌ Component_questions reformatting (system preserves originals)
- ❌ Over-prescription of format

**Result:** ~35 lines → ~20 lines (43% reduction)

---

### Phase 4: Testing & Validation (Week 4)

**Estimated effort:** 12-16 hours

#### 4.1 Create Test Suite

**Create:** `tests/prompt_improvements/test_cases.yaml`

```yaml
test_cases:
  - name: "Technical Product Question"
    user_topic: "分析 GPT-4 和 Claude 3 在代码生成任务上的表现差异"
    user_guidance: "我特别关心实际使用中的差异，不只是benchmark分数"
    expected_outcomes:
      - Focuses on practical differences
      - Cites specific examples
      - Addresses user's skepticism about benchmarks
    
  - name: "Broad Exploratory Question"
    user_topic: "了解远程工作对员工生产力的影响"
    user_guidance: "我在考虑是否让团队永久远程，需要全面了解利弊"
    expected_outcomes:
      - Balanced perspective (pros and cons)
      - Addresses decision-making context
      - Practical insights for management
  
  - name: "Specific Niche Question"
    user_topic: "为什么 Rust 在游戏开发中的采用率不高？"
    user_guidance: "我知道性能很好，想了解实际障碍是什么"
    expected_outcomes:
      - Goes beyond obvious answers (performance)
      - Identifies specific barriers
      - Based on user's stated prior knowledge
  
  # Add 5-10 more diverse test cases
```

#### 4.2 A/B Testing Protocol

**For each test case:**

1. **Run both versions**:
   - Old prompts (current system)
   - New prompts (improved system)

2. **Collect outputs**:
   - Phase 1 goals
   - Phase 2 plan
   - Phase 3 findings
   - Phase 4 final report

3. **Evaluate on metrics**:
   - **Relevance**: How well does it address user's actual question? (1-5)
   - **User Intent Alignment**: Does it prioritize what user cares about? (1-5)
   - **Naturalness**: Does output feel natural vs. templated? (1-5)
   - **Insight Quality**: Does it provide genuine insights? (1-5)
   - **Usability**: Would this be useful to the user? (1-5)

4. **Blind review**:
   - Have reviewers evaluate outputs without knowing which system produced them
   - Aggregate scores

#### 4.3 Regression Testing

**Check for:**
- JSON parsing errors (should be fewer with simpler schemas)
- Missing required fields (update parsers for new simplified schemas)
- System crashes or failures
- Evidence citation functionality still works
- Cross-phase data passing still works

**Files to update:**
- Backend parsing code for new JSON schemas
- Phase transition logic if removing outline generation
- Any validation that checks for removed fields

#### 4.4 User Feedback

**If possible, get real user feedback:**

1. **User survey** (for both old and new versions):
   - "Did this answer your question?" (Yes/Somewhat/No)
   - "How relevant were the findings?" (1-5)
   - "How natural did the report feel?" (1-5)
   - "Would you use this tool again?" (Yes/No)

2. **Qualitative feedback**:
   - "What did you like?"
   - "What was missing?"
   - "What would you change?"

3. **Preference test**:
   - Show user two reports (old vs new, blinded)
   - "Which better answers your question?"
   - "Which would you rather read?"

---

## 🔧 Technical Implementation Details

### Updating JSON Schemas

**Current schemas** (`output_schema.json` files) are complex. Need to update both:
1. The JSON schema files
2. Backend code that parses these schemas

**Example: Phase 3 Schema Simplification**

**Before** (`phase3_execute/output_schema.json`):
```json
{
  "type": "object",
  "properties": {
    "step_id": {"type": "integer"},
    "requests": {"type": "array"},
    "missing_context": {"type": "array"},
    "findings": {
      "type": "object",
      "properties": {
        "summary": {"type": "string"},
        "article": {"type": "string"},
        "points_of_interest": {
          "type": "object",
          "properties": {
            "key_claims": {"type": "array"},
            "notable_evidence": {"type": "array"},
            "controversial_topics": {"type": "array"},
            "surprising_insights": {"type": "array"},
            "specific_examples": {"type": "array"},
            "open_questions": {"type": "array"}
          }
        },
        "analysis_details": {
          "type": "object",
          "properties": {
            "five_whys": {"type": "array"},
            "assumptions": {"type": "array"},
            "uncertainties": {"type": "array"}
          }
        }
      },
      "required": ["summary", "article", "points_of_interest", "analysis_details"]
    },
    "insights": {"type": "string"},
    "confidence": {"type": "number"}
  },
  "required": ["step_id", "findings", "insights", "confidence"]
}
```

**After**:
```json
{
  "type": "object",
  "properties": {
    "step_id": {"type": "integer"},
    "content_requests": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "what": {"type": "string"},
          "why": {"type": "string"},
          "priority": {"type": "string", "enum": ["high", "medium", "low"]}
        }
      }
    },
    "key_findings": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "insight": {"type": "string"},
          "evidence": {"type": "string"},
          "relevance": {"type": "string"}
        },
        "required": ["insight", "evidence"]
      }
    },
    "deeper_analysis": {"type": "string"},
    "connections": {"type": "string"},
    "open_questions": {
      "type": "array",
      "items": {"type": "string"}
    },
    "confidence": {"type": "number", "minimum": 0, "maximum": 1}
  },
  "required": ["key_findings", "deeper_analysis"]
}
```

**Backend code updates needed:**
Look for code that accesses:
- `result['findings']['article']` → Remove or use `result['deeper_analysis']`
- `result['findings']['points_of_interest']['key_claims']` → Change to `result['key_findings']`
- `result['findings']['analysis_details']['five_whys']` → Remove (no longer required)

### Handling Backward Compatibility

**Strategy:**
1. **Version the prompts**: Keep old prompts in `prompts_v1/`, new in `prompts_v2/`
2. **Feature flag**: Add config option to use old or new prompts
3. **Gradual migration**: Run both systems in parallel during testing
4. **Schema adapters**: Write adapters to convert new format to old format if needed

**Config example:**
```yaml
# config.yaml
research:
  prompt_version: "v2"  # or "v1" for old system
  # ... other config
```

**Code example:**
```python
def load_prompts():
    version = config['research']['prompt_version']
    base_path = f"research/prompts_{version}/"
    # Load from appropriate directory
    return load_from_path(base_path)
```

---

## 📊 Success Metrics & Monitoring

### Quantitative Metrics

Track these for old vs. new system:

1. **Response Quality**:
   - Average relevance score (1-5)
   - Average insight quality score (1-5)
   - Naturalness score (1-5)

2. **Technical Performance**:
   - JSON parsing errors (should decrease)
   - Average token usage (may decrease with shorter prompts)
   - Average time per phase

3. **User Satisfaction**:
   - "Answered my question" rate
   - Preference rate (when shown both outputs)
   - Return usage rate

### Qualitative Assessment

For 20-30 test cases, manually assess:

**Before → After comparisons:**
- Does new version better address user intent?
- Is output more relevant?
- Is output more natural (less templated)?
- Are insights more meaningful?

**Document examples of:**
- ✅ Clear improvements
- ⚠️ Regressions or issues
- 🤔 Unclear/mixed results

---

## 🚨 Rollback Plan

**If new prompts cause problems:**

1. **Immediate rollback**:
   ```yaml
   # config.yaml
   research:
     prompt_version: "v1"  # Switch back to old prompts
   ```

2. **Identify issues**:
   - Which phases are problematic?
   - What specific outputs are worse?
   - Are issues with prompts or with schema changes?

3. **Partial rollback**:
   - Can roll back individual phases
   - e.g., Keep new Phase 1 & 2, revert Phase 3 & 4

4. **Iterate**:
   - Fix identified issues
   - Test again before re-deploying

---

## 📝 Checklist

### Before Starting
- [ ] Backup current prompts directory
- [ ] Create `prompts_v2/` directory
- [ ] Set up A/B testing infrastructure
- [ ] Create test cases document
- [ ] Document current system metrics (baseline)

### Phase 1: Quick Wins
- [ ] Consolidate language instructions across all phases
- [ ] Simplify anti-repetition system in Phase 3
- [ ] Reorder all prompts to put user first
- [ ] Make role system advisory (or remove)
- [ ] Update backend code for role changes
- [ ] Test that system still works
- [ ] Run regression tests

### Phase 2: Core Simplification
- [ ] Rewrite Phase 3 instructions (132 → 50 lines)
- [ ] Update Phase 3 JSON schema
- [ ] Update backend parsing for Phase 3
- [ ] Simplify Phase 2 instructions (74 → 30 lines)
- [ ] Update Phase 2 JSON schema
- [ ] Update backend parsing for Phase 2
- [ ] Refocus Phase 1 instructions (47 → 20 lines)
- [ ] Update Phase 1 JSON schema
- [ ] Update backend parsing for Phase 1
- [ ] Test all phases individually
- [ ] Test end-to-end flow

### Phase 3: Structural Changes
- [ ] Remove Phase 4 outline generation
- [ ] Rewrite Phase 4 instructions (107 → 40 lines)
- [ ] Update backend to skip outline phase
- [ ] Simplify Phase 1.5 & 2.5 synthesize
- [ ] Update corresponding schemas and parsers
- [ ] Test Phase 4 with diverse inputs
- [ ] Ensure evidence citations still work
- [ ] Test final report generation

### Phase 4: Testing & Validation
- [ ] Create test suite with 10+ diverse cases
- [ ] Run A/B tests (old vs. new)
- [ ] Collect quantitative metrics
- [ ] Perform qualitative assessment
- [ ] Document improvements and regressions
- [ ] Get user feedback (if possible)
- [ ] Make final adjustments based on feedback
- [ ] Update documentation

### Deployment
- [ ] Review all changes one final time
- [ ] Update user-facing documentation
- [ ] Deploy with feature flag enabled
- [ ] Monitor for errors
- [ ] Collect feedback
- [ ] Switch fully to new prompts (or rollback if needed)

---

## 🎯 Expected Timeline

| Week | Phase | Key Deliverables | Hours |
|------|-------|------------------|-------|
| **Week 1** | Quick Wins | Reordered prompts, simplified role, consolidated instructions | 4-6 |
| **Week 2** | Core Simplification | Phases 1-3 rewritten and tested | 12-16 |
| **Week 3** | Structural Changes | Phase 4 flexible, synthesize simplified | 16-20 |
| **Week 4** | Testing & Validation | A/B tests, user feedback, final adjustments | 12-16 |
| **Total** | | | **44-58 hours** |

**Recommendation:** 
- Full-time: Complete in 1-2 weeks
- Part-time: Complete in 3-4 weeks
- Can be done in stages with testing between each

---

## 📞 Getting Help

If you encounter issues during implementation:

1. **Prompt Wording**: Test with GPT-4 or Claude to validate prompt clarity
2. **JSON Schema**: Use online validators to check schema syntax
3. **Backend Integration**: Write unit tests for parsers before integration
4. **A/B Testing**: Start with small sample, expand if results are promising

---

**Next Step:** Start with Phase 1 (Quick Wins) to validate the approach with minimal risk.

*Document Version: 1.0*  
*Last Updated: 2025-11-12*

