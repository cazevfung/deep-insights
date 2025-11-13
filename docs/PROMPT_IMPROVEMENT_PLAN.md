# Research Tool Prompt System Improvement Plan

## Executive Summary

This document outlines a comprehensive plan to improve the research tool's prompt system, addressing issues of rigidity, over-complication, and insufficient prioritization of user intent. The current system, while sophisticated, creates barriers between the user's needs and the research output.

**Core Problems Identified:**
1. **Role rigidity** - Fixed research role limits adaptability
2. **User intent deprioritization** - System methodology overshadows user questions
3. **Over-engineered complexity** - Excessive structural requirements
4. **Prescriptive output formats** - Rigid templates constrain natural analysis

---

## Current System Analysis

### Phase 0.5: Role Generation
**Current Issues:**
- Generates a single, fixed role (e.g., "市场研究与用户行为分析师") that persists through all phases
- Role selection is data-driven rather than user-intent-driven
- No flexibility to adapt perspective as research evolves
- Role becomes a constraint rather than an enabler

**Impact:** The AI becomes locked into a persona that may not align with user's actual needs, leading to answers that feel "professional" but miss the mark on what the user actually wants to know.

### Phase 1: Discover & Synthesize
**Current Issues:**
- Heavy focus on "marker overview" and data structures
- Research goals generated from markers rather than user questions
- System role description dominates over user intent
- Instructions emphasize avoiding overlap rather than answering user questions
- 45+ lines of JSON schema requirements for goal generation

**Impact:** Research goals that are technically comprehensive but may not address the user's core curiosity or concerns.

### Phase 2: Planning
**Current Issues:**
- 74 lines of highly structured planning instructions
- Multiple layers of abstraction (markers, retrieval strategies, chunk strategies)
- Design philosophy section that prescribes specific approaches ("5 Whys", etc.)
- Plans focused on methodology rather than user's actual questions
- Excessive JSON structure requirements

**Impact:** Plans that are methodologically sound but disconnected from user intent, creating busywork rather than targeted investigation.

### Phase 3: Execution
**Current Issues:**
- **132 lines of instructions** - the most complex phase
- User guidance context buried in the middle (line 13)
- 10+ different retrieval mechanisms described
- Mandatory "5 Whys" methodology enforcement
- 60+ lines of JSON output schema
- Language requirements take up significant space (17 lines)
- Multiple competing priorities (novelty, evidence, structure, language, etc.)

**Impact:** The AI spends cognitive effort navigating constraints rather than deeply engaging with the user's question. Output becomes formulaic and checkbox-driven.

### Phase 4: Synthesis (Final Report)
**Current Issues:**
- Rigid outline structure with mandatory sections
- Coverage matrix that must be "逐条落实"
- Prescriptive writing requirements (51 lines of instructions)
- Mandatory appendices (方法与来源说明, 证据附录)
- Specific formatting requirements for evidence citations
- Self-check list that focuses on compliance rather than usefulness
- Title must follow specific patterns ("引言：", "结语：")

**Impact:** Reports that feel templated and bureaucratic rather than insightful and relevant. The structure serves the system rather than the user.

---

## Root Cause Analysis

### 1. System-First vs User-First Design
**Problem:** The system is optimized for internal consistency and completeness rather than user satisfaction.

**Evidence:**
- Phases reference system constructs (markers, retrieval strategies, coverage matrices) more than user needs
- User guidance appears as `{user_guidance}` - a variable to be inserted rather than the foundation
- Success criteria focus on methodological rigor rather than relevance

**Why This Happened:**
- Natural evolution of a sophisticated system
- Focus on preventing AI errors and ensuring quality
- Desire to leverage advanced features (markers, semantic search)
- Academic research mindset ("proper methodology") rather than consultant mindset ("answer the client")

### 2. Over-Engineering Through Iteration
**Problem:** Each phase has accumulated layers of instructions to handle edge cases and improve quality.

**Evidence:**
- Phase 3 has grown to 132 lines
- Multiple safeguards against repetition
- Extensive JSON schemas
- Multiple retrieval mechanisms

**Why This Happened:**
- Iterative bug fixes added constraints
- Each improvement added a new section rather than simplifying existing ones
- No periodic simplification/refactoring
- "More instructions = better output" assumption

### 3. Role Rigidity
**Problem:** A single research role is locked in at the start and becomes a constraint.

**Evidence:**
- Phase 0.5 generates role based on data characteristics
- Role persists unchanged through all phases
- "你是{system_role_description}" repeated at the start of every phase

