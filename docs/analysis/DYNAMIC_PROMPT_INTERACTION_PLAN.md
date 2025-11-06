# Dynamic Prompt Interaction Analysis & Plan

## Problem Statement

When updating prompt requirements (e.g., changing `phase1_discover` to generate 5 goals instead of 3), subsequent phases fail to adapt automatically. This is because:

1. **Prompt templates hardcode specific numbers** (e.g., "三个研究问题")
2. **Placeholders are hardcoded** (e.g., `{goal_1}`, `{goal_2}`, `{goal_3}`)
3. **Python code extracts only fixed positions** (e.g., `all_goals[0]`, `all_goals[1]`, `all_goals[2]`)
4. **Validation enforces exact counts** (e.g., `if len(all_goals) < 3`)
5. **Schema validation expects fixed array lengths** (e.g., `component_questions` must have exactly 3 items)

## Root Cause Analysis

### Affected Components

#### 1. `phase1_synthesize` - **CRITICAL ISSUE**

**Prompt Files:**
- `phase1_synthesize/system.md`: Hardcoded "三个相关的研究问题"
- `phase1_synthesize/instructions.md`: 
  - Hardcoded "三个研究问题"
  - Hardcoded placeholders: `{goal_1}`, `{goal_2}`, `{goal_3}`
  - Hardcoded references: "涵盖所有三个问题", "识别三个问题之间的内在关系"
  - JSON output example hardcodes 3 items in `component_questions`

**Python Code (`phase1_synthesize.py`):**
- Line 29-30: `if len(all_goals) < 3: raise ValueError(f"Expected 3 goals, got {len(all_goals)}")`
- Lines 33-35: Only extracts first 3 goals: `goal_1 = all_goals[0]`, `goal_2 = all_goals[1]`, `goal_3 = all_goals[2]`
- Lines 38-41: Only passes 3 goals to context
- Lines 115-116: Schema validation expects exactly 3 `component_questions`

**Schema (`phase1_synthesize/output_schema.json`):**
- No explicit length constraint, but validation code enforces 3

#### 2. `phase1_discover` - **MINOR ISSUES** (already updated but still has hardcoded references)

**Prompt Files:**
- `phase1_discover/system.md`: Mentions "提出三个不同的" (legacy reference)
- `phase1_discover/instructions.md`: 
  - Updated to "生成5个高价值" but output example still shows 5 items (this is OK, but should be dynamic)
  - Output example hardcodes 5 items in array

**Python Code:**
- Already flexible - handles any number of goals returned

#### 3. `phase2_plan` - **MINOR ISSUES**

**Prompt Files:**
- `phase2_plan/instructions.md`: 
  - Example JSON shows 3 steps (this is fine - just an example)
  - No hardcoded goal count references

**Python Code:**
- Already flexible - formats all goals dynamically via `_format_suggested_goals()`

#### 4. `phase4_synthesize` - **MINOR ISSUES**

**Prompt Files:**
- `phase4_synthesize/instructions.md`: 
  - Line 269: Example text mentions "这三个核心问题" (only in example, but should be dynamic)

#### 5. `research_role` Generation - **NEW FEATURE REQUEST**

**Current Implementation:**
- `research/agent.py` (lines 158-168): Prompts user interactively for research role
- `research/phases/phase1_discover.py`: Accepts optional `research_role` parameter
- `research/prompts/phase1_discover/instructions.md`: Shows role as "研究角色（用户提供）"

**Problem:**
- Requires user input, interrupting workflow
- Role might not be optimal for the research topic/data
- Can be skipped (None) leading to generic analysis

**Solution:**
- Create new phase (Phase 0.5: Role Generation) to automatically generate an appropriate research role
- AI analyzes data abstract and user topic to determine best research persona/role
- Generated role is then used in Phase 1

## Solution Design

### Design Principles

1. **Data-Driven Prompts**: Prompts should adapt to the actual data passed, not assume fixed counts
2. **Dynamic Template Rendering**: Use programmatic generation of placeholders/formatting
3. **Flexible Validation**: Validation should check for minimum requirements, not exact counts
4. **Backward Compatibility**: Changes should work with existing data (3 goals, 5 goals, any number)
5. **Clear Instructions**: Prompts should use generic language ("所有研究问题" instead of "三个研究问题")

### Implementation Strategy

#### Phase 0: Add Automated Role Generation

