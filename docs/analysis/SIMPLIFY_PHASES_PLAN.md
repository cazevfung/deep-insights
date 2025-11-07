# Simplify Research Flow: Skip Phase 2 and Use Phase 1 Questions Directly

## Problem Statement

Current flow has unnecessary complexity:
1. **Phase 1.5** regenerates questions with "原始问题1将探索：" format, duplicating Phase 1 questions
2. **Phase 2** creates a research plan from synthesized goals, but loses direct connection to Phase 1 questions
3. Multiple API calls that don't add value

## Current Flow

```
Phase 1 → Generate research questions (e.g., 20 questions)
  ↓
Phase 1.5 → Regenerate questions with "原始问题1将探索：" format + create unified topic
  ↓
Phase 2 → Create research plan (generic steps, loses connection to Phase 1 questions)
  ↓
Phase 3 → Execute plan steps
  ↓
Phase 4 → Synthesize report using Phase 1.5 questions
```

## Proposed Simplified Flow

```
Phase 1 → Generate research questions (e.g., 20 questions with goal_text)
  ↓
Phase 1.5 (Modified) → Create unified topic ONLY, preserve Phase 1 questions directly
  ↓
[SKIP Phase 2] → Convert Phase 1 questions directly to steps for Phase 3
  ↓
Phase 3 → Execute steps directly addressing Phase 1 questions
  ↓
Phase 4 → Synthesize report using Phase 1 questions directly
```

## Key Changes

### 1. Modify Phase 1.5: Preserve Questions, Don't Regenerate

**Current Behavior**:
- Takes Phase 1 goals
- Regenerates questions with "原始问题1将探索：" prefix
- Creates `component_questions` array with regenerated format

**New Behavior**:
- Takes Phase 1 goals
- Extracts `goal_text` directly from Phase 1 goals
- Creates unified topic (`comprehensive_topic`) without regenerating questions
- Preserves Phase 1 questions as-is in `component_questions`

**Files to Modify**:
- `research/phases/phase1_synthesize.py` - Skip question regeneration, preserve Phase 1 questions
- `research/prompts/phase1_synthesize/instructions.md` - Remove question regeneration requirement

### 2. Skip Phase 2 Entirely: Convert Questions Directly to Steps

**Current Behavior**:
- Phase 2 creates research plan with generic steps
- Loses direct connection to Phase 1 questions

**New Behavior**:
- Skip Phase 2 API call entirely
- Convert Phase 1 questions directly to research steps for Phase 3
- Each Phase 1 question becomes a research step

**Conversion Logic**:
```python
def convert_phase1_questions_to_steps(phase1_goals: List[Dict]) -> List[Dict]:
    """Convert Phase 1 questions directly to Phase 3 steps."""
    steps = []
    for i, goal in enumerate(phase1_goals, 1):
        step = {
            "step_id": i,
            "goal": goal.get("goal_text", ""),  # Use Phase 1 question directly
            "required_data": "transcript_with_comments",  # Default
            "chunk_strategy": "sequential",  # Default
            "notes": f"直接回答Phase 1问题：{goal.get('goal_text', '')}"
        }
        steps.append(step)
    return steps
```

**Files to Modify**:
- `research/agent.py` - Skip Phase 2, convert questions directly to steps

### 3. Update Phase 4: Use Phase 1 Questions Directly

**Current Behavior**:
- Uses Phase 1.5 regenerated questions with "原始问题1将探索：" format

**New Behavior**:
- Uses Phase 1 questions directly (via phase1_5_output, but preserving original format)
- No need to use "原始问题1将探索：" prefix

**Files to Modify**:
- `research/phases/phase4_synthesize.py` - Already uses component_questions, should work with preserved format

## Implementation Details

### Phase 1.5 Modification

**File**: `research/phases/phase1_synthesize.py`

**Changes**:
```python
def execute(self, phase1_output: Dict[str, Any], data_abstract: str) -> Dict[str, Any]:
    # Extract goals from Phase 1
    all_goals = phase1_output.get("suggested_goals", [])
    
    # Extract goal_text directly - DON'T regenerate
    component_questions = [goal.get("goal_text", "") for goal in all_goals]
    
    # Create unified topic ONLY (simpler prompt, no question regeneration)
    # ... generate comprehensive_topic ...
    
    synthesized_goal = {
        "comprehensive_topic": comprehensive_topic,
        "component_questions": component_questions,  # Use Phase 1 questions directly
        "unifying_theme": unifying_theme,  # Optional
        "research_scope": research_scope  # Optional
    }
    
    return {
        "synthesized_goal": synthesized_goal,
        "component_goals": all_goals,  # Preserve original Phase 1 goals
        "raw_response": response
    }
```