**Why This Happened:**
- Attempt to give AI consistent persona/expertise
- Belief that expertise focus improves quality
- Lack of mechanism to adapt perspective as research evolves

---

## Improvement Strategy

### Guiding Principles

1. **User Intent First, Always**
   - Every prompt should start with user's question
   - Methodological guidance should serve user intent, not overshadow it
   - Success = "Did we answer what the user actually wanted to know?"

2. **Simplicity Through Constraint Removal**
   - Remove rather than add
   - Trust the AI to be intelligent rather than prescribing every detail
   - Shorter prompts that focus on core goals

3. **Flexibility Over Structure**
   - Provide examples rather than rigid templates
   - Allow natural variation in output structure
   - Remove mandatory sections that may not always be relevant

4. **Progressive Guidance**
   - Critical guidance first, optional guidance last
   - Distinguish between "must do" and "consider doing"
   - Allow AI to make judgment calls

---

## Detailed Improvement Plans by Phase

### Phase 0.5: Role Generation → **REMOVE OR SIMPLIFY**

**Option A: Remove Entirely**
- Remove the separate role generation phase
- Let the AI naturally adopt appropriate expertise in each phase
- User intent and data context provide sufficient framing

**Option B: Convert to Lightweight Framing**
- Change from "你是[固定角色]" to "Consider relevant expertise areas:"
- Make it advisory rather than prescriptive
- Allow role to evolve across phases

**Recommended Changes:**
```markdown
## New System Prompt (if keeping the phase):

You are a research assistant helping the user explore their topic. 

Based on the data available and the user's question, consider what expertise or perspectives would be most valuable for analyzing this information. You don't need to rigidly adopt a single role - draw on relevant expertise as needed throughout the research process.

The goal is to provide insights that directly address the user's needs, not to perfectly embody a professional persona.
```

**Reduce from:** 30 lines → **10 lines**

---

### Phase 1: Discover → **MAJOR SIMPLIFICATION**

**Current Length:** ~45 lines of instructions + system prompt  
**Target Length:** ~20 lines

**Key Changes:**

1. **Reorder priorities:**
```markdown
## New Instruction Structure:

**USER'S RESEARCH TOPIC:**
{user_topic}

**USER'S GUIDANCE & PRIORITIES:**
{user_guidance}

**Available Data:**
{marker_overview}

**YOUR TASK:**
Generate research goals that directly address what the user wants to know.

Start with the user's question and think about:
- What would actually answer their question?
- What aspects are they most curious about?
- What would be most useful or surprising to them?

Then check the available data to see which goals are feasible.

Generate 5-10 specific research goals. Each should:
- Be clearly relevant to the user's question
- Be answerable with the available data
- Provide genuine insight (not just description)
```

2. **Simplify JSON output:**
   - Remove excessive field requirements
   - Focus on core: `goal_text`, `rationale`, `feasibility`
   - Remove prescriptive source/use tagging

3. **Remove marker-centric language:**
   - Less emphasis on "标记概览"
   - More emphasis on understanding content
   - Let AI judge what data is needed

**Benefits:**
- User intent is the first thing the AI sees
- Simpler mental model (question → goals → feasibility)
- Less cognitive overhead navigating system constructs

---

### Phase 1.5: Synthesize → **SIMPLIFY**

**Current Length:** ~35 lines  
**Target Length:** ~15 lines

**Key Changes:**

1. **Remove rigid format requirements:**
   - Don't force 20-character limit on comprehensive_topic
   - Remove prescriptive component_questions format
   - Let AI naturally synthesize

2. **Emphasize user language:**
```markdown
**YOUR TASK:**
Look at the research goals and create a unified research focus that:
1. Captures what the user wants to understand
2. Can be stated in the user's own terms (not academic jargon)
3. Feels natural and meaningful to the user

You're not creating a formal research proposal - you're clarifying the user's curiosity in a clear, focused way.
```

**Benefits:**
- More natural synthesis
- User-centric language
- Less bureaucratic

---

### Phase 2: Planning → **MAJOR SIMPLIFICATION**

**Current Length:** 74 lines  
**Target Length:** ~30 lines

**Key Changes:**

1. **Remove prescriptive methodology:**
   - Remove mandatory "5 Whys" requirement
   - Remove "设计哲学" section (10+ lines)
   - Remove detailed chunk_strategy requirements

