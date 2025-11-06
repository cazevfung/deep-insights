# Article Cohesion & Journalistic Style Improvement Plan

## Current State Analysis

### Problems Identified from Sample Report

Based on the sample report (`report_251029_150500_20251029_191137.md`), the current article generation has several cohesion issues:

#### 1. **Fragmented Structure**
- **Problem**: The report jumps between topics without smooth transitions
- **Evidence**: Section "关键发现与兴趣点" uses bullet lists that break narrative flow
- **Impact**: Reads like a collection of data points rather than a cohesive story
- **Example**: The report moves from "核心吸引力" to "挫败感根源" without bridging why these are related

#### 2. **Repetitive Content**
- **Problem**: Same examples and quotes appear in multiple sections
- **Evidence**: "37秒死亡" appears in:
  - 执行摘要 (line 19)
  - 主要发现 (line 41)
  - 关键发现与兴趣点 (line 66)
  - 详细分析 (line 103)
- **Impact**: Redundancy breaks reader engagement, wastes space

#### 3. **List-Based Sections**
- **Problem**: The "关键发现与兴趣点" section (lines 57-94) is entirely bullet points
- **Structure**: 
  ```
  ### **关键论点**
  1. ...
  2. ...
  3. ...
  ### **重要证据**
  - ...
  - ...
  ```
- **Impact**: Reads like a research outline, not a finished article
- **Issue**: Information is categorized rather than woven into narrative

#### 4. **Source Citation Disruption**
- **Problem**: Source citations break narrative flow
- **Pattern**: "(来源：bili_req1, bili_case1)" appears after every quote
- **Impact**: Reads like academic citation rather than journalistic attribution
- **Better Approach**: Integrate sources naturally: "一位B站玩家在评论中提到..."

#### 5. **Lack of Narrative Arc**
- **Problem**: No clear storytelling progression
- **Current Flow**: 
  - 执行摘要 → 主要发现 (facts) → 关键发现与兴趣点 (lists) → 详细分析 (more facts) → 结论
- **Issue**: No "hook," no story development, no emotional progression
- **Missing**: Opening that grabs attention, middle that builds tension, conclusion that feels like resolution

#### 6. **Transitions Between Sections**
- **Problem**: Abrupt transitions with only horizontal rules (`---`)
- **Example**: Lines 23, 54, 95 use `---` but no transition sentences
- **Impact**: Feels like separate documents concatenated, not one article

#### 7. **Tone Inconsistency**
- **Problem**: Mixes academic research tone with emotional player quotes
- **Example**: 
  - Academic: "跨平台分析揭示了显著的文化与表达差异"
  - Player quote: "红温""白忙活""四不像"
- **Impact**: Disconnect between writer's voice and source voices

---

## Root Cause Analysis

### Why These Problems Exist

#### 1. **Prompt Structure Encourages Listing**
**Location**: `research/prompts/phase4_synthesize/instructions.md`

**Current Instruction** (lines 31-40):
```
## 关键发现与兴趣点
如果发现中包含points_of_interest，请在此章节总结：
- **关键论点**: 从所有步骤中提取的最突出的论点
- **重要证据**: 最有力的数据、例子、引用
...
```

**Problem**: The prompt explicitly asks for categorized lists, not narrative integration.

**Impact**: AI follows the structure literally, creating bullet-point sections rather than weaving points into narrative.

---

#### 2. **Scratchpad Format Doesn't Support Narrative Synthesis**

**Current Scratchpad Structure** (from `session.py:145-209`):
```
步骤 1: {insights}
摘要: {summary}
兴趣点: 关键论点: 3 个, 重要证据: 5 个...
发现: {full JSON dump}
来源: link_id_1, link_id_2
```

**Problems**:
- **JSON dump inclusion**: Full findings JSON is too structured/dense for narrative use
- **Categorical organization**: Points are pre-categorized (key_claims, evidence, etc.) before synthesis
- **Source labels**: Technical IDs (link_id_1) not human-readable context
- **No temporal/thematic grouping**: Steps organized by execution order, not story relevance

**Impact**: AI receives data in research format, outputs in research format.

---

#### 3. **System Prompt Defines Wrong Role**

**Current System Prompt** (`phase4_synthesize/system.md`):
```
你是一位专业的研究报告撰写专家。你的工作是将一系列结构化数据点综合成最终、连贯、书写良好的Markdown格式报告。
```

**Problems**:
- **Role**: "研究报告撰写专家" (research report expert) → academic writing
- **Goal**: "综合成报告" (synthesize into report) → informational, not narrative
- **No mention**: No instruction to create engaging, story-driven content

