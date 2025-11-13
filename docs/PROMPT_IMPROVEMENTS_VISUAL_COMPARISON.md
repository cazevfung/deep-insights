# Visual Comparison: Prompt Improvements

This document provides side-by-side comparisons of current vs. proposed prompts to illustrate the improvements.

---

## 🎯 Core Philosophy Change

### BEFORE: System-Centric
```
System Architecture → Data Structures → Methodology → User Question
```

### AFTER: User-Centric
```
User Question → User Priorities → Task → Available Resources → Guidance
```

---

## 📊 Phase-by-Phase Comparisons

### Phase 0.5: Role Generation

#### BEFORE (30 lines)
```markdown
你是{system_role_description}。你的任务是分析提供的数据摘要和研究主题，
确定最适合进行深度研究的分析角色或视角。

一个好的研究角色应该：
1. 与研究主题密切相关
2. 适合分析可用的数据类型
3. 能够提供独特的分析视角
4. 有助于产生有价值的洞察

**数据摘要：**
{data_abstract}

{user_topic}

{user_guidance}

**任务：**
基于提供的数据摘要和研究主题，确定一个最合适的分析角色。这个角色应该：
- 与研究主题高度相关
- 适合分析可用的数据类型（转录文本、评论、文章等）
- 能够提供专业、深入的视角
- 有助于生成高质量的研究目标和分析

角色应该是具体、专业的，例如：
- "市场研究与用户行为分析师"
- "技术产品分析师"
[etc...]
```

**Issues:**
- Creates a fixed role that locks the AI into a persona
- Role selection based on data, not user needs
- Forces professional persona that may not fit user's context

#### AFTER (10 lines) - OR REMOVE ENTIRELY
```markdown
You're helping the user research: {user_topic}

{user_guidance}

Consider what expertise would be most helpful for this question.
You don't need to adopt a fixed professional role - just draw on 
relevant knowledge as needed.

Focus on being useful to the user, not on embodying a persona.

Available data: {data_abstract}
```

**Improvements:**
- ✅ Advisory rather than prescriptive
- ✅ User context first
- ✅ Flexibility to adapt
- ✅ 70% shorter

---

### Phase 1: Discover

#### BEFORE (45+ lines, heavy structure)
```markdown
你是{system_role_description}。你的任务是快速分析提供的资料摘要，
并针对用户提出的研究主题，提出多个不同的、有洞察力且可执行的研究目标。

你是一名深度研究助理，将以指定的研究角色开展工作。

**研究角色:** {research_role_display}
{research_role_rationale}

**可用内容标记概览:**
{marker_overview}

{user_topic}

**任务:**
基于上述标记概览，这些标记代表了所有可用内容项中的关键信息点。
每个标记对应：
- 关键事实：具体的事实性陈述
- 关键观点：观点、论证、解释
- 关键数据点：统计数据、数字、指标

请分析这些标记，识别：
1. 哪些研究目标可以充分利用这些标记中体现的信息？
2. 哪些话题领域有足够的信息支持深入研究？
3. 哪些内容项的组合对特定研究目标最有价值？

基于标记概览生成尽可能多的、高价值、互不重叠且可执行的研究目标
[... more instructions ...]
```

**Issues:**
- ❌ System role and markers dominate
- ❌ User topic buried in the middle
- ❌ Focus on system constructs (markers) rather than user question
- ❌ Over-emphasis on data structure

#### AFTER (~20 lines, user-focused)
```markdown
**用户想了解:**
{user_topic}

**用户的具体关注点:**
{user_guidance}

---

**可用的研究资料:**
{data_overview}

---

**你的任务:**
提出5-10个具体的研究目标，直接回应用户的问题。

思考:
- 用户真正想知道什么？
- 什么样的发现对用户最有价值？
- 什么样的洞察会让用户感到"这正是我想知道的！"？

然后检查可用资料，判断哪些目标是可行的。

每个目标应该:
- 清楚地与用户问题相关
- 能用现有资料回答
- 提供真正的洞察（不只是描述事实）
- 用用户能理解的语言表达

**输出格式:**
{
  "goals": [
    {
      "goal": "具体目标",
      "why_relevant": "为什么这能回答用户的问题",
      "feasibility": "基于现有资料的可行性"
    }
  ]
}
```

**Improvements:**
- ✅ User question is the FIRST thing the AI sees
- ✅ Reframed from "analyze markers" to "answer user's question"
- ✅ Simpler, more intuitive mental model
- ✅ Emphasis on relevance and usefulness
- ✅ 55% shorter