**0.1 Create New Phase for Role Generation**

- **New file**: `research/phases/phase0_5_role_generation.py` (or integrate into `phase0_prepare.py`)
  - Analyze `data_abstract` and `user_topic` to generate appropriate research role
  - Return role as string (e.g., "市场分析师", "技术研究员", "用户行为专家")
  
- **New prompt files**: `research/prompts/phase0_5_role_generation/`
  - `system.md`: Define role as research strategy expert
  - `instructions.md`: Prompt to analyze data/topic and generate role
  - `output_schema.json`: Simple schema with `research_role` string field

**0.2 Update `research/agent.py`**

- **Remove user prompt for role** (lines 158-168):
  ```python
  # BEFORE:
  research_role: Optional[str] = None
  if not non_interactive:
      try:
          research_role = self.ui.prompt_user("你希望AI以什么角色进行研究？(自由输入，留空跳过)") or None
      except Exception:
          research_role = None
  
  # AFTER:
  # Phase 0.5: Generate research role automatically
  self.ui.display_header("Phase 0.5: 生成研究角色")
  phase0_5 = Phase0_5RoleGeneration(self.client, session)
  role_result = phase0_5.execute(combined_abstract, user_topic)
  research_role = role_result.get("research_role", None)
  self.ui.display_message(f"生成的研究角色: {research_role}", "info")
  ```

**0.3 Update `phase1_discover` Prompt**

- **`phase1_discover/instructions.md`**:
  - Change from "研究角色（用户提供）" to "研究角色（AI生成）"
  - Or simply "研究角色:" (more generic)

#### Phase 1: Make `phase1_synthesize` Fully Dynamic

**1.1 Update Prompt Templates**

- **`phase1_synthesize/system.md`**: 
  - Change from "分析三个相关的研究问题" to "分析提供的研究问题" (or "分析以下研究问题")
  
- **`phase1_synthesize/instructions.md`**:
  - Replace hardcoded "三个研究问题" with "研究问题"
  - Replace hardcoded placeholders `{goal_1}`, `{goal_2}`, `{goal_3}` with dynamic list rendering
  - Use a dynamic format like `{goals_list}` that will be populated programmatically
  - Update all references from "三个问题" to "所有问题" or "提供的所有问题"
  - Update JSON example to show variable number of items

**1.2 Update Python Code (`phase1_synthesize.py`)**

- **Remove hardcoded count validation**: 
  - Change from `if len(all_goals) < 3` to `if len(all_goals) < 1` (minimum 1 goal)
  
- **Dynamic goal extraction and formatting**:
  - Instead of extracting only 3 goals, extract all goals
  - Format goals as a numbered list dynamically: `goals_list = "\n".join([f"{i+1}. {goal.get('goal_text', '')}" for i, goal in enumerate(all_goals)])`
  - Pass `goals_list` (or `goals_count`, `goals_list`) to context
  
- **Update schema validation**:
  - Change from `if len(component_questions) != 3` to `if len(component_questions) != len(all_goals)` (or just check minimum)

**1.3 Update Output Schema**

- Make schema validation flexible - check that `component_questions` length matches input goals length (or at minimum, is not empty)

#### Phase 2: Update Supporting Prompts

**2.1 Update `phase1_discover/system.md`**
- Change "提出三个不同的" to "提出多个不同的" or just remove the count

**2.2 Update `phase4_synthesize/instructions.md`**
- Update example text to use generic language instead of "这三个核心问题"

#### Phase 3: Add Dynamic Template Helper

**3.1 Create Utility Function**
- Add a helper function in `research/prompts/loader.py` or create new `research/prompts/formatters.py`:
  - `format_goals_list(goals: List[Dict]) -> str`: Formats goals as numbered list
  - `format_goals_context(goals: List[Dict]) -> Dict[str, Any]`: Creates context dict with dynamic fields

This ensures consistent formatting across phases.

### Detailed Changes Required

#### Change Set 1: `phase1_synthesize` Prompt Template

**File**: `research/prompts/phase1_synthesize/instructions.md`

**Before:**
```markdown
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
{
  "synthesized_goal": {
    "comprehensive_topic": "...",
    "component_questions": [
      "...",
      "...",
      "..."
    ],
    "unifying_theme": "...",
    "research_scope": "..."
  }
}
```