**Impact**: AI defaults to research/academic style rather than journalistic style.

---

#### 4. **No Narrative Structure Guidance**

**Current Structure Template** (instructions.md lines 22-46):
```
## 执行摘要
## 主要发现
## 关键发现与兴趣点
## 详细分析
## 结论
```

**Problems**:
- **Formulaic**: Academic report structure, not news article
- **No storytelling elements**: Missing hook, narrative arc, human interest
- **No emphasis on flow**: No guidance on transitions, pacing, engagement

---

#### 5. **Points of Interest Are Pre-Extracted, Not Synthesized**

**Phase 3 Extraction** creates structured categories:
- `key_claims[]`
- `notable_evidence[]`
- `controversial_topics[]`
- `surprising_insights[]`
- `specific_examples[]`
- `open_questions[]`

**Phase 4 Instruction** (line 16): "如果发现中包含'points_of_interest'，请专门提取和展示这些内容"

**Problem**: "提取和展示" (extract and display) = list them, not "integrate into narrative"

---

## Improvement Strategy

### Goal
Transform from **structured research documentation** to **cohesive, engaging journalistic article** while maintaining accuracy and source attribution.

### Core Principles

1. **Narrative Flow Over Categorization**
   - Integrate points into story, don't list them
   - Use transitions to connect ideas
   - Build narrative arc: hook → development → resolution

2. **Natural Source Integration**
   - Attributions woven into sentences, not parenthetical citations
   - Use descriptive source context ("一位B站玩家写道" vs "来源：bili_req1")

3. **Deduplication**
   - Use examples once, in their most impactful location
   - Reference previous mentions if needed, don't repeat

4. **Thematic Organization**
   - Group by story themes, not data categories
   - Lead with most compelling/newsworthy angles

5. **Conversational but Authoritative Tone**
   - Accessible language without dumbing down
   - Active voice, vivid details
   - Balance player emotions with analytical insights

---

## Proposed Changes

### Change 0: Add Multi-Question Synthesis Phase (NEW - HIGH IMPACT)

**Problem**: Currently, user selects ONE of three research goals, missing broader perspective. All three questions should be synthesized into a comprehensive topic.

**New Phase**: Phase 1.5 (Synthesize All Research Questions)

**Location**: Between Phase 1 and Phase 2 in `research/agent.py`

**Implementation**:

#### 0.1. New Phase 1.5 Module

**File**: `research/phases/phase1_synthesize.py` (NEW FILE)

```python
class Phase1Synthesize(BasePhase):
    """Phase 1.5: Synthesize all three research goals into unified topic."""
    
    def execute(
        self,
        all_goals: List[Dict[str, Any]],
        data_abstract: str
    ) -> Dict[str, Any]:
        """
        Synthesize all three research goals into one comprehensive topic.
        
        Args:
            all_goals: List of all three suggested goals from Phase 1
            data_abstract: Abstract of available data
            
        Returns:
            Dict with synthesized goal
        """
        # Context includes all three goals
        context = {
            "goal_1": all_goals[0].get("goal_text", ""),
            "goal_2": all_goals[1].get("goal_text", ""),
            "goal_3": all_goals[2].get("goal_text", ""),
            "data_abstract": data_abstract
        }
        
        messages = compose_messages("phase1_synthesize", context=context)
        
        response = self._stream_with_callback(messages)
        
        # Parse synthesized goal
        parsed = self.client.parse_json_from_stream(iter([response]))
        synthesized_goal = parsed.get("synthesized_goal", {})
        
        return {
            "synthesized_goal": synthesized_goal,
            "component_goals": all_goals,
            "raw_response": response
        }
```

#### 0.2. New Prompt Files

**Files**:
- `research/prompts/phase1_synthesize/system.md` (NEW)
- `research/prompts/phase1_synthesize/instructions.md` (NEW)
- `research/prompts/phase1_synthesize/output_schema.json` (NEW)

**System Prompt** (`phase1_synthesize/system.md`):
```
你是一位资深的研究策略专家。你的任务是分析三个相关的研究问题，将它们综合成一个更大、更全面的研究主题，确保这个综合主题能够涵盖所有三个问题的核心内容。
```