---

### Phase 2: Planning

#### BEFORE (74 lines, highly structured)
```markdown
你是{system_role_description}。你的任务是为特定的研究目标创建一个
详细、可执行、逐步的计划，并使用结构化JSON响应。

**上下文（输入）:**

**原始研究目标（来自Phase 1）：**
{suggested_goals_list}

**综合研究主题（来自Phase 1.5）：**
{synthesized_goal_context}

**可用数据:** 转录本/文章、评论、元数据

**相关内容的标记概览:**
{marker_overview}

**任务（简化计划）:**
基于选定的研究目标和标记概览，制定一个精炼、可执行的研究计划。

**标记说明:**
- 每个标记对应内容项中的具体信息点
- 你可以通过标记快速判断哪些内容项对每个研究步骤最有价值
- 在研究计划中，请明确指定：
  * 每个步骤需要哪些内容项 (link_id)
  * 需要哪些类型的标记信息 (facts/opinions/datapoints)
  * 是否需要完整的转录/评论内容，还是仅需标记已足够

聚焦于实现目标所需的最小充分步骤。强调灵活性与证据驱动，
不做过度模板化设计。

请输出一个JSON对象，包含：
- step_id: 整数
- goal: 该步骤要达成的明确目标
- required_content_items: ["link_id1", "link_id2", ...]
- required_data: 从 ['transcript','transcript_with_comments','metadata','previous_findings'] 中选择
- marker_relevance: ["FACT: X", "OPINION: Y", ...]
- retrieval_strategy: "markers_only" | "full_content" | "selective_by_markers"
- chunk_strategy: 从 ['all','sequential','semantic_chunks'] 中选择
- notes: 简要说明

**设计哲学 (你的指导原则):**
- **洞见优先:** 不要只罗列任务
- **逻辑流程:** 计划应能讲述一个故事
- **创新方法:** 超越简单的信息提取
- **清晰至上:** method_description必须明确

[... detailed example with 3 nested steps ...]
```

**Issues:**
- ❌ Heavy focus on system constructs (markers, retrieval strategies, chunk strategies)
- ❌ Complex JSON schema with many required fields
- ❌ "Design philosophy" section prescribes approach
- ❌ User intent not prominently featured

#### AFTER (~30 lines, goal-focused)
```markdown
**用户想要理解:**
{selected_goal}

**具体要探索的问题:**
{component_questions}

**用户的优先关注:**
{user_guidance}

---

**可用资料概览:**
{data_overview}

---

**你的任务:**
制定一个简单、清晰的计划来回答用户的问题。

思考:
1. 首先需要了解什么？
2. 什么样的分析最有洞察力？
3. 什么样的顺序最合理？

创建3-7个研究步骤，每个步骤应该:
- 有明确的目的，与用户问题相关
- 说明需要什么资料
- 逻辑上承接前面的步骤

不需要规定具体的分析方法 - 相信执行时你会知道如何有效分析。
专注于*发现什么*，而不是*如何发现*。

**输出:**
{
  "steps": [
    {
      "step": "这一步要发现什么",
      "needed_data": "需要什么资料",
      "purpose": "为什么这对回答用户问题很重要"
    }
  ]
}
```

**Improvements:**
- ✅ User question front and center
- ✅ Removed prescriptive methodology (design philosophy)
- ✅ Simplified JSON (3 fields vs. 8 fields)
- ✅ Removed complex system constructs
- ✅ 60% shorter
- ✅ Trusts AI to determine methods during execution

---

### Phase 3: Execution

