# Phase 2 User Input Issue Investigation

## Problem Summary

1. **User input doesn't affect Phase 2 output**: User provides input about their project (AI resume optimization service), but Phase 2 generates completely unrelated research topics (vector indexing, RAG systems, etc.)

2. **Long delay between Phase 1 user input and Phase 2**: Service takes too long to proceed from Phase 1 user input to Phase 2 research plan generation.

## Root Cause Analysis

### Issue 1: User Input Not Passed to Phase 2

**Location**: `research/agent.py` lines 232-258

**Flow**:
1. After Phase 1 generates goals, user is prompted: `"你想如何修改这些目标？(自由输入，留空表示批准并继续)"` (line 232)
2. User provides input (`amend` variable)
3. If `amend` is provided, Phase 1 is called again with `amendment_feedback=amend` (lines 235-241)
4. **Phase 2 is called at line 258**: `phase2_result = phase2.execute(phase1_result, combined_abstract)`
5. **Problem**: Phase 2 only receives:
   - `phase1_output` (the goals)
   - `data_abstract` (the data summary)
   - **NO user input is passed**

**Code Evidence**:
```python
# research/agent.py:258
phase2_result = phase2.execute(phase1_result, combined_abstract)
```

**Phase 2 Implementation** (`research/phases/phase2_synthesize.py`):
- Line 51-56: Context only includes:
  - `goals_list`
  - `goals_count`
  - `data_abstract`
- **No user input variable**

**Phase 2 Prompt Template** (`research/prompts/phase2_synthesize/instructions.md`):
- Only uses: `{goals_list}`, `{goals_count}`, `{data_abstract}`
- **No user input or user topic variable**

### Issue 2: User Topic Not Passed from Workflow

**Location**: `tests/test_full_workflow_integration.py` line 292

**Problem**: `user_topic` is hardcoded to `None`:
```python
result = agent.run_research(
    batch_id=batch_id,
    user_topic=None  # Let AI discover goals naturally
)
```

**Impact**: Even if the user provided a topic initially, it's not being passed through the workflow.

### Issue 3: Phase 2 Prompt Doesn't Include User Context

**Current Phase 2 Prompt Template** (`research/prompts/phase2_synthesize/instructions.md`):
```
**研究问题（共{goals_count}个）：**

{goals_list}

**可用数据概览：**
{data_abstract}
```

**Missing**: 
- User's original research topic/context
- User's amendment feedback
- User's project description

## Expected Behavior

When user provides input like:
> "我在做一个 AI 简历优化与职位推荐服务，通过对话理解用户经历并匹配理想工作。我不会编码，也没有in…ng 如何提升对话理解、简历生成和人岗匹配的效果与效率。我希望报告可以从简入深的，提供合适的建议。"

Phase 2 should:
1. Receive this user input
2. Use it to synthesize goals that are relevant to the user's project
3. Generate a research plan that addresses the user's specific needs

## Current Behavior

Phase 2:
1. Receives only Phase 1 goals (which may be unrelated to user's project)
2. Synthesizes based solely on goals and data abstract
3. Generates generic research topics unrelated to user's input

## Delay Issue

**Possible causes**:
1. **Phase 2 API call is slow** (line 59 in `phase2_synthesize.py`: `response = self._stream_with_callback(messages)`)
   - No progress messages during synthesis
   - Large context being sent to API (goals_list + data_abstract)
   
2. **No progress indication during Phase 2 synthesis**
   - User sees "Phase 2: 综合研究主题" but no updates during actual synthesis
   - Only sees completion message after API call finishes
   
3. **Blocking operations in the prompt_user flow**
   - `prompt_user()` blocks for up to 300 seconds waiting for user input (line 276 in `websocket_ui.py`)
   - Small 0.1s delay before waiting (line 270) - not significant
   - However, this shouldn't cause delay AFTER user provides input

**Most Likely Cause**: Phase 2 API call takes a long time because:
- Large `data_abstract` being sent
- No streaming progress updates during synthesis
- AI model needs time to synthesize multiple goals into unified topic

## Files Involved

1. **`research/agent.py`** (lines 232-258)
   - User input collection
   - Phase 2 invocation (missing user input parameter)

2. **`research/phases/phase2_synthesize.py`** (lines 12-102)
   - Phase 2 execution
   - Context building (missing user input)

3. **`research/prompts/phase2_synthesize/instructions.md`**
   - Prompt template (missing user input variables)

4. **`tests/test_full_workflow_integration.py`** (line 292)
   - `user_topic=None` hardcoded

5. **`backend/app/services/workflow_service.py`** (line 749)
   - `run_research_agent` call (no user_topic parameter)

## Recommended Fixes (Not Implemented - Investigation Only)

### Fix 1: Pass User Input to Phase 2
- Modify `phase2.execute()` to accept `user_input` or `user_topic` parameter
- Update `agent.py` line 258 to pass user input
- Update Phase 2 context to include user input

### Fix 2: Update Phase 2 Prompt Template
- Add `{user_input}` or `{user_topic}` variable to prompt template
- Include user context in synthesis instructions

### Fix 3: Pass User Topic Through Workflow
- Modify `run_research_agent()` to accept `user_topic` parameter
- Update workflow service to pass user topic from frontend
- Store user topic in session metadata

### Fix 4: Add Progress Indicators
- Add progress messages during Phase 2 synthesis
- Show "正在综合研究主题..." message

## Investigation Date
2025-01-06

## Status
Investigation complete - root causes identified. Implementation deferred per user request.