**Instructions** (`phase1_synthesize/instructions.md`):
```
**三个研究问题：**

1. "{goal_1}"
2. "{goal_2}"
3. "{goal_3}"

**可用数据概览：**
{data_abstract}

**任务：**

分析这三个研究问题，识别它们的共同主题、相关性和可能的交叉点。然后，创建一个综合的研究主题，这个主题应该：

1. **涵盖所有三个问题**：确保综合主题能够回答或探索所有三个原始问题的核心
2. **发现深层联系**：识别三个问题之间的内在关系或共同线索
3. **提供更广阔视角**：综合主题应该比单个问题提供更全面的视角
4. **保持可行性**：综合后的主题应该仍然可以在一篇深度文章中充分探索

**输出格式（必须是有效的JSON）：**
{{
  "synthesized_goal": {{
    "comprehensive_topic": "综合后的研究主题（一句话或一个问题）",
    "component_questions": [
      "原始问题1将探索：...",
      "原始问题2将探索：...",
      "原始问题3将探索：..."
    ],
    "unifying_theme": "将三个问题联系在一起的核心主题",
    "research_scope": "研究的范围和深度说明"
  }}
}}

**示例：**

输入：
- 问题1: "玩家对游戏的吸引力是什么？"
- 问题2: "玩家遇到的挫败感来源是什么？"
- 问题3: "这些体验如何影响留存？"

输出：
{{
  "synthesized_goal": {{
    "comprehensive_topic": "玩家对游戏的核心吸引力和挫败感分别是什么？这些情感体验如何影响其长期留存与成瘾性？",
    "component_questions": [
      "探索游戏的核心吸引力机制和玩家动机",
      "分析挫败感的根源和影响因素",
      "研究吸引力与挫败感的相互作用如何影响玩家行为"
    ],
    "unifying_theme": "游戏情感体验的双面性及其对长期参与的影响",
    "research_scope": "全面分析游戏的吸引力-挫败感机制，及其对玩家留存和成瘾性的复合影响，涵盖机制设计、玩家心理和长期行为模式"
  }}
}}
```

**Output Schema** (`phase1_synthesize/output_schema.json`):
```json
{
  "type": "object",
  "required": ["synthesized_goal"],
  "properties": {
    "synthesized_goal": {
      "type": "object",
      "required": ["comprehensive_topic", "component_questions"],
      "properties": {
        "comprehensive_topic": {"type": "string"},
        "component_questions": {
          "type": "array",
          "items": {"type": "string"}
        },
        "unifying_theme": {"type": "string"},
        "research_scope": {"type": "string"}
      }
    }
  }
}
```

#### 0.3. Update Agent Flow

**File**: `research/agent.py`

**Current Flow** (lines 118-143):
```python
# Phase 1: Discover
phase1_result = phase1.execute(combined_abstract, user_topic)
goals = phase1_result.get("suggested_goals", [])
self.ui.display_goals(goals)

# User selects goal
selected_id = self.ui.prompt_user("请选择研究目标ID (1-3)", goal_ids)
selected_goal = next((g for g in goals if str(g.get("id")) == selected_id), None)
selected_goal_text = selected_goal.get("goal_text", "")

# Phase 2: Plan (uses selected_goal_text)
phase2_result = phase2.execute(selected_goal_text, data_summary)
```

**New Flow**:
```python
# Phase 1: Discover
phase1_result = phase1.execute(combined_abstract, user_topic)
goals = phase1_result.get("suggested_goals", [])
self.ui.display_goals(goals)

# Phase 1.5: Synthesize all goals (NEW)
self.ui.display_header("Phase 1.5: 综合研究主题")
phase1_5 = Phase1Synthesize(self.client, session)
phase1_5_result = phase1_5.execute(goals, combined_abstract)

synthesized = phase1_5_result.get("synthesized_goal", {})
comprehensive_topic = synthesized.get("comprehensive_topic", "")
component_questions = synthesized.get("component_questions", [])

self.ui.display_message("综合研究主题已生成", "success")
self.ui.display_synthesized_goal(synthesized)  # New UI method

# Phase 2: Plan (uses comprehensive_topic, ensures all component questions addressed)
phase2_result = phase2.execute(comprehensive_topic, data_summary, component_questions)
```

#### 0.4. Update Phase 2 to Address All Component Questions

**File**: `research/prompts/phase2_plan/instructions.md`

**Add to Context**:
```
**综合研究主题：** "{comprehensive_topic}"

**需要涵盖的组成问题：**
1. {component_question_1}
2. {component_question_2}
3. {component_question_3}

**重要要求：**
- 研究计划必须确保所有三个组成问题都得到充分探索
- 计划中的步骤应该自然地覆盖所有方面
- 可以创建专门步骤来回答特定问题，或者将多个问题整合在单个步骤中
- 确保最终报告能够全面回答综合主题，包括所有组成问题
```