2. **Simplify to core planning:**
```markdown
**USER WANTS TO UNDERSTAND:**
{selected_goal}

**COMPONENT QUESTIONS:**
{component_questions}

**USER'S PRIORITIES:**
{user_guidance}

**Available Data:**
{marker_overview}

**YOUR TASK:**
Create a simple, logical plan to answer the user's question.

Think about:
1. What information do you need to gather first?
2. What analysis would be most insightful?
3. What order makes sense?

Create 3-7 research steps. Each step should:
- Have a clear purpose tied to the user's question
- Specify what data/content is needed
- Build logically on previous steps

You don't need to prescribe exact methods - trust that during execution you'll know how to analyze effectively. Focus on *what* needs to be discovered, not *how* to discover it.
```

3. **Simplify JSON schema:**
   - Remove: marker_relevance, retrieval_strategy, chunk_strategy
   - Keep: step_id, goal, required_data, notes
   - Make most fields optional

**Benefits:**
- 60% reduction in instruction complexity
- Focus on logical flow rather than methodology
- More flexibility for AI to adapt approach

---

### Phase 3: Execution → **MAJOR OVERHAUL NEEDED**

**Current Length:** 132 lines  
**Target Length:** ~50 lines

This is the most critical phase to fix. Current version is extremely over-engineered.

**Key Changes:**

1. **Restructure priority order:**
```markdown
## NEW PRIORITY ORDER:

[FIRST - USER CONTEXT]
**What the user wants to know:**
{selected_goal}

**User's specific interests/priorities:**
{user_guidance}

[SECOND - TASK]
**Current step goal:**
{goal}

**Your task:**
Analyze the available content and provide insights that directly address this step's goal, ultimately helping answer the user's question.

[THIRD - AVAILABLE CONTENT]
{retrieved_content}

[FOURTH - CONTEXT FROM PREVIOUS STEPS]
{previous_chunks_context}

[LAST - TECHNICAL GUIDANCE]
- Write in Chinese
- Focus on new insights (check cumulative digest for what's already covered)
- Support claims with evidence
```

2. **Remove over-prescription:**
   - **Remove:** Mandatory "5 Whys" framework (takes up 10+ lines)
   - **Remove:** Detailed retrieval strategy explanations (20+ lines)
   - **Remove:** Extensive language requirement section (15+ lines - just say "输出用中文")
   - **Remove:** Rigid JSON schema with nested structures

3. **Simplify output format:**
```json
{
  "summary": "What did you discover in this step?",
  "key_findings": [
    {
      "finding": "The insight",
      "evidence": "Supporting evidence",
      "relevance": "Why this matters to the user's question"
    }
  ],
  "analysis": "Deeper exploration and reasoning (free-form)",
  "questions_raised": ["What else needs investigation?"],
  "next_step_suggestions": "What should we look at next?"
}
```

4. **Remove article requirement:**
   - Current system requires a full article in `findings.article`
   - This creates redundancy and adds pressure
   - Just ask for analysis and findings

5. **Trust the AI:**
```markdown
## Analysis Guidance:

Focus on being helpful to the user. Ask yourself:
- Does this answer their question?
- Is this insight meaningful?
- Would the user find this interesting?

Use whatever analytical approach makes sense - you don't need to follow rigid frameworks. If comparing sources is useful, do it. If deep causal analysis is needed, do that. Let the question guide the method.
```

**Benefits:**
- 60% reduction in length
- User intent is front and center
- AI has flexibility to adapt approach
- Less cognitive overhead = better analysis

---

### Phase 4: Final Synthesis → **MAJOR SIMPLIFICATION**

**Current Length:** Outline (49 lines) + Instructions (58 lines) = 107 lines  
**Target Length:** ~40 lines total

**Key Changes:**

1. **Remove rigid outline phase:**
   - **Eliminate the separate outline generation step**
   - Let AI naturally structure the report
   - Provide guidance, not templates