#### BEFORE (132 lines - MOST COMPLEX)
```markdown
你是{system_role_description}。你的任务是执行特定的分析步骤，
并以结构化的JSON格式返回结果。
{research_role_rationale}

**上下文（简要）**
{scratchpad_summary}

{previous_chunks_context}

**禁止重复的内容**
{cumulative_digest}

**研究角色定位**
{research_role_section}

**用户指导与优先事项**    <-- BURIED AT LINE 13!
{user_guidance_context}

**相关内容的标记概览**
{marker_overview}

**已检索的完整内容**
{retrieved_content}

**任务（精简与创意）**
围绕步骤目标 "{goal}" 做证据驱动分析，并撰写详细研究报告。

- 在结构化报告中于"重要发现"与"深入分析"之间插入一篇完整文章
- 文章需综述研究主题、明确回答当前步骤目标...

**避免重复的特别指示**
- {novelty_guidance}
- 若必须引用既有结论，请明确解释本次新增的证据...

**语言要求（重要）:**          <-- 17 LINES OF LANGUAGE INSTRUCTIONS
- **所有输出必须使用中文**：无论源内容使用何种语言...
- **跨语言术语引用**：...
- **引用原文的处理**：...
- **一致性**：...

**标记说明:**                    <-- MORE MARKER EXPLANATIONS
- 标记概览显示了所有可用内容项中的关键信息点...

**检索能力说明:**               <-- 20+ LINES ON RETRIEVAL
你可以通过以下方式请求更多内容：
1. 请求完整内容项: ...
2. 基于标记检索: ...
3. 按话题检索: ...
4. 语义向量检索: ...

以主要内容（转录/文章）为锚；评论仅用于验证与发现争议。
优先采用"5 Whys"方法深入原因链...      <-- PRESCRIBED METHODOLOGY

方法要点：
- 5 Whys：围绕核心现象连续追问"为什么"...
- 矛盾与空白：主动标注矛盾...
- 非重复：同一点只表述一次...

**输出（必须是有效JSON）**          <-- 60+ LINES OF JSON SCHEMA
{
  "step_id": 1,
  "requests": [...],              // Complex retrieval system
  "missing_context": [...],
  "findings": {
    "summary": "...",
    "article": "完整文章：...",   // REQUIRES FULL ARTICLE
    "points_of_interest": {
      "key_claims": [{...}],
      "notable_evidence": [{...}],
      "controversial_topics": [{...}],
      "surprising_insights": [...],
      "specific_examples": [{...}],
      "open_questions": [...]
    },
    "analysis_details": {
      "five_whys": [              // MANDATORY 5 WHYS
        {"level": 1, "question": "...", "answer": "..."},
        ...
      ],
      "assumptions": [...],
      "uncertainties": [...]
    }
  },
  "insights": "...",
  "confidence": 0.0
}
```

**Issues:**
- ❌ 132 lines - overwhelming cognitive load
- ❌ User guidance buried at line 13
- ❌ Mandatory "5 Whys" framework
- ❌ Requires full article + structured findings (redundant)
- ❌ 17 lines just for language requirements
- ❌ Complex retrieval system explanations
- ❌ Deeply nested JSON schema
- ❌ Multiple competing priorities

#### AFTER (~50 lines, focused)
```markdown
**用户想知道:**
{selected_goal}

**用户特别关心:**
{user_guidance_context}

---

**当前步骤目标:**
{goal}

---

**可用内容:**
{retrieved_content}

**之前的发现:**
{previous_chunks_context}
(避免重复这些已经分析过的内容)

---

**你的任务:**
分析内容，提供有助于回答用户问题的洞察。

重点关注:
- 直接相关于用户的问题
- 新的洞察（避免重复已有发现）
- 基于证据的推理
- 用清晰、自然的中文表达

采用任何有意义的分析方法 - 比较来源、深入因果分析、
识别模式，等等。让问题引导方法，而不是遵循固定框架。

**输出格式:**
{
  "key_findings": [
    {
      "insight": "发现了什么",
      "evidence": "支持证据",
      "relevance": "为什么这对用户的问题重要"
    }
  ],
  "deeper_analysis": "你的推理和解释（自由形式）",
  "connections": "与之前发现或用户问题的联系",
  "open_questions": ["还有什么不清楚的？"],
  "confidence": 0.8
}

**注意:** 输出用中文。引用非中文来源时，提供中文翻译并用括号标注原文。

如果需要更多内容才能完成分析，说明需要什么以及为什么。
```

**Improvements:**
- ✅ User context is THE FIRST thing the AI sees
- ✅ Reduced from 132 to ~50 lines (62% reduction)
- ✅ No mandatory methodologies (5 Whys removed)
- ✅ No redundant article requirement
- ✅ Simplified JSON (5 fields vs. 15+ nested fields)
- ✅ Language requirements condensed (17 lines → 2 lines)
- ✅ Removed complex retrieval explanations
- ✅ Trust AI to use appropriate analysis methods
- ✅ Clear priorities and purpose

---

### Phase 4: Final Synthesis

#### BEFORE (107 lines across outline + instructions)