#### 0.5. Update UI for Synthesized Goal Display

**Files**: `research/ui/console_interface.py` and `research/ui/mock_interface.py`

**New Method Needed**:
```python
def display_synthesized_goal(self, synthesized_goal: Dict[str, Any]) -> None:
    """
    Display the synthesized comprehensive topic and component questions.
    
    Args:
        synthesized_goal: Dictionary containing comprehensive_topic, 
                        component_questions, unifying_theme, research_scope
    """
    comprehensive_topic = synthesized_goal.get("comprehensive_topic", "")
    component_questions = synthesized_goal.get("component_questions", [])
    unifying_theme = synthesized_goal.get("unifying_theme", "")
    
    self.display_message("\n综合研究主题:", "info")
    self.display_message(f"  {comprehensive_topic}", "success")
    
    if unifying_theme:
        self.display_message(f"\n统一主题: {unifying_theme}", "info")
    
    if component_questions:
        self.display_message("\n组成问题:", "info")
        for i, question in enumerate(component_questions, 1):
            self.display_message(f"  {i}. {question}", "")
```

**Rationale**: User should see the synthesized goal before proceeding to planning phase.

#### 0.6. Update Phase 4 to Reference All Questions

**File**: `research/prompts/phase4_synthesize/instructions.md`

**Update Context**:
```
**综合研究主题：** "{comprehensive_topic}"

**需要涵盖的组成问题：**
1. {component_question_1}
2. {component_question_2}
3. {component_question_3}

**任务：**
使用所有提供的"结构化发现"，撰写一篇综合报告，回答"综合研究主题"。

**重要要求：**
- 文章必须全面回答综合主题，包括所有三个组成问题
- 但要以叙事方式整合，而不是分别回答（除非结构自然要求如此）
- 确保所有组成问题的关键发现都融入文章
- 如果某个组成问题没有得到充分回答，需要明确说明为什么（数据限制等）

**结构灵活性：**
根据素材内容，选择最能展示所有方面并回答所有组成问题的结构。例如：
- 如果三个问题相互独立 → 可能使用"主题并行"结构
- 如果三个问题有递进关系 → 可能使用"线性叙事"
- 如果三个问题相互关联 → 可能整合在深度探索中
```

**Rationale**:
- Ensures comprehensive coverage of all research angles
- Creates more cohesive final article (unified topic instead of single question)
- Better utilizes the three-goal generation process
- Provides richer context for article structure determination

---

### Change 1: Update System Prompt (HIGH IMPACT)

**File**: `research/prompts/phase4_synthesize/system.md`

**Current**:
```
你是一位专业的研究报告撰写专家。你的工作是将一系列结构化数据点综合成最终、连贯、书写良好的Markdown格式报告。
```

**Proposed**:
```
你是一位资深新闻记者，擅长撰写深度报道和调查文章。你的工作是将收集的素材、引述和事实整理成一篇引人入胜、结构清晰、面向大众的新闻报道，使用Markdown格式。

你的文章应该：
- 以引人入胜的开头抓住读者注意力
- 采用叙事结构，而不是列表式列举
- 自然融入引述和例子，让证据支撑故事
- 使用流畅的过渡连接各部分
- 保持客观但富有叙事性
- 让复杂信息易于理解，但不失深度
```

**Rationale**: 
- Changes AI identity from "research report writer" to "journalist"
- Sets expectations for narrative style, not academic style
- Emphasizes engagement and readability

---

### Change 2: Rewrite Instructions Structure (CRITICAL)

**File**: `research/prompts/phase4_synthesize/instructions.md`

#### 2.1. Remove Categorical List Section

**Delete** (current lines 31-40):
```
## 关键发现与兴趣点
如果发现中包含points_of_interest，请在此章节总结：
- **关键论点**: 从所有步骤中提取的最突出的论点
- **重要证据**: 最有力的数据、例子、引用
- **争议话题**: 存在明显分歧的话题和对立观点
- **意外洞察**: 与预期不符或令人惊讶的发现
- **值得引用的例子**: 具体的案例、故事、引用
- **开放问题**: 内容中提出或值得进一步研究的问题

每个兴趣点应注明来源（根据发现中的来源信息）。
```

**Replace With**: Instructions to integrate points into narrative, not extract as lists.

#### 2.2. Flexible Structure Determination (NEW)

**Instead of rigid template, provide guidance for AI to determine structure based on content:**

