# Analysis & Plan: Transforming from Research Expert to Journalist Style

## Current System Analysis

### Current AI Roles by Phase

1. **Phase 1 (Discover)**: `你是一位专业的研究策略专家`
   - **English**: "You are a professional research strategy expert"
   - **Purpose**: Generate research goals from abstracts

2. **Phase 2 (Plan)**: `你是一位世界级的研究助手`
   - **English**: "You are a world-class research assistant"
   - **Purpose**: Create detailed research plans

3. **Phase 3 (Execute)**: `你是一位数据分析专家`
   - **English**: "You are a data analysis expert"
   - **Purpose**: Execute analysis steps and extract findings

4. **Phase 4 (Synthesize)**: `你是一位专业的研究报告撰写专家`
   - **English**: "You are a professional research report writing expert"
   - **Purpose**: Synthesize findings into final report

### Current System Prompt Structure

- **Location**: `research/prompts/{phase}/system.md`
- **Format**: Single line defining AI identity
- **Usage**: Loaded first as system message, followed by instructions.md as user message

### Current Writing Style Indicators

From Phase 4 instructions, the current style emphasizes:
- Structured academic report format
- Executive summaries
- Detailed analysis with evidence
- Source citations
- Clear hierarchical sections
- Formal research documentation

---

## Journalist vs Research Expert: Key Differences

### 1. **Purpose & Audience**
| Research Expert | Journalist |
|----------------|------------|
| Academic/research documentation | Public communication |
| For researchers/experts | For general audience |
| Comprehensive coverage | Focused storytelling |
| Objective analysis | Engaging narrative |

### 2. **Writing Style**
| Research Expert | Journalist |
|----------------|------------|
| Formal, academic tone | Conversational, accessible |
| Passive voice acceptable | Active voice preferred |
| Technical terminology OK | Plain language required |
| Structured sections | Narrative flow |
| Abstract conclusions | Concrete, vivid details |

### 3. **Story Structure**
| Research Expert | Journalist |
|----------------|------------|
| Introduction → Analysis → Conclusion | Hook → Story → Impact |
| Linear, comprehensive | Narrative arc with highlights |
| All findings equally weighted | Hierarchy by newsworthiness |
| Objective reporting | Compelling storytelling |

### 4. **Evidence Handling**
| Research Expert | Journalist |
|----------------|------------|
| Citations in formal format | Quotes as dialog/narrative |
| Source attribution inline | Source context integrated |
| Evidence as proof | Evidence as story elements |
| Statistical summaries | Human stories, anecdotes |

### 5. **Engagement Approach**
| Research Expert | Journalist |
|----------------|------------|
| Informative | Captivating |
| Complete coverage | Select highlights |
| Balanced presentation | Perspective with context |
| Fact-focused | Story-driven |

---

## Required Changes by Phase

### Phase 1: Discover (Goal Generation)
**Current**: Research strategy expert suggesting research goals
**Change Needed**: Journalist identifying story angles and newsworthy questions

**Impact**: 
- Goals should be framed as "story questions" rather than research questions
- Focus on what's interesting/newsworthy vs. what's comprehensive
- Consider audience appeal, conflict, human interest

**Files to Modify**:
- `research/prompts/phase1_discover/system.md`
- `research/prompts/phase1_discover/instructions.md` (minor tweaks)

### Phase 2: Plan (Research Planning)
**Current**: Research assistant creating analytical plans
**Change Needed**: Journalist planning investigation approach and story structure

**Impact**:
- Steps should focus on gathering "story elements" (quotes, examples, human stories)
- Plan should consider narrative flow, not just analytical completeness
- Include steps for finding "hook" elements and compelling details

**Files to Modify**:
- `research/prompts/phase2_plan/system.md`
- `research/prompts/phase2_plan/instructions.md` (moderate changes)

### Phase 3: Execute (Analysis Execution)
**Current**: Data analysis expert extracting findings
**Change Needed**: Journalist gathering quotes, facts, and story elements

**Impact**:
- Findings should prioritize quotable content, specific examples, human narratives
- Analysis should identify story-worthy elements (conflict, surprise, impact)
- Evidence should be formatted for narrative use (ready-to-quote passages)

**Files to Modify**:
- `research/prompts/phase3_execute/system.md`
- `research/prompts/phase3_execute/instructions.md` (significant changes)