**Outline Generation (49 lines):**
```markdown
**任务**：在理解以下上下文后，仅输出一个JSON对象，定义最终文章的
章节结构。目标是将研究上下文中的洞察串联成自然流畅、层层递进的
分析叙事，而不是逐条重复。章节标题要一句完整的话，点题、生动、
吸引眼球，不要公式化。第一个章节必须是一个Overview/引言，且内容
必须提示简洁；最后一个章节必须是一个总结，且内容必须提示简洁、展望。

[... research context ...]

**输出要求**
请生成：
{
  "sections": [
    {
      "title": "...",
      "target_words": 650,              // WORD COUNT REQUIREMENTS
      "purpose": "...",
      "supporting_steps": [...],
      "supporting_evidence": [...],
      "notes": "..."
    }
  ],
  "appendices": ["方法与来源说明", "证据附录"]  // MANDATORY
}

约束：
1. 6-10个主体章节...
2. `title` 使用自然、专业的分析型标题，引言的标题文案就必须以
   "引言："为开头，结语的标题文案就必须以"结语："为开头
3. `supporting_steps` 标明...
4. `supporting_evidence` 选取...
5. `notes` 可用于...
6. 保留附录：`方法与来源说明`、`证据附录`。
```

**Report Writing (58 lines):**
```markdown
你是{system_role_description}。{research_role_rationale}

总体原则：
- 处理主题：「{selected_goal}」
- 结论先行：用专业、克制的语气说明结论及驱动逻辑
- 在正文中使用内联标注 `[EVID-##]`
- 文章使用自然中文撰写
- 直接引用不超过全文5%
- 必须包含"方法与来源说明""证据附录"两部分

**任务**：基于以下上下文撰写完整的研究文章。仅输出 Markdown 正文
（禁止输出 JSON 或额外说明）。文章必须系统性地回答全部研究目标，
并引用证据目录中的 `[EVID-##]`。

### 大纲与覆盖约束
- 大纲（可自由改写标题词汇以适配叙事，但不得新增/删除核心章节；
  需保持与原大纲呼应）：`{outline_json}`
- 覆盖矩阵（必须逐条落实）：`{coverage_json}`

[... extensive context ...]

### 写作要点
1. **开篇**：以2-4条要点概述...
2. **结构**：依照大纲顺序展开...
3. **链接步骤**：写作时优先引用 `supporting_steps`...
4. **证据引用**：所有分析性陈述需配套 `[EVID-##]`...
5. **语气**：保持专业、克制...
6. **覆盖检查**：确保 `coverage_json` 中的每个 `goal`...
7. **附录**：结尾包含 `## 方法与来源说明`（≥400字）与
   `## 证据附录`（≥800字）...
8. **缺口提示**：若证据不足...
9. **辅助产出（可选）**：若 `auxiliary_artifacts_required` = "yes"，
   在附录后追加 FAQ 和 Slide Bullet Pack...

### 简要自检
- 是否覆盖所有组成问题与覆盖矩阵中的条目？
- 每个章节是否体现了多个步骤之间的联系？
- 关键结论、风险、争议与假设是否明确标注证据来源？
```

**Issues:**
- ❌ Separate outline generation step adds complexity
- ❌ Rigid section structure with mandatory formats
- ❌ Prescribed title patterns ("引言：", "结语：")
- ❌ Word count targets per section
- ❌ Coverage matrix must be "逐条落实"
- ❌ Mandatory appendices with word counts (≥400, ≥800)
- ❌ Self-check compliance list
- ❌ Structure serves system rather than user

#### AFTER (~40 lines, flexible)
```markdown
**用户的问题:**
{selected_goal}

**用户最关心的:**
{user_guidance}

---

**研究发现:**
{phase3_summary}

**可用证据:**
{evidence_catalog}

---

**写一份研究报告来回答用户的问题**

## 报告结构（灵活）

**核心发现概述** (2-4个要点)
- 从最重要的答案开始
- 关键结论是什么？

**主要分析** (按最合理的方式组织)
- 充分回答用户的问题
- 按逻辑展开你的发现
- 用证据支持观点 [EVID-##]
- 不要强行套用固定结构 - 让内容引导组织方式

可能的组织方式：
- 按主题分组
- 按时间顺序展现演变
- 按问题-解决方案组织
- 按对比不同观点组织

**局限与未解问题**
- 什么问题没能完全回答？
- 什么需要进一步研究？

**证据索引**
- 列出证据及其来源

---

## 写作指导

1. **以用户为中心:** 不断问"这回答了用户想知道的吗？"
2. **清晰直接:** 用自然的中文，避免不必要的术语
3. **基于证据:** 用 [EVID-##] 支持论点
4. **诚实:** 如果证据有限，直接说明
5. **有洞察:** 不只是总结 - 要分析和联系想法

## 不要做的事
- 不要强行套用预定的大纲
- 不要写成学术论文（除非用户想要）
- 不要用不必要的章节填充报告
- 不要让格式重于实质

输出：纯 Markdown，无 JSON 包装。
```

**Improvements:**
- ✅ No separate outline phase (saves complexity)
- ✅ Flexible structure based on content
- ✅ No mandatory section titles or formats
- ✅ No word count targets
- ✅ No coverage matrix checklist
- ✅ Suggests options rather than prescribing structure
- ✅ Focus on user value over compliance
- ✅ 63% reduction in length (107 → 40 lines)

---

## 🔑 Key Themes Across All Improvements

### 1. **Reorder Priorities**

**BEFORE:** System → Methodology → Data → User  
**AFTER:** User → Task → Resources → Guidance

### 2. **Simplify JSON Schemas**

**BEFORE:**
```json
{
  "findings": {
    "summary": "...",
    "article": "...",
    "points_of_interest": {
      "key_claims": [{...}],
      "notable_evidence": [{...}],
      "controversial_topics": [{...}],
      "surprising_insights": [...],
      "specific_examples": [{...}],
      "open_questions": [...]
    },
    "analysis_details": {
      "five_whys": [...],
      "assumptions": [...],
      "uncertainties": [...]
    }
  }
}
```

**AFTER:**
```json
{
  "key_findings": [
    {
      "insight": "...",
      "evidence": "...",
      "relevance": "..."
    }
  ],
  "analysis": "...",
  "open_questions": [...]
}
```

### 3. **Trust the AI**

**BEFORE:**
- "优先采用'5 Whys'方法"
- "必须包含方法与来源说明"
- "按照大纲顺序展开，不得新增/删除核心章节"
- Prescriptive methodologies

**AFTER:**
- "采用任何有意义的分析方法"
- "按最合理的方式组织"
- "让内容引导组织方式"
- Guidance without constraints

### 4. **Remove System Constructs**

**BEFORE:**
- Heavy emphasis on "markers"
- Multiple retrieval strategies
- Chunk strategies
- Coverage matrices
- Design philosophies

**AFTER:**
- Simple "available data" or "available content"
- Let AI request what it needs
- Focus on goals, not mechanisms

### 5. **Consolidate Redundant Instructions**

**BEFORE:**
- 17 lines of language requirements per phase
- Multiple anti-repetition systems
- Repeated role descriptions

**AFTER:**
- 2 lines: "输出用中文。引用非中文来源时提供译文并标注原文。"
- Simple: "避免重复已有发现"
- Remove or simplify role system

---

## 📈 Overall Impact Summary

| Aspect | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Total Lines** | ~500 | ~200 | -60% |
| **User Priority** | Buried | First | Fundamental shift |
| **Flexibility** | Rigid templates | Adaptable | Enables natural output |
| **Cognitive Load** | High | Low | AI can focus on insight |
| **JSON Complexity** | 30+ fields | 12 fields | -60% |
| **Mandatory Constraints** | Many | Few | Trust over control |

---

## 💡 Philosophy Shift

### BEFORE: Control Through Prescription
*"If we specify every detail, the AI will produce perfect outputs"*

**Result:** 
- Overwhelming complexity
- AI navigates constraints instead of thinking deeply
- Templated, bureaucratic outputs
- User intent gets lost in system requirements

### AFTER: Empower Through Clarity
*"If we clearly state the goal and trust the AI's intelligence, it will produce relevant, insightful outputs"*

**Result:**
- Simple, clear instructions
- AI focuses cognitive capacity on the user's actual question
- Natural, relevant outputs
- User satisfaction is the primary measure

---

## 🎯 Next Steps

1. **Phase 1 Implementation (Week 1):**
   - Remove/simplify role system
   - Reorder all prompts to put user first
   - Consolidate language instructions
   - Simplify JSON schemas

2. **Phase 2 Implementation (Week 2):**
   - Rewrite Phase 3 (biggest win)
   - Simplify Phase 2 planning
   - Refocus Phase 1 on user intent

3. **Phase 3 Implementation (Week 3):**
   - Remove Phase 4 outline generation
   - Flexible final report structure
   - Cross-phase consistency

4. **Testing (Week 4):**
   - A/B test old vs. new
   - Measure relevance and satisfaction
   - Iterate based on results

---

*This visual comparison demonstrates how simplification and reordering can dramatically improve prompt effectiveness while reducing complexity by 60%.*