**Add New Section**:
```
**文章结构设计原则：**

你的文章结构应该由内容决定，而不是遵循固定模板。在开始写作前，分析收集的素材，然后决定最适合这个故事的结构。

**结构设计流程：**

1. **分析素材主题**：
   - 识别素材中自然出现的主题和故事线
   - 考虑三个原始研究问题之间的关系
   - 确定主要角度（是单一故事线，还是多个并行故事线？）

2. **选择结构类型**（根据内容选择合适的）：
   
   **a) 线性叙事**：按时间或逻辑顺序展开
   - 适合：有明确发展过程的话题
   - 示例：问题的发现 → 不同观点的出现 → 争议的发展 → 可能的解决
   
   **b) 主题并行**：多个相关主题并列展开
   - 适合：研究问题涵盖多个独立但有联系的方面
   - 示例：核心吸引力 → 挫败感根源 → 留存机制（每个作为独立章节）
   
   **c) 对比分析**：通过对比不同观点/案例来展开
   - 适合：存在明显争议或对立观点
   - 示例：理想设计 vs. 现实产品 → 不同社区的观点对比
   
   **d) 问题解答**：逐一回答关键问题
   - 适合：原始研究问题是明确且独立的
   - 示例：针对每个研究问题创建专门章节
   
   **e) 深度探索**：从一个核心点向外扩展
   - 适合：有一个核心发现需要深入挖掘
   - 示例：核心机制 → 其影响 → 更深层的含义 → 未来展望

3. **章节组织**：
   - 根据选定的结构类型，决定需要哪些章节
   - 每个章节应该：
     * 聚焦一个清晰的主题或子问题
     * 有自然过渡连接到其他章节
     * 包含足够的支撑（引述、例子、数据）
   - 章节数量：通常3-6个主要章节（不包括开头和结论）
   - 章节标题应该：简洁、具体、吸引人

4. **开头和结尾**：
   - **开头**：必须引人入胜，可以是：
     * 一个生动的场景或例子
     * 一个引人注目的引述
     * 一个令人意外的事实或统计
     * 直接切入核心问题
   - **结尾**：应该：
     * 总结核心发现
     * 连接回开头（形成闭环）
     * 指出意义或提出思考方向

**重要原则**：
- ❌ 不要强制使用固定结构（如"执行摘要→主要发现→详细分析→结论"）
- ✅ 根据素材内容选择最合适的结构
- ✅ 确保所有三个原始研究问题都能得到充分回答
- ✅ 结构应该服务于故事，而不是故事服务于结构
- ✅ 每个章节都要有明确目的，避免冗余

**示例判断流程**：
```
如果素材显示：
- 多个独立话题 → 使用"主题并行"
- 有时间发展 → 使用"线性叙事"
- 有强烈对比 → 使用"对比分析"
- 有明确问题集合 → 使用"问题解答"
- 有核心发现需要深挖 → 使用"深度探索"
```
```

**Key Differences**:
- No rigid template
- AI determines structure based on content analysis
- Multiple structure options provided
- Emphasis on content-driven organization
- Ensures all three research questions are addressed

#### 2.3. New Instructions for Points of Interest Integration

**Add New Section**:
```
**如何将兴趣点融入文章：**

发现中包含的"points_of_interest"应该自然地融入叙事，而不是单独列出。

- **关键论点 (key_claims)**: 用作文章的主要观点，通过具体例子和引述来支撑
- **重要证据 (notable_evidence)**: 在相关段落中作为支撑细节，而不是单独列出
- **争议话题 (controversial_topics)**: 通过展示不同观点来呈现，创建叙事张力
- **意外洞察 (surprising_insights)**: 用作文章的"转折点"或"揭示时刻"
- **具体例子 (specific_examples)**: 用来让抽象概念具体化，让读者产生共鸣
- **开放问题 (open_questions)**: 在结论中自然提及，作为未来思考的方向

**原则**：每个兴趣点应该服务于故事，而不是为了完整性而列出。如果某个兴趣点不能自然地融入某个叙事位置，考虑是否真的需要它，或者是否可以用更简洁的方式提及。
```

#### 2.4. Source Attribution Guidelines

**Add Section**:
```
**来源标注的最佳实践：**

1. **自然融入**：
   - ❌ 避免："（来源：bili_req1, bili_case1）"
   - ✅ 使用："一位B站玩家在评论中写道"、"Reddit社区用户指出"、"视频作者在转录中强调"

2. **提供上下文**：
   - ❌ 避免：只给技术ID
   - ✅ 使用：描述来源类型和情境（"在激烈的讨论中"、"在玩家自述中"）

3. **引用密度**：
   - 重要引述：直接引用，提供说话者/来源描述
   - 次要信息：转述即可，不需要每句都标注来源
   - 避免过度引用导致文章断裂

4. **保持可追溯性**：
   - 在文章末尾可添加"参考来源"列表（可选）
   - 重要论断必须能追溯到具体来源
```