**After:**
```markdown
**研究问题：**

{goals_list}

**可用数据概览：**
{data_abstract}

**任务：**

分析以下研究问题（共 {goals_count} 个），识别它们的共同主题、相关性和可能的交叉点。然后，创建一个综合的研究主题，这个主题应该：

1. **涵盖所有问题**：确保综合主题能够回答或探索所有原始问题的核心
2. **发现深层联系**：识别这些问题之间的内在关系或共同线索
3. **提供更广阔视角**：综合主题应该比单个问题提供更全面的视角
4. **保持可行性**：综合后的主题应该仍然可以在一篇深度文章中充分探索

**重要提示：**输出中的 `component_questions` 数组长度应与输入的研究问题数量一致（共 {goals_count} 个）。

{{> json_formatting.md}}

**输出格式（必须是有效的JSON）：**
{
  "synthesized_goal": {
    "comprehensive_topic": "...",
    "component_questions": [
      // 应包含与输入研究问题数量相同的项目（{goals_count} 个）
      "...",
      "...",
      "..."
    ],
    "unifying_theme": "...",
    "research_scope": "..."
  }
}
```

#### Change Set 2: `phase1_synthesize` System Prompt

**File**: `research/prompts/phase1_synthesize/system.md`

**Before:**
```
你是一位资深的研究策略专家。你的任务是分析三个相关的研究问题，将它们综合成一个更大、更全面的研究主题，确保这个综合主题能够涵盖所有三个问题的核心内容。
```

**After:**
```
你是一位资深的研究策略专家。你的任务是分析提供的研究问题，将它们综合成一个更大、更全面的研究主题，确保这个综合主题能够涵盖所有问题的核心内容。
```

#### Change Set 3: `phase1_synthesize.py` Implementation

**File**: `research/phases/phase1_synthesize.py`

**Changes needed:**

1. **Update `execute()` method signature/docstring**:
   - Change from "all three research goals" to "all research goals"

2. **Remove hardcoded count validation**:
   ```python
   # BEFORE:
   if len(all_goals) < 3:
       raise ValueError(f"Expected 3 goals, got {len(all_goals)}")
   
   # AFTER:
   if len(all_goals) < 1:
       raise ValueError(f"Expected at least 1 goal, got {len(all_goals)}")
   ```

3. **Dynamic goal formatting**:
   ```python
   # BEFORE:
   goal_1 = all_goals[0].get("goal_text", "")
   goal_2 = all_goals[1].get("goal_text", "")
   goal_3 = all_goals[2].get("goal_text", "")
   
   context = {
       "goal_1": goal_1,
       "goal_2": goal_2,
       "goal_3": goal_3,
       "data_abstract": data_abstract,
   }
   
   # AFTER:
   goals_list = "\n".join([
       f"{i+1}. {goal.get('goal_text', '')}" 
       for i, goal in enumerate(all_goals)
   ])
   
   context = {
       "goals_list": goals_list,
       "goals_count": len(all_goals),
       "data_abstract": data_abstract,
   }
   ```

4. **Update schema validation**:
   ```python
   # BEFORE (in _validate_against_schema):
   if len(component_questions) != 3:
       raise ValueError(f"Schema validation failed: 'component_questions' must have 3 items, got {len(component_questions)}")
   
   # AFTER:
   # Store goals_count as instance variable or pass to validator
   # Validation: component_questions should match input goals count (flexible)
   expected_count = len(all_goals)  # Or pass this to validator
   if len(component_questions) != expected_count:
       self.logger.warning(
           f"'component_questions' length ({len(component_questions)}) doesn't match input goals count ({expected_count})"
       )
       # Or make it strict:
       # raise ValueError(f"'component_questions' must have {expected_count} items")
   ```

#### Change Set 4: Automated Role Generation (Enhanced Design)

**Design Improvement**: Instead of storing `research_role` as a simple string, we'll structure it as an object containing both the role name and rationale. This makes the context self-contained and future-proof for additional fields (e.g., `perspective`, `methodology`, `analysis_focus`).

**New File**: `research/phases/phase0_5_role_generation.py`