2. **Simplify final report prompt:**
```markdown
**USER'S ORIGINAL QUESTION:**
{selected_goal}

**WHAT THE USER CARES ABOUT:**
{user_guidance}

**RESEARCH FINDINGS:**
{phase3_summary}

**YOUR TASK:**
Write a comprehensive research report that answers the user's question.

## Report Structure (Flexible):

**Executive Summary** (2-4 key points)
- Start with the most important answers to the user's question
- What are the key takeaways?

**Main Analysis** (Organize however makes sense)
- Answer the user's question thoroughly
- Present your findings in a logical flow
- Use evidence to support your points [EVID-##]
- Don't force a rigid structure - let the findings guide organization

**Limitations & Open Questions**
- What couldn't be fully answered?
- What would need more research?

**Evidence Index** (List evidence with sources)

## Writing Guidance:

1. **User-focused:** Constantly ask "Does this answer what the user wanted to know?"
2. **Clear and direct:** Use natural Chinese, avoid jargon unless necessary
3. **Evidence-based:** Support claims with [EVID-##] references
4. **Honest:** If evidence is limited, say so
5. **Insightful:** Don't just summarize - analyze and connect ideas

## What NOT to do:
- Don't force findings into a predetermined outline
- Don't write like an academic paper unless the user wants that
- Don't pad the report with unnecessary sections
- Don't prioritize format over substance

Output: Pure Markdown, no JSON wrapper.
```

3. **Remove bureaucratic requirements:**
   - **Remove:** Coverage matrix checklist
   - **Remove:** Mandatory section titles with prescribed formats ("引言：", "结语：")
   - **Remove:** Word count targets per section
   - **Remove:** Mandatory appendix structure
   - **Remove:** Self-check compliance list