---

### Change 3: Enhance Scratchpad Summary Format (MEDIUM IMPACT)

**File**: `research/session.py` - `get_scratchpad_summary()` method

**Problem**: Current format dumps full JSON, which is too structured for narrative synthesis.

**Proposed Enhancement**: Create a "narrative-friendly" scratchpad format for Phase 4.

#### Option A: Create Separate Method for Narrative Synthesis

**New Method**:
```python
def get_scratchpad_summary_for_narrative(self) -> str:
    """
    Get scratchpad formatted for narrative/article writing.
    Focuses on story elements rather than structured data.
    """
```

**Format**:
```
# 研究素材摘要

## 主题线索
[基于所有步骤识别的主要主题和故事角度]

## 重要引述（按主题分组）
[Quotable statements with context and sources, organized by theme]

## 关键事实与数据
[Important numbers, statistics, specific examples with sources]

## 争议与对立观点
[Conflicts and debates with opposing views]

## 意外发现
[Surprising insights that could be story twists]

## 具体案例
[Human stories, anecdotes, vivid examples]

---

[Then provide step-by-step context below for detailed reference]
```

**Usage**: Phase 4 would use `get_scratchpad_summary_for_narrative()` instead of `get_scratchpad_summary()`.

**Pros**: 
- Cleaner input for narrative synthesis
- Thematic organization over step-by-step
- Less JSON noise

**Cons**:
- Requires implementing theme extraction logic
- May lose some detail

#### Option B: Keep Current Format, Enhance Instructions

**Simpler Approach**: Keep current scratchpad format, but add Phase 4 instructions to extract themes and reorganize mentally.

**Pros**: 
- No code changes needed
- Flexible for AI to reorganize

**Cons**:
- AI still sees cluttered JSON format
- Relies on AI's ability to re-organize

**Recommendation**: Start with Option B (instruction enhancement), add Option A later if needed.

---

### Change 4: Add Deduplication Guidance (MEDIUM IMPACT)

**File**: `research/prompts/phase4_synthesize/instructions.md`

**Add Section**:
```
**避免重复：**

- 每个引述、例子、数据点应该只使用一次，在它最有影响力的位置
- 如果需要在多个地方提及相同内容，采用"前面提到"、"正如...所述"等交叉引用
- 避免在不同章节中重复相同的信息
- 执行摘要应该是精炼概述，不要与正文详细内容完全重复
```

---

### Change 5: Add Transition and Flow Guidelines (MEDIUM IMPACT)

**File**: `research/prompts/phase4_synthesize/instructions.md`

**Add Section**:
```
**段落衔接与叙事流畅性：**

1. **使用过渡句**：
   - 每个新段落/章节应该以过渡句连接上一部分
   - 过渡句应该：a) 回顾前文要点 b) 引入新话题 c) 解释为什么转向这个话题
   - 示例："然而，这种吸引力与挫败感实为同一机制的两面..."

2. **保持段落聚焦**：
   - 每个段落应该聚焦一个核心观点或例子
   - 段落长度：2-4句为宜，避免冗长段落

3. **信息层次**：
   - 从最重要/最吸引人的内容开始
   - 逐步深入细节和背景
   - 结论应该呼应开头，形成闭环

4. **节奏控制**：
   - 避免连续多个段落都是引述
   - 交替使用：具体例子 → 分析 → 引述 → 背景信息
   - 使用数据/统计来提供支撑，但不要过度
```

---

### Change 6: Enhance Phase 3 to Extract Narrative-Ready Material (LOW-MEDIUM IMPACT)

**File**: `research/prompts/phase3_execute/instructions.md`

**Add Instructions**: When extracting `points_of_interest`, also note:
- **Narrative potential**: How this could be used in a story (hook, turning point, conclusion)
- **Quote readiness**: Is this already quotable, or needs framing?
- **Emotional resonance**: What feeling does this evoke?
- **Visual/vivid details**: Concrete details that make it vivid

**Rationale**: Better prepared material = better narrative synthesis.

**Example Addition**:
```
在提取兴趣点时，请考虑其叙事价值：
- 这个论点能否作为文章的主要观点？
- 这个例子是否足够生动，能让读者产生共鸣？
- 这个引述是否需要上下文才能使用？
- 这个洞察是否可以成为文章的"转折点"？
```