```python
"""Phase 0.5: Generate Research Role."""

from typing import Dict, Any, Optional
from research.phases.base_phase import BasePhase
from research.prompts import compose_messages, load_schema


class Phase0_5RoleGeneration(BasePhase):
    """Phase 0.5: Automatically generate appropriate research role."""
    
    def execute(
        self,
        data_abstract: str,
        user_topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate appropriate research role based on data and topic.
        
        Args:
            data_abstract: Abstract of the available data
            user_topic: Optional user-specified research topic
            
        Returns:
            Dict with generated research_role
        """
        self.logger.info("Phase 0.5: Generating research role")
        
        context = {
            "data_abstract": data_abstract,
            "user_topic": (
                f"**研究主题:**\n{user_topic}" if user_topic else ""
            ),
        }
        messages = compose_messages("phase0_5_role_generation", context=context)
        
        response = self._stream_with_callback(messages)
        
        try:
            parsed = self.client.parse_json_from_stream(iter([response]))
            role_name = parsed.get("research_role", "")
            rationale = parsed.get("rationale", "")
        except Exception as e:
            self.logger.warning(f"JSON parsing error: {e}")
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                role_name = parsed.get("research_role", "")
                rationale = parsed.get("rationale", "")
            else:
                # Fallback: extract role from text response
                role_name = response.strip()[:100]  # First 100 chars as fallback
                rationale = ""
        
        # Structure research_role as an object for future extensibility
        research_role = {
            "role": role_name,
            "rationale": rationale
        }
        
        # Store in session
        self.session.set_metadata("research_role", research_role)
        
        result = {
            "research_role": research_role,
            "raw_response": response
        }
        
        self.logger.info(f"Phase 0.5 complete: Generated role '{role_name}'")
        
        return result
```

**New File**: `research/prompts/phase0_5_role_generation/system.md`

```
你是一位资深的研究策略专家。你的任务是分析提供的数据摘要和研究主题，确定最适合进行深度研究的分析角色或视角。

一个好的研究角色应该：
1. 与研究主题密切相关
2. 适合分析可用的数据类型
3. 能够提供独特的分析视角
4. 有助于产生有价值的洞察
```

**New File**: `research/prompts/phase0_5_role_generation/instructions.md`

```markdown
**数据摘要：**
{data_abstract}

{user_topic}

**任务：**
基于提供的数据摘要和研究主题，确定一个最合适的分析角色。这个角色应该：
- 与研究主题高度相关
- 适合分析可用的数据类型（转录文本、评论、文章等）
- 能够提供专业、深入的视角
- 有助于生成高质量的研究目标和分析

角色应该是具体、专业的，例如：
- "市场研究与用户行为分析师"
- "技术产品分析师"
- "内容策略与社区研究专家"
- "游戏设计与玩家体验研究员"
- "商业策略与行业分析专家"

{{> json_formatting.md}}

**输出格式（必须是有效的JSON）：**
{
  "research_role": "具体的研究角色名称（中文，10-30字）",
  "rationale": "选择这个角色的理由（1-2句话）"
}
```

**New File**: `research/prompts/phase0_5_role_generation/output_schema.json`

```json
{
  "type": "object",
  "required": ["research_role"],
  "properties": {
    "research_role": {
      "type": "string",
      "description": "Generated research role/persona name for analysis (10-30 characters)"
    },
    "rationale": {
      "type": "string",
      "description": "Reason for choosing this role (1-2 sentences). This will be included in context for subsequent phases."
    }
  }
}
```

**Note**: The output still returns `research_role` as a string and `rationale` as a separate field, but the phase code will structure them into a dict object `{"role": "...", "rationale": "..."}` for storage and passing between phases.

**File**: `research/prompts/phase1_discover/instructions.md`

**Update to handle structured research_role:**

**Before:**
```markdown
**研究角色（用户提供）:** "{research_role}"
```

**After:**
```markdown
**研究角色:** {research_role_display}

{research_role_rationale}
```

Where `research_role_display` will be formatted from the structured object:
- If `research_role` is a dict: `research_role.get("role", "")` 
- If `research_role` is a string (backward compatibility): use string directly

And `research_role_rationale`:
- If `research_role` is a dict with rationale: `**角色选择理由:** {research_role.get("rationale", "")}`
- Otherwise: empty string
```

**File**: `research/agent.py`

**Replace lines 158-168:**

**Before:**
```python
# Role selection (interactive by default)
# Determine interactivity: allow FORCE_INTERACTIVE to override; consider TTY
env_non_interactive = os.getenv("NON_INTERACTIVE", "0").lower() in ("1", "true", "yes", "on")
force_interactive = os.getenv("FORCE_INTERACTIVE", "0").lower() in ("1", "true", "yes", "on")
non_interactive = env_non_interactive and not force_interactive
research_role: Optional[str] = None
if not non_interactive:
    try:
        research_role = self.ui.prompt_user("你希望AI以什么角色进行研究？(自由输入，留空跳过)") or None
    except Exception:
        research_role = None