4. **Simplify evidence system:**
   - Keep [EVID-##] references (they're useful)
   - Remove prescriptive rules about where/how to use them
   - Trust AI to cite appropriately

**Benefits:**
- 60%+ reduction in complexity
- Natural, user-appropriate report structure
- AI adapts format to content rather than forcing content into format
- Report serves user needs rather than system requirements

---

## Cross-Phase Improvements

### 1. **Consistent User-First Structure**

Every phase should follow this structure:

```markdown
## Suggested Template for All Phases:

**USER'S QUESTION:**
[Most prominent, first thing AI sees]

**USER'S CONTEXT & PRIORITIES:**
[Second most prominent]

**YOUR TASK:**
[Clear, simple, focused on user value]

**AVAILABLE RESOURCES:**
[Data, previous findings, etc.]

**GUIDANCE:**
[Helpful suggestions, not rigid requirements]

**OUTPUT:**
[Simple format, fewer required fields]
```

### 2. **Remove System Role Prescription**

**Current:** "你是{system_role_description}"  
**Proposed:** "You are a research assistant helping the user understand [topic]"

Or even simpler: Just start with the task, no role declaration needed.

### 3. **Simplify JSON Schemas**

**Across all phases:**
- Reduce required fields by 50%
- Make most fields optional
- Allow free-form text fields instead of rigid structures
- Remove nested objects where possible

**Example Simplification:**
```json
// BEFORE (Phase 3):
{
  "findings": {
    "points_of_interest": {
      "key_claims": [{"claim": "...", "supporting_evidence": "..."}],
      "notable_evidence": [{"evidence_type": "...", "description": "...", "quote": "..."}],
      "controversial_topics": [{"topic": "...", "opposing_views": [], "intensity": "..."}],
      "surprising_insights": ["..."],
      "specific_examples": [{"example": "...", "context": "..."}],
      "open_questions": ["..."]
    },
    "analysis_details": {
      "five_whys": [...],
      "assumptions": [...],
      "uncertainties": [...]
    }
  }
}

// AFTER:
{
  "key_findings": [
    {
      "insight": "The main finding",
      "evidence": "Supporting evidence",
      "importance": "Why this matters to the user"
    }
  ],
  "analysis": "Free-form deeper analysis",
  "open_questions": ["What's still unclear?"]
}
```

### 4. **Consolidate Language Instructions**

**Currently:** 15-20 lines per phase explaining Chinese/translation requirements  
**Proposed:** 2-3 lines at system level

Add to system prompt once:
```markdown
**Language:** Output in Chinese. When citing non-Chinese sources, provide Chinese translation with original text in brackets if needed.
```

Remove from individual phase instructions.

### 5. **Remove Redundant Anti-Repetition Systems**

**Currently:**
- Cumulative digest
- Novelty guidance
- "禁止重复的内容"
- Multiple checks for redundancy

**Proposed:**
- Simple context: "Previous findings: [summary]"
- Single line: "Focus on new insights not already covered"
- Trust AI's natural ability to avoid repetition

---

## Implementation Approach

### Phase 1: Quick Wins (Week 1)
**Goal:** Reduce complexity by 30% without changing core logic

1. **Consolidate language instructions** → Add to system prompt, remove from phases
2. **Remove rigid role system** → Make Phase 0.5 advisory or remove entirely
3. **Simplify JSON schemas** → Remove 50% of required fields
4. **Reorder prompts** → User context first in all phases

**Files to modify:**
- `phase0_5_role_generation/system.md` - Soften or remove
- All `system.md` files - Remove "你是{role}" or make advisory
- All `instructions.md` files - Move user_context to top
- All `output_schema.json` files - Reduce required fields

### Phase 2: Core Simplification (Week 2)
**Goal:** Reduce total instruction length by 50%

1. **Phase 3 overhaul** (132 lines → 50 lines)
   - Remove 5 Whys requirement
   - Simplify retrieval explanations
   - Reduce JSON schema
   
2. **Phase 2 simplification** (74 lines → 30 lines)
   - Remove design philosophy section
   - Simplify planning requirements
   
3. **Phase 1 user-focus** (45 lines → 20 lines)
   - Deprioritize markers, prioritize user question

**Files to modify:**
- `phase3_execute/instructions.md` - Major rewrite
- `phase2_plan/instructions.md` - Major simplification
- `phase1_discover/instructions.md` - Reorder and simplify

### Phase 3: Structural Improvements (Week 3)
**Goal:** Remove rigid templates, enable flexibility

1. **Phase 4 flexible reporting**
   - Remove mandatory outline structure
   - Combine outline generation into main synthesis
   - Remove coverage matrix requirement
   
2. **Cross-phase consistency**
   - Apply user-first template to all phases
   - Ensure consistent tone and style
   
3. **System-wide cleanup**
   - Remove unused constructs
   - Consolidate redundant instructions

**Files to modify:**
- `phase4_synthesize/outline.md` - Remove or simplify drastically
- `phase4_synthesize/instructions.md` - Major rewrite
- All phases - Apply consistent structure

### Phase 4: Testing & Refinement (Week 4)
**Goal:** Validate improvements, fine-tune

1. **Test with diverse user queries**
   - Technical questions
   - Business questions
   - Exploratory research
   - Specific vs. broad topics

2. **Compare outputs**
   - Old system vs. new system
   - Measure: relevance, naturalness, user satisfaction

3. **Iterate based on results**
   - Add back critical guardrails if needed
   - Further simplify where possible

---

## Expected Outcomes

### Quantitative Improvements

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Total instruction length** | ~500 lines | ~200 lines | -60% |
| **Phase 3 complexity** | 132 lines | 50 lines | -62% |
| **Phase 4 complexity** | 107 lines | 40 lines | -63% |
| **Required JSON fields** | ~30 | ~12 | -60% |
| **Rigid structural requirements** | Many | Few | -80% |

### Qualitative Improvements

**Better User Experience:**
- Answers feel more relevant and directly address user's question
- Less bureaucratic, more natural outputs
- Reports adapt to user needs rather than following templates

**Better AI Performance:**
- Less cognitive overhead navigating complex constraints
- More freedom to apply intelligence and judgment
- Better focus on insight rather than compliance

**Easier Maintenance:**
- Simpler system = easier to understand and modify
- Fewer edge cases from rigid requirements
- Clearer purpose for each phase

---

## Risk Mitigation

### Risk 1: Quality Degradation
**Concern:** Removing guardrails might reduce output quality

**Mitigation:**
- Phase implementation with testing between phases
- Keep critical constraints (evidence citation, Chinese language, anti-repetition basics)
- Monitor outputs and add back specific guardrails if needed
- Trust that reducing cognitive load actually improves quality

### Risk 2: Output Format Inconsistency
**Concern:** Less rigid schemas might create parsing issues

**Mitigation:**
- Keep JSON schemas, just simplify them
- Maintain core required fields needed for system operation
- Use clear examples to guide format
- Update parsing code to handle more variation

### Risk 3: Missing Important Details
**Concern:** Shorter prompts might omit critical guidance

**Mitigation:**
- Review each removal carefully - is this actually needed?
- Preserve genuinely important constraints
- Use progressive disclosure (critical first, optional last)
- Test edge cases that previously had specific handling

---

## Success Metrics

### Primary Metrics
1. **User Satisfaction:** Do users feel their question was answered?
2. **Relevance Score:** How relevant are outputs to user's original intent?
3. **Naturalness:** Do outputs feel natural or templated?

### Secondary Metrics
4. **Development Velocity:** How easy is it to modify and improve prompts?
5. **AI Performance:** Are outputs insightful and well-reasoned?
6. **Error Rate:** Are there fewer format/parsing errors?

### Measurement Approach
- A/B testing: Same queries on old vs. new system
- User surveys: Which output better answers your question?
- Manual review: Blind evaluation of output quality
- System logs: Track parsing errors, failures

---

## Conclusion

The current prompt system has evolved into a sophisticated but over-engineered solution that prioritizes system methodology over user needs. By simplifying prompts, removing rigid structures, and consistently prioritizing user intent, we can create a system that:

1. **Produces more relevant research** that directly addresses user questions
2. **Enables better AI performance** by reducing cognitive overhead
3. **Creates more natural outputs** that don't feel templated
4. **Is easier to maintain and improve** through clearer, simpler design

**Core Philosophy Shift:**
- **From:** "Control the AI with detailed instructions to ensure quality"
- **To:** "Empower the AI with clear goals and trust its intelligence"

**Next Step:** Begin Phase 1 implementation with quick wins to validate approach.

---

## Appendix: Example Transformations

### Example 1: Phase 3 Instructions (Before → After)

**BEFORE (132 lines):**
```markdown
**上下文（简要）**
{scratchpad_summary}

{previous_chunks_context}

**禁止重复的内容**
{cumulative_digest}

**研究角色定位**
{research_role_section}

**用户指导与优先事项**
{user_guidance_context}

**相关内容的标记概览**
{marker_overview}

**已检索的完整内容**
{retrieved_content}

**任务（精简与创意）**
围绕步骤目标 "{goal}" 做证据驱动分析，并撰写详细研究报告。

- 在结构化报告中于"重要发现"与"深入分析"之间插入一篇完整文章，并写入 `findings.article` 字段。
- 文章需综述研究主题、明确回答当前步骤目标，并展开充分论证，确保读者单独阅读也能理解核心结论。
[... 110 more lines ...]
```

**AFTER (~50 lines):**
```markdown
**USER'S RESEARCH QUESTION:**
{selected_goal}

**USER'S PRIORITIES:**
{user_guidance_context}

---

**CURRENT STEP:**
{goal}

**AVAILABLE CONTENT:**
{retrieved_content}

**PREVIOUS FINDINGS:**
{previous_chunks_context}

---

**YOUR TASK:**
Analyze the content and provide insights that help answer the user's question.

Focus on:
- Direct relevance to the user's question
- New insights (avoid repeating: {cumulative_digest_summary})
- Evidence-based reasoning
- Clear, natural Chinese

**OUTPUT FORMAT:**
{
  "key_findings": [
    {"insight": "...", "evidence": "...", "why_this_matters": "..."}
  ],
  "deeper_analysis": "Your reasoning and interpretation",
  "open_questions": ["What's still unclear?"],
  "confidence": 0.0
}

If you need more content to complete your analysis, specify what you need and why.
```

**Key Changes:**
- User context front and center
- Removed rigid methodologies (5 Whys, article requirement)
- Simplified JSON output
- Reduced from 132 to ~50 lines
- Clearer priorities and task focus

---

### Example 2: Phase 4 Final Report (Before → After)

**BEFORE (107 lines total with outline + instructions):**
- Separate outline generation phase with rigid section requirements
- Mandatory coverage matrix
- Prescribed title formats ("引言：", "结语：")
- Word counts per section
- Multiple appendix requirements
- Self-check compliance list

**AFTER (~40 lines, no separate outline):**
```markdown
**USER ASKED:**
{selected_goal}

**YOUR RESEARCH FOUND:**
{phase3_summary}

**EVIDENCE AVAILABLE:**
{evidence_catalog}

---

**WRITE A RESEARCH REPORT:**

Start with the most important answers to the user's question.

Then organize your findings in whatever structure makes sense - could be:
- Thematic (group by topics)
- Chronological (show evolution)
- Problem-solution (show issues and answers)
- Comparative (compare perspectives)

Whatever you choose, make sure:
1. It directly answers the user's question
2. It flows logically
3. Claims are supported with [EVID-##]
4. Limitations are acknowledged

End with an evidence index.

**WRITE IN NATURAL CHINESE:**
- Clear and direct
- Professional but not bureaucratic
- Focus on insights, not just facts

Output as Markdown.
```

**Key Changes:**
- No separate outline phase
- No rigid structure requirements
- No mandatory sections or title formats
- Freedom to organize based on content
- Reduced from 107 to ~40 lines
- Focus on user value over system compliance

---

*Document Version: 1.0*  
*Created: 2025-11-12*  
*Status: Proposal - Not Yet Implemented*