**File**: `research/prompts/phase1_synthesize/instructions.md`

**Changes**:
- Remove requirement to regenerate questions with "原始问题1将探索：" format
- Simplify to only create unified topic
- Preserve Phase 1 questions as-is

### Skip Phase 2

**File**: `research/agent.py`

**Changes**:
```python
# After Phase 1.5
# SKIP Phase 2 - convert questions directly to steps
def _convert_questions_to_steps(phase1_goals: List[Dict], data_summary: Dict) -> List[Dict]:
    """Convert Phase 1 questions directly to research steps."""
    steps = []
    for i, goal in enumerate(phase1_goals, 1):
        goal_text = goal.get("goal_text", "")
        
        # Determine required_data based on goal uses
        uses = goal.get("uses", [])
        if "transcript_with_comments" in uses or "comments" in uses:
            required_data = "transcript_with_comments"
        elif "transcript" in uses:
            required_data = "transcript"
        else:
            required_data = "transcript_with_comments"  # Default
        
        # Determine chunk strategy based on data size
        total_words = data_summary.get("total_words", 0)
        if total_words > 50000:  # Large dataset
            chunk_strategy = "sequential"
        else:
            chunk_strategy = "all"
        
        step = {
            "step_id": i,
            "goal": goal_text,  # Use Phase 1 question directly
            "required_data": required_data,
            "chunk_strategy": chunk_strategy,
            "notes": f"直接回答研究问题：{goal_text}"
        }
        steps.append(step)
    
    return steps

# In agent.py, replace Phase 2 call:
# OLD: phase2_result = phase2.execute(...)
# NEW:
phase1_goals = phase1_result.get("suggested_goals", [])
plan = _convert_questions_to_steps(phase1_goals, data_summary)
phase2_result = {"research_plan": plan}  # Mock Phase 2 output for compatibility
```

### Phase 4 Compatibility

**File**: `research/phases/phase4_synthesize.py`

**Changes**:
- Already uses `component_questions` from `synthesized_goal`
- Should work with preserved Phase 1 questions (no format change needed)
- May need to adjust display format if it expects "原始问题1将探索：" prefix

## Benefits

1. **Reduced API Calls**: Skip Phase 2 entirely (saves 1 API call)
2. **Preserved Context**: Phase 1 questions used directly, no regeneration
3. **Consistency**: Questions remain consistent throughout all phases
4. **Simpler Flow**: Fewer steps, clearer connection between questions and research
5. **No Duplication**: Questions not regenerated with unnecessary prefixes

## Migration Path

1. **Phase 1**: No changes needed
2. **Phase 1.5**: Modify to preserve questions, only create unified topic
3. **Phase 2**: Skip entirely, convert questions to steps in agent.py
4. **Phase 3**: No changes needed (receives steps in same format)
5. **Phase 4**: No changes needed (uses component_questions as-is)

## Testing Checklist

- [ ] Phase 1 generates questions correctly
- [ ] Phase 1.5 preserves Phase 1 questions, creates unified topic
- [ ] Phase 2 is skipped, questions converted to steps
- [ ] Phase 3 executes steps correctly
- [ ] Phase 4 uses Phase 1 questions correctly in report
- [ ] No "原始问题1将探索：" format appears in output
- [ ] All Phase 1 questions are addressed in final report

## Files to Modify

1. `research/phases/phase1_synthesize.py` - Preserve questions, don't regenerate
2. `research/prompts/phase1_synthesize/instructions.md` - Simplify to topic creation only
3. `research/agent.py` - Skip Phase 2, convert questions to steps
4. `research/phases/phase4_synthesize.py` - Ensure compatibility with preserved format (may need minor adjustments)

## Backward Compatibility

- Phase 1 output format unchanged
- Phase 3 input format unchanged (still receives list of steps)
- Phase 4 input format unchanged (still receives phase1_5_output with component_questions)
- Only internal flow changes, external interfaces remain the same