```

**After:**
```python
# Phase 0.5: Automatically generate research role
self.ui.display_header("Phase 0.5: 生成研究角色")
phase0_5 = Phase0_5RoleGeneration(self.client, session)
role_result = phase0_5.execute(combined_abstract, user_topic)
research_role = role_result.get("research_role", None)
if research_role:
    # Handle both structured (dict) and legacy (string) formats
    role_display = research_role.get("role", "") if isinstance(research_role, dict) else str(research_role)
    self.ui.display_message(f"生成的研究角色: {role_display}", "info")
else:
    self.ui.display_message("未生成研究角色，将使用通用分析视角", "warning")
```

#### Change Set 5: Update Phase1Discover to Handle Structured Role

**File**: `research/phases/phase1_discover.py`

**Update `execute()` method to format structured research_role:**

```python
# BEFORE (line 40):
"research_role": research_role or "",

# AFTER:
# Format research_role for prompt context (handle both structured dict and legacy string)
if research_role:
    if isinstance(research_role, dict):
        research_role_display = research_role.get("role", "")
        research_role_rationale = research_role.get("rationale", "")
        if research_role_rationale:
            research_role_rationale = f"\n**角色选择理由:** {research_role_rationale}"
        else:
            research_role_rationale = ""
    else:
        # Backward compatibility: treat as string
        research_role_display = str(research_role)
        research_role_rationale = ""
else:
    research_role_display = ""
    research_role_rationale = ""