---

## Implementation Priority

### Phase 0: Multi-Question Synthesis (NEW - Highest Priority)
**Estimated Time**: 2-3 hours

0. ✅ **Change 0**: Implement multi-question synthesis
   - Create `phase1_synthesize.py` module
   - Create prompt files (`system.md`, `instructions.md`, `output_schema.json`)
   - Update `agent.py` flow to include Phase 1.5
   - Update Phase 2 instructions to address all component questions
   - Update Phase 4 instructions to reference all questions
   - Add UI method `display_synthesized_goal()` to console and mock interfaces

**Impact**: Ensures comprehensive coverage and unified topic for better article cohesion.

### Phase 1: Core Transformation (Highest Impact)
**Estimated Time**: 2-3 hours

1. ✅ **Change 1**: Update system prompt (`phase4_synthesize/system.md`)
2. ✅ **Change 2**: Rewrite instructions structure (`phase4_synthesize/instructions.md`)
   - Remove categorical list section
   - **Replace rigid template with flexible structure determination guidance**
   - Add points of interest integration guidelines
   - Add source attribution best practices

**Impact**: Immediate improvement in article structure and style, with flexible organization.

### Phase 2: Refinement (Medium Impact)
**Estimated Time**: 1-2 hours

3. ✅ **Change 4**: Add deduplication guidance
4. ✅ **Change 5**: Add transition and flow guidelines

**Impact**: Improves coherence and eliminates redundancy.

### Phase 3: Optional Enhancement (Low-Medium Impact)
**Estimated Time**: 2-4 hours (if needed)

5. ⚠️ **Change 3**: Enhance scratchpad format (if Phase 1-2 insufficient)
6. ⚠️ **Change 6**: Enhance Phase 3 extraction (nice to have)

**Impact**: Further refinement, but may not be necessary if Phase 1-2 work well.

---

## Success Metrics

### Qualitative Indicators

**Before** (Current):
- ❌ Bullet-point sections (关键发现与兴趣点)
- ❌ Source citations break flow: "(来源：bili_req1)"
- ❌ Repetitive content across sections
- ❌ Abrupt transitions (just `---`)
- ❌ List-based organization

**After** (Target):
- ✅ Narrative flow throughout
- ✅ Natural source integration ("一位玩家写道...")
- ✅ Each point used once, in best location
- ✅ Smooth transitions with context
- ✅ Thematic organization, not categorical lists

### Readability Indicators

- **Paragraph length**: 2-4 sentences average (current: some 6+ sentence paragraphs)
- **Sentence variety**: Mix of short and medium sentences
- **Quote integration**: Quotes woven into narrative, not isolated
- **Transitions**: Every section change has transition sentence
- **No repetition**: No same example/quote repeated verbatim

### Narrative Quality Indicators

- **Hook**: Opening paragraph grabs attention
- **Arc**: Clear progression from opening through development to conclusion
- **Engagement**: Uses vivid details, human stories
- **Clarity**: Complex ideas explained accessibly
- **Coherence**: All parts connect, serves overall story

---

## Testing Strategy

### Test Case 1: Sample Research Run
- Run existing research topic through updated system
- Compare output with current sample report
- Check for:
  - Narrative flow vs. bullet lists
  - Natural source attribution
  - Deduplication of examples
  - Smooth transitions

### Test Case 2: Variety of Topics
- Test with different research topics
- Verify narrative style adapts to content type
- Check that structure remains coherent across topics

### Test Case 3: Source Attribution
- Verify sources are traceable
- Check that attribution doesn't break flow
- Ensure no important claims are unsourced

---

## Risks & Mitigation

### Risk 1: Loss of Information Completeness
**Concern**: Narrative style might omit some points of interest that would be in list format.

**Mitigation**:
- Keep instructions to integrate all important points, just narratively
- Add guidance: "如果某个重要发现无法自然融入，可以添加一个简短的'补充说明'段落"
- Balance: Prioritize narrative flow, but ensure completeness

### Risk 2: Over-Narrative, Loss of Objectivity
**Concern**: Too much storytelling might sacrifice analytical depth.

**Mitigation**:
- Instructions emphasize: "保持客观但富有叙事性"
- Maintain evidence-based writing
- Use narrative structure for clarity, not sensationalism

### Risk 3: Source Attribution Issues
**Concern**: Natural attribution might lose traceability.

**Mitigation**:
- Instructions require: "重要论断必须能追溯到具体来源"
- Optional: Add reference section at end for detailed source list
- Balance readability with accountability