### Phase 4: Synthesize (Final Report)
**Current**: Research report writing expert creating formal reports
**Change Needed**: Journalist writing engaging, accessible news/investigative piece

**Impact**: **HIGHEST PRIORITY**
- Complete transformation of writing style and structure
- Narrative structure instead of academic structure
- Engaging lead/hook required
- Conversational, accessible tone
- Quotes integrated naturally
- Human-interest focus

**Files to Modify**:
- `research/prompts/phase4_synthesize/system.md` (CRITICAL)
- `research/prompts/phase4_synthesize/instructions.md` (MAJOR REWRITE)

---

## Detailed Modification Plan

### Phase 1 Changes: Story Angle Discovery

#### System Prompt (`phase1_discover/system.md`)
**Current:**
```
你是一位专业的研究策略专家。你的任务是快速分析提供的资料摘要，并针对用户提出的研究主题，提出三个不同的、有洞察力且可执行的研究目标。
```

**Proposed:**
```
你是一位资深的新闻记者。你的任务是从新闻角度分析提供的资料摘要，针对用户提出的主题，识别三个不同的、有新闻价值的报道角度和故事线索。
```

**Key Changes**:
- 专业的研究策略专家 → 资深的新闻记者
- 研究目标 → 报道角度和故事线索
- Focus on newsworthiness vs. research comprehensiveness

#### Instructions (`phase1_discover/instructions.md`)
**Current Emphasis**: Research goals, analytical questions
**New Emphasis**: Story angles, newsworthy questions, audience appeal

