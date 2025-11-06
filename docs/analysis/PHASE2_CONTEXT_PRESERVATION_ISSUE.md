# Phase 2 Context Preservation Issue Analysis

## Problem Statement

Phase 2 is losing context from previous phases. While it receives the component questions from Phase 1.5, it's generating generic research steps instead of steps that directly address the specific research questions that were generated earlier.

## Current Flow

### Phase 1.5 Output
- **Input**: List of research goals from Phase 1 (e.g., 20 goals)
- **Output**: `synthesized_goal` containing:
  - `comprehensive_topic`: Unified high-level theme
  - `component_questions`: Array of all original research questions (preserved)
  - `unifying_theme`: Core theme linking all questions
  - `research_scope`: Research scope description

### Phase 2 Input
- Receives `phase1_5_output` with `synthesized_goal`
- Extracts `component_questions` from `synthesized_goal`
- Formats them in `component_questions_context` (lines 91-101 in `phase2_plan.py`)

### Phase 2 Current Behavior
- **Problem**: Generates generic analysis steps like:
  - "构建《七日世界》核心机制全景图" (Build core mechanism overview)
  - "量化玩家对关键机制的情感极性与强度" (Quantify player emotional polarity)
  - "验证机制设计与玩家行为的因果链" (Verify causal chains)
  
- **Expected**: Steps should directly address the 20 specific component questions, such as:
  - "评估《七日世界》/《Once Human》的赛季重置机制（6周周期）对玩家长期留存与建造投入意愿的影响"
  - "分析游戏核心养成系统（模组/Mod系统）是否形成'刷副本→强化→更快刷副本'的闭环疲劳"
  - etc.

## Root Cause Analysis

### 1. Instructions Not Explicit Enough
**File**: `research/prompts/phase2_plan/instructions.md`

**Current Instructions (lines 14-25)**:
```
**任务（简化计划）:**
基于选定的研究目标和标记概览，制定一个精炼、可执行的研究计划。
```

The instructions focus on:
- General analysis strategies ("洞见优先", "逻辑流程", "创新方法")
- Flexibility and evidence-driven approach
- But **NOT** explicitly requiring steps to map to component questions

### 2. Component Questions Context Provided But Not Emphasized

**File**: `research/phases/phase2_plan.py` (lines 91-101)

The code formats component questions:
```python
component_questions_context = "**需要涵盖的组成问题：**\n"
for i, question in enumerate(component_questions, 1):
    component_questions_context += f"{i}. {question}\n"
component_questions_context += "\n**重要要求：**\n"
component_questions_context += "- 研究计划必须确保所有组成问题都得到充分探索\n"
```

However, this context is added to the prompt but:
- It's not prominently placed in the instructions
- The instructions don't emphasize that **each step should directly address specific component questions**
- The instructions don't require steps to reference which component question(s) they're answering

### 3. Missing Explicit Mapping Requirement

The current instructions don't require:
- Each step to specify which component question(s) it addresses
- Steps to be organized around answering component questions
- Explicit traceability between steps and component questions

## Proposed Solutions

### Solution 1: Enhance Phase 2 Instructions (Recommended)

**Modify**: `research/prompts/phase2_plan/instructions.md`

**Changes**:
1. Add explicit requirement that steps must address component questions
2. Require each step to reference which component question(s) it addresses
3. Add guidance on organizing steps around component questions
4. Make component questions more prominent in the prompt structure

**Example Addition**:
```
**核心要求：**
- 研究计划必须直接回答所有组成问题（见下方）
- 每个步骤应该明确指定它要回答哪个或哪些组成问题
- 可以通过以下方式组织：
  * 为每个组成问题创建专门步骤，或
  * 将相关组成问题组合在单个步骤中，或
  * 创建综合步骤来回答多个相关问题

**组成问题（必须全部涵盖）：**
{component_questions_context}
```

### Solution 2: Add Step-Level Component Question Mapping

**Modify**: Phase 2 output schema to include `component_questions` field in each step

**Example**:
```json
{
  "step_id": 1,
  "goal": "...",
  "component_questions": [1, 3, 5],  // Which component questions this step addresses
  "required_data": "...",
  ...
}
```

### Solution 3: Restructure Plan Generation

**Approach**: Instead of generic analysis steps, generate steps that directly answer component questions

**Example**:
- Step 1: "回答组成问题1：评估赛季重置机制对玩家长期留存的影响"
- Step 2: "回答组成问题2：分析模组系统是否形成闭环疲劳"
- Step 3: "综合步骤：整合步骤1-2的发现，分析机制间的交互关系"

## Implementation Plan

### Phase 1: Investigation (Current)
- ✅ Identify root cause
- ✅ Document issue
- ✅ Propose solutions

### Phase 2: Implementation (Not Yet - User Requested Investigation Only)
1. Modify `research/prompts/phase2_plan/instructions.md`:
   - Add prominent section emphasizing component questions
   - Require explicit mapping between steps and component questions
   - Add examples showing how to structure steps around component questions

2. Optionally enhance Phase 2 output schema:
   - Add `component_questions` field to step schema
   - Update validation to ensure all component questions are covered

3. Test with sample research to verify:
   - All component questions are addressed
   - Steps are traceable to specific component questions
   - Context is preserved from Phase 1.5

## Files to Modify (When Implementing)

1. `research/prompts/phase2_plan/instructions.md` - Main prompt instructions
2. `research/phases/phase2_plan.py` - May need to adjust context formatting
3. `research/prompts/phase2_plan/output_schema.json` - Optional: add component_questions field

## Key Insight

The issue is that Phase 2 is treating the research plan as a general analysis workflow rather than a structured plan to answer specific research questions. The component questions are provided but not used as the primary organizing principle for the plan.

## Next Steps

User requested investigation only - no implementation yet. Ready to implement when approved.