context = {
    "data_abstract": data_abstract,
    "user_topic": (
        f"**可选的研究主题（如果用户未指定则省略）:**\n{user_topic}" if user_topic else ""
    ) + amendment_note,
    "research_role_display": research_role_display,
    "research_role_rationale": research_role_rationale,
    "avoid_list": "",
}
```

#### Change Set 6: Supporting Prompt Updates

**File**: `research/prompts/phase1_discover/system.md`

**Before:**
```
你是一位专业的研究策略专家。你的任务是快速分析提供的资料摘要，并针对用户提出的研究主题，提出三个不同的、有洞察力且可执行的研究目标。
```

**After:**
```
你是一位专业的研究策略专家。你的任务是快速分析提供的资料摘要，并针对用户提出的研究主题，提出多个不同的、有洞察力且可执行的研究目标。
```

**File**: `research/prompts/phase4_synthesize/instructions.md`

**Change example text** (Line 269):

**Before:**
```
- **问题解答开头**："玩家对'搜打撤'游戏既爱又恨。是什么让他们上瘾？又是什么让他们沮丧？这三个核心问题将引导我们深入了解..."
```

**After:**
```
- **问题解答开头**："玩家对'搜打撤'游戏既爱又恨。是什么让他们上瘾？又是什么让他们沮丧？这些核心问题将引导我们深入了解..."
```

### Implementation Order

1. **Create `phase0_5_role_generation`** - New phase for automated role generation
   - Create new phase class and prompt files
   - Update `research/agent.py` to call role generation instead of prompting user
   - Update `phase1_discover` prompt to reflect AI-generated role

2. **Update `phase1_synthesize.py`** - Python code changes (most critical for goal count)
3. **Update `phase1_synthesize` prompts** - Template changes
4. **Update supporting prompts** - Minor fixes
5. **Test with different goal counts** - Verify 3, 5, 7 goals all work
6. **Test role generation** - Verify role is generated appropriately for different topics/data

### Testing Strategy

#### Role Generation Testing

1. **Test role generation with different topics**
   - Technical topic → Should generate technical analyst role
   - Business topic → Should generate business analyst role
   - User experience topic → Should generate UX researcher role

2. **Test role generation with different data types**
   - Video transcripts → Should consider content analyst role
   - Comments-heavy data → Should consider community analyst role
   - Article-heavy data → Should consider research analyst role

3. **Test error handling**
   - Empty data abstract → Should still generate a generic role
   - Role generation failure → Should fall back gracefully

#### Dynamic Goal Count Testing

1. **Test with 3 goals** (backward compatibility)
   - Verify existing behavior still works
   - Verify output structure matches expectations

2. **Test with 5 goals** (user's case)
   - Verify all 5 goals are passed to synthesize
   - Verify synthesized goal includes all 5 component questions

3. **Test with 7 goals** (edge case)
   - Verify system handles larger numbers gracefully

4. **Test with 1 goal** (edge case)
   - Should still work (single goal synthesis)

5. **Test error handling**
   - Empty goals list should fail gracefully
   - Invalid goal format should fail gracefully

### Migration Considerations

- **Backward Compatibility**: Existing sessions with 3 goals should continue to work
- **Data Migration**: No data migration needed - all existing data is compatible
- **Schema Changes**: Output schema validation needs to be flexible enough to accept variable lengths

### Benefits of Structured Research Role Design

1. **Self-Contained Context**: All role-related information (name, rationale, future fields) is bundled together
2. **Future-Proof**: Easy to extend with additional fields (e.g., `perspective`, `methodology`, `analysis_focus`, `key_questions`) without breaking existing code
3. **Better Context Engineering**: Rationale is automatically passed to subsequent phases, improving AI understanding
4. **Backward Compatible**: Can handle both structured (dict) and legacy (string) formats
5. **Consistent Pattern**: Can apply same pattern to other phase outputs (goals, synthesized_goal, etc.)

### Future Enhancements

1. **Aggregated Context Objects**: Implement structured context objects for ALL phases (see `AGGREGATED_CONTEXT_DESIGN.md`)
   - Phase outputs become structured objects containing all related context
   - Subsequent phases receive full objects (not extracted pieces)
   - New fields automatically propagate without code changes

2. **Dynamic Template System**: Create a more sophisticated template system that can handle dynamic lists, loops, and conditionals

3. **Context Formatting Helpers**: Centralized helpers to format structured objects for prompts (`research/prompts/context_formatters.py`)

4. **Schema Versioning**: If we need stricter validation, consider schema versioning

5. **Goal Prioritization**: If many goals are provided, could add logic to prioritize or group similar goals

6. **Automatic Goal Count Detection**: Could detect optimal number of goals based on data complexity

7. **Role Customization**: Allow user to optionally override AI-generated role or refine it

8. **Multi-Role Analysis**: Support multiple roles for different aspects of the research (e.g., technical analyst + business analyst)

9. **Role Evolution**: Allow role to evolve based on findings as research progresses

10. **Extended Context Fields**: Add fields like `perspective`, `methodology`, `key_questions` to all structured objects - they automatically flow through the pipeline

## Related Design: Aggregated Context Objects

**See also**: `docs/analysis/AGGREGATED_CONTEXT_DESIGN.md`

This plan focuses on making prompts dynamic for goal counts and role generation. However, a broader architectural improvement is to structure **all phase outputs** as aggregated context objects. This means:

1. Each phase returns a structured object containing all related context
2. Subsequent phases receive the **full structured object** (not extracted pieces)
3. When a phase adds new fields, they automatically propagate to later phases
4. Context formatting helpers extract/format what each phase needs for prompts

This pattern makes the entire system future-proof and eliminates the need to update multiple phases when adding context fields.

**Key Insight**: Apply the same structured object pattern used for `research_role` to:
- `suggested_goals` → Phase 1 output
- `synthesized_goal` → Phase 1.5 output  
- `research_plan` → Phase 2 output
- `findings` → Phase 3 output

## Summary

This plan addresses two main improvements:

### 1. Dynamic Prompt Interaction (Core Issue)

The core issue is that `phase1_synthesize` is hardcoded to expect exactly 3 goals, while `phase1_discover` has been updated to generate 5. The solution is to make `phase1_synthesize` (and any other affected phases) fully dynamic by:

1. Replacing hardcoded placeholders with dynamic list formatting
2. Updating validation to be flexible
3. Using generic language in prompts
4. Ensuring all phases adapt to the actual data passed

### 2. Automated Role Generation (New Feature)

Replace user-interactive role selection with AI-generated role based on data and topic:

1. Create new Phase 0.5 for automated role generation
2. Remove user prompt for research role
3. Generate role automatically based on data abstract and user topic
4. Use generated role in Phase 1 for more appropriate analysis

These changes will make the system truly flexible and allow prompt modifications in one phase to automatically propagate through the pipeline, while also improving workflow automation by removing manual role selection.