**Additions Needed**:
- Frame goals as "story questions" (What's the story? Why does it matter?)
- Consider human interest, conflict, surprise elements
- Think about what would engage a general audience

---

### Phase 2 Changes: Investigation Planning

#### System Prompt (`phase2_plan/system.md`)
**Current:**
```
你是一位世界级的研究助手。你的任务是为特定的研究目标创建一个详细、可执行、逐步的计划，并使用结构化JSON响应。
```

**Proposed:**
```
你是一位经验丰富的调查记者。你的任务是为特定的报道角度制定详细的调查计划，包括需要收集的素材、引述、证据和故事元素，使用结构化JSON格式。
```

**Key Changes**:
- 研究助手 → 调查记者
- 研究目标 → 报道角度
- 分析任务 → 调查计划、素材收集
- Emphasize story elements (quotes, examples, narratives)

#### Instructions (`phase2_plan/instructions.md`)
**Current Focus**: Analytical steps, data chunks, systematic analysis
**New Focus**: Investigation steps, story gathering, narrative elements

**Modifications Needed**:
- Change "analysis tasks" to "investigation steps"
- Emphasize collecting:
  - Quotable passages (引述)
  - Specific examples (具体事例)
  - Human narratives (人物故事)
  - Conflict/disagreement (争议观点)
  - Surprising facts (意外事实)
- Consider narrative structure (hook, development, conclusion)

---

### Phase 3 Changes: Story Element Extraction

#### System Prompt (`phase3_execute/system.md`)
**Current:**
```
你是一位数据分析专家。你的任务是执行特定的分析步骤，并以结构化的JSON格式返回结果。
```

**Proposed:**
```
你是一位新闻采编记者。你的任务是按照调查计划执行采访和分析，从资料中提取引述、事实、故事元素和新闻报道所需的素材，以结构化JSON格式返回。
```

**Key Changes**:
- 数据分析专家 → 新闻采编记者
- 分析步骤 → 采访和分析
- Findings → 引述、事实、故事元素

#### Instructions (`phase3_execute/instructions.md`)
**Current Structure**: Analysis with findings, points_of_interest
**New Structure**: Story elements ready for narrative use

**Major Modifications Needed**:

1. **Emphasize Quote Extraction**:
   - Format findings with ready-to-quote passages
   - Include context for quotes
   - Identify speakers/subjects

2. **Reframe Points of Interest**:
   - **Key Claims** → **引述 (Quotable Statements)**: Ready-to-use quotes
   - **Notable Evidence** → **事实素材 (Fact Materials)**: Specific facts, numbers, examples
   - **Controversial Topics** → **冲突点 (Conflict Points)**: Disagreements, debates
   - **Surprising Insights** → **新闻点 (News Angles)**: Newsworthy, surprising elements
   - **Specific Examples** → **故事元素 (Story Elements)**: Anecdotes, human stories
   - **Open Questions** → **待追踪线索 (Follow-up Leads)**: Unanswered questions worth investigating

3. **Add Narrative Context**:
   - For each element, note: "How would this be used in a story?"
   - Identify emotional resonance
   - Note visual/vivid details

---

### Phase 4 Changes: Journalistic Writing (CRITICAL)

#### System Prompt (`phase4_synthesize/system.md`)
**Current:**
```
你是一位专业的研究报告撰写专家。你的工作是将一系列结构化数据点综合成最终、连贯、书写良好的Markdown格式报告。
```

**Proposed:**
```
你是一位资深新闻记者。你的工作是将调查收集的材料、引述和事实整理成一篇引人入胜、结构清晰、面向大众的新闻报道或深度调查文章，使用Markdown格式。
```

**Key Changes**:
- 研究报告撰写专家 → 资深新闻记者
- 结构化数据点 → 调查收集的材料、引述和事实
- 研究报告 → 新闻报道或深度调查文章
- Emphasize: 引人入胜 (engaging), 面向大众 (for general audience)

#### Instructions (`phase4_synthesize/instructions.md`)
**COMPLETE REWRITE NEEDED**

**Current Structure**: Academic report format
**New Structure**: Journalistic article format

**Proposed New Structure**:

```markdown
**原始报道角度:**
用户选择的报道角度是："{selected_goal}"

**收集的素材（你的采访笔记）:**
以下是调查中收集的所有素材：
{scratchpad_contents}

**任务:**
使用所有提供的素材，撰写一篇新闻报道或深度调查文章，直接回答"原始报道角度"。文章应：

1. **引人入胜的开头**：用一个吸引人的引子、故事或引人注目的引述开始
2. **叙事结构**：采用新闻写作的倒金字塔结构或叙事展开
3. **活生生的引述**：将收集的引述自然融入文章，作为人物的话语
4. **具体例子**：使用具体的例子、数据、故事使内容生动
5. **可读性**：使用平实的语言，避免学术术语，面向大众读者
6. **来源标注**：自然地在文中引用来源（如："来自XXX视频的内容显示..."或"评论区用户指出..."）
7. **Markdown格式**：使用标题、列表、引用等Markdown格式增强可读性
8. **故事节奏**：保持叙事节奏，避免冗长的分析段落

**不要输出JSON，输出纯Markdown文本文章。**

**文章结构建议:**

# {标题：用新闻标题风格，抓住核心故事}

## [开头段落：引人入胜的引子]
用一个生动的场景、引人注目的引述、或令人意外的事实开始，立即抓住读者注意力。

## 核心故事
基于素材展开主要故事，自然融入引述和例子。

## 关键发现
如果素材中包含"points_of_interest"，将其转换为新闻叙述：
- **引人注目的引述**：将quotable statements作为直接引述呈现
- **关键事实**：突出最重要的数据和事实
- **冲突与争议**：展示不同观点和争议，增加故事张力
- **意外发现**：强调令人惊讶或反直觉的洞察
- **具体案例**：通过具体例子让抽象概念具体化
- **待解之谜**：指出未解答的问题，暗示未来追踪方向

每个元素应自然地融入叙事，而不是列表式呈现。

## 影响与意义
阐述这个故事的意义、对读者的影响，或提出值得思考的问题。

## [可选的] 不同声音
如果存在明显争议，可以专门展示不同观点。

---

**写作风格要求:**
- 使用主动语态
- 句子简洁有力
- 段落短而精悍（2-4句为宜）
- 用具体细节替代抽象概念
- 让数字有意义（不仅是数字，还要解释含义）
- 保持客观但富有叙事性
- 适当的过渡和连接，保证流畅阅读

**引述使用建议:**
- 将引述作为直接引语呈现："..."，XXX说道
- 提供引述的上下文
- 将引述与叙述自然结合
- 不要过度依赖引述，适当转述
```

---

## Implementation Considerations

### 1. **Language & Tone Consistency**
- Current system uses Chinese prompts
- Journalist style should maintain Chinese
- Need to ensure consistency across all phases
- Tone: Professional journalism (not tabloid), accessible but authoritative

### 2. **Backward Compatibility**
- Phase 1-3 output schemas might need minor adjustments
- Phase 4 output format stays the same (Markdown text)
- Existing data structures mostly compatible
- Main change is in interpretation and writing style

### 3. **Phase Dependencies**
- Phase 3 findings structure already includes `points_of_interest`
- Need to ensure Phase 3 reframes these for narrative use
- Phase 4 needs to transform findings into story elements

### 4. **Testing Considerations**
- Test with various content types (video transcripts, comments, articles)
- Verify narrative quality vs. analytical quality
- Check quote integration and source attribution
- Ensure readability for general audience

---

## Risk Assessment

### Low Risk Areas
- System prompt changes (simple text replacement)
- Instructions updates (additive changes mostly)
- Output format remains Markdown

### Medium Risk Areas
- Phase 3 reframing of points_of_interest might be confusing
- AI might not fully adopt journalistic style in first attempts
- Need iterative prompt refinement

### High Risk Areas
- Phase 4 complete rewrite could lose important elements
- Need to preserve source attribution while making it narrative
- Balance between engaging and informative

### Mitigation Strategies
1. **Gradual Rollout**: Update Phase 4 first (most visible), then work backwards
2. **Prompt Examples**: Include examples of desired output style
3. **Validation**: Test with sample research to verify narrative quality
4. **Fallback**: Keep old prompts as backup until new ones validated

---

## Recommended Implementation Order

### Phase 1: Core Transformation (Highest Impact)
**Priority**: Phase 4 → Phase 3 → Phase 2 → Phase 1

1. **Update Phase 4** (2-3 hours)
   - Rewrite system.md
   - Complete rewrite of instructions.md
   - Test with sample research
   - Refine based on output quality

2. **Update Phase 3** (1-2 hours)
   - Update system.md
   - Modify instructions to emphasize story elements
   - Update points_of_interest framing
   - Test extraction quality

3. **Update Phase 2** (1 hour)
   - Update system.md
   - Modify instructions for investigation planning
   - Test plan generation

4. **Update Phase 1** (30 min)
   - Update system.md
   - Minor tweaks to instructions
   - Test goal generation

### Phase 2: Refinement (After Initial Testing)
- Add example outputs to prompts
- Refine language for better style adoption
- Adjust based on actual output quality

### Phase 3: Optional Enhancements
- Add journalist-specific prompts (e.g., "write a headline")
- Consider different article types (news piece, feature, investigative)
- Add style guide references

---

## Success Metrics

### Qualitative Indicators
- Output reads like journalism (not academic report)
- Engaging narrative with clear story arc
- Quotes naturally integrated
- Accessible to general audience
- Maintains accuracy and source attribution

### Quantitative Indicators
- Average sentence length (shorter for journalism)
- Active vs passive voice ratio
- Quote density (more quotes in journalism)
- Paragraph length (shorter paragraphs)
- Readability scores (higher for journalism)

---

## Alternative Approaches

### Option A: Complete Transformation (Recommended)
- Transform all phases to journalist style
- Consistent narrative approach throughout
- Maximum impact on final output

### Option B: Hybrid Approach
- Keep Phase 1-3 analytical
- Transform only Phase 4 to journalist style
- Faster implementation, but less consistency

### Option C: Configurable Style
- Add style parameter (research/journalist)
- Maintain both prompt sets
- More flexible, but more maintenance

**Recommendation**: Option A for consistency and maximum narrative quality

---

## Conclusion

**Primary Change**: Transform from academic research documentation to journalistic storytelling

**Key Files to Modify**:
1. `research/prompts/phase4_synthesize/system.md` (CRITICAL)
2. `research/prompts/phase4_synthesize/instructions.md` (COMPLETE REWRITE)
3. `research/prompts/phase3_execute/system.md` (IMPORTANT)
4. `research/prompts/phase3_execute/instructions.md` (SIGNIFICANT UPDATES)
5. `research/prompts/phase2_plan/system.md` (MODERATE)
6. `research/prompts/phase2_plan/instructions.md` (MODERATE UPDATES)
7. `research/prompts/phase1_discover/system.md` (MINOR)
8. `research/prompts/phase1_discover/instructions.md` (MINOR TWEAKS)

**Estimated Time**: 4-6 hours for complete transformation

**Next Steps**: 
1. Review this plan
2. Approve modifications
3. Begin with Phase 4 implementation
4. Iterate based on output quality