### Risk 4: AI Doesn't Follow Instructions
**Concern**: AI might still create lists despite instructions.

**Mitigation**:
- Strong, clear examples in instructions
- Explicit: "不要创建'关键发现与兴趣点'这样的列表章节"
- Iterative refinement based on output

---

## Alternative Approaches Considered

### Option A: Post-Processing Transformation
**Approach**: Generate current format, then use second AI pass to transform to narrative.

**Pros**: 
- No changes to core system
- Can keep both formats

**Cons**:
- Two-stage generation (slower, more expensive)
- May lose nuance in transformation
- Doesn't address root cause

**Verdict**: Not recommended - address at generation stage.

---

### Option B: Configurable Style
**Approach**: Add parameter to choose "research" vs. "journalist" style.

**Pros**:
- Flexibility for different use cases
- Backward compatible

**Cons**:
- More complexity
- User asked specifically for journalist style
- Can add later if needed

**Verdict**: Start with journalist style, add option later if needed.

---

### Option C: Template-Based Structure
**Approach**: Provide specific article templates (news piece, feature, investigation).

**Pros**:
- More control over structure
- Can optimize for specific article types

**Cons**:
- Less flexible
- May constrain AI creativity
- Current issue is style, not just structure

**Verdict**: Can add as Phase 3 enhancement if needed.

---

## Conclusion

### Summary of Problems
1. Fragmented structure with bullet lists
2. Repetitive content across sections
3. Source citations breaking narrative flow
4. Lack of narrative arc and transitions
5. Academic/research tone rather than journalistic
6. **Only one research question addressed** (missing broader perspective)
7. **Rigid structure template** (doesn't adapt to content)

### Root Causes
1. Prompt asks for categorized lists
2. System role = research expert, not journalist
3. Scratchpad format too structured for narrative synthesis
4. No guidance on narrative flow and transitions
5. **User selects single goal** (other questions ignored)
6. **Fixed structure template** (not content-driven)

### Solution Approach
1. **Add multi-question synthesis** (Phase 1.5) to unify all research angles
2. **Update system prompt** to journalist role
3. **Rewrite instructions** to emphasize narrative integration and flexible structure
4. **Add guidelines** for transitions, deduplication, source attribution
5. **Enable structure determination** based on content analysis
6. **Enhance scratchpad** (optional, if needed)

### Expected Outcome
Articles that read like **cohesive, engaging journalism** rather than **scattered research points**, while:
- **Comprehensively addressing all research angles** (from all three original questions)
- **Organizing content flexibly** based on what best serves the story
- Maintaining accuracy and source traceability

---

## Next Steps (After Approval)

1. Review and approve this plan
2. **Implement Phase 0** (multi-question synthesis)
3. **Implement Phase 1** (flexible structure + system prompt + instructions)
4. Test with sample research (verify all three questions are addressed)
5. Verify structure flexibility (test with different content types)
6. Refine based on output quality
7. Implement Phase 2 if needed
8. Document final approach

---

## Appendix: Example Transformation

### Current Style (Sample):
```
## 关键发现与兴趣点

### **关键论点**
1. **搜打撤的核心吸引力在于其非击杀导向的目标**（以成功撤离为核心），这拓宽了玩家类型，包括喜欢探索、解谜、社交和建造的玩家。（来源：rd_case1）
2. **国内搜打撤产品**（如《暗区突围》），导致体验割裂为"搜和打"，沦为"四不像"。（来源：bili_req1, bili_case1）
```

### Target Style (Proposed):
```
搜打撤游戏的根本创新在于将目标从"击杀"转向"撤离"。这一转变不仅重构了射击游戏的玩法逻辑，更拓宽了玩家类型。正如一位Reddit用户所写："The objective is not to kill opposing players. The objective is to extract." 这为喜欢探索、解谜、社交和建造的玩家提供了参与空间。

然而，这一理想设计在现实产品中常常被割裂。以《暗区突围》为例，玩家批评其机制不完整："国内没有一款游戏是搜打撤...都是搜和打，复活点能出生复活...竞技不竞技，休闲不休闲四不像。" 这种机制缺陷直接破坏了"撤"的仪式感与风险价值，使得体验沦为玩家口中的"四不像"。
```

**Key Differences**:
- ✅ Narrative flow, not bullet points
- ✅ Natural quote integration
- ✅ Descriptive source attribution ("一位Reddit用户所写", "玩家批评")
- ✅ Transitions ("然而", "以...为例")
- ✅ Each example used once, in context

