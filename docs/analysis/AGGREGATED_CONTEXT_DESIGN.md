# Aggregated Context Design - All Phases

## Problem Statement

Currently, contexts are passed between phases as separate fields or extracted pieces. When we update one phase's output structure, we need to update every subsequent phase that uses it. This is brittle and requires changes in multiple places.

## Solution: Structured Context Objects

Each phase should:
1. **Output structured objects** containing all related context
2. **Receive full structured objects** from previous phases
3. **Format/display what they need** for their specific task
4. **Pass forward the full object** so future phases automatically get new fields

## Context Flow

```
Phase 0.5 → research_role: {role, rationale, ...}
           ↓
Phase 1 → suggested_goals: [{goal_text, rationale, uses, sources, ...}, ...]
         ↓
Phase 1.5 → synthesized_goal: {comprehensive_topic, component_questions, unifying_theme, research_scope, ...}
           ↓
Phase 2 → research_plan: [{step_id, goal, required_data, chunk_strategy, notes, ...}, ...]
         ↓
Phase 3 → findings: [{step_id, findings: {summary, points_of_interest, ...}, insights, confidence}, ...]
         ↓
Phase 4 → (receives all above contexts)
```

## Implementation Pattern

### Pattern 1: Phase Output Structure

Each phase returns structured objects:

```python
# Phase 0.5
return {
    "research_role": {
        "role": "...",
        "rationale": "...",
        # Future: "perspective", "methodology", "key_questions", etc.
    }
}

# Phase 1
return {
    "suggested_goals": [
        {
            "id": 1,
            "goal_text": "...",
            "rationale": "...",
            "uses": [...],
            "sources": [...],
            # Future: "priority", "estimated_complexity", "dependencies", etc.
        },
        ...
    ]
}

# Phase 1.5
return {
    "synthesized_goal": {
        "comprehensive_topic": "...",
        "component_questions": [...],
        "unifying_theme": "...",
        "research_scope": "...",
        # Future: "key_assumptions", "expected_outcomes", "analysis_approach", etc.
    }
}

# Phase 2
return {
    "research_plan": [
        {
            "step_id": 1,
            "goal": "...",
            "required_data": "...",
            "chunk_strategy": "...",
            "notes": "...",
            # Future: "estimated_time", "dependencies", "validation_criteria", etc.
        },
        ...
    ]
}

# Phase 3
return {
    "findings": [
        {
            "step_id": 1,
            "findings": {
                "summary": "...",
                "points_of_interest": {...},
                "analysis_details": {...},
                "sources": [...],
                # Future: "confidence_score", "key_insights", "follow_up_questions", etc.
            },
            "insights": "...",
            "confidence": 0.8
        },
        ...
    ]
}
```

### Pattern 2: Phase Input - Receive Full Objects

Each phase should receive the FULL structured object:

```python
# Phase 1.5: Receive full Phase 1 output
def execute(self, phase1_output: Dict[str, Any], data_abstract: str):
    suggested_goals = phase1_output.get("suggested_goals", [])
    # Extract what we need, but keep full object available

# Phase 2: Receive full Phase 1.5 output
def execute(self, phase1_output: Dict[str, Any], phase1_5_output: Dict[str, Any], data_summary: Dict[str, Any]):
    suggested_goals = phase1_output.get("suggested_goals", [])
    synthesized_goal = phase1_5_output.get("synthesized_goal", {})
    # Use full objects, don't extract individual fields

# Phase 4: Receive all previous outputs
def execute(self, phase1_5_output: Dict[str, Any], phase3_output: Dict[str, Any]):
    synthesized_goal = phase1_5_output.get("synthesized_goal", {})
    findings = phase3_output.get("findings", [])
    # Use full structured objects
```

### Pattern 3: Context Formatting Helpers

Each phase should have helpers to format structured objects for prompts:

```python
# In BasePhase or helper module
def format_research_role_for_context(role_obj: Optional[Union[str, Dict]]) -> Dict[str, str]:
    """Format research_role for prompt context (backward compatible)."""
    if not role_obj:
        return {"research_role_display": "", "research_role_rationale": ""}
    
    if isinstance(role_obj, dict):
        role_name = role_obj.get("role", "")
        rationale = role_obj.get("rationale", "")
        rationale_text = f"\n**角色选择理由:** {rationale}" if rationale else ""
        return {
            "research_role_display": role_name,
            "research_role_rationale": rationale_text
        }
    else:
        # Backward compatibility
        return {
            "research_role_display": str(role_obj),
            "research_role_rationale": ""
        }

def format_synthesized_goal_for_context(goal_obj: Dict[str, Any]) -> Dict[str, str]:
    """Format synthesized_goal for prompt context."""
    topic = goal_obj.get("comprehensive_topic", "")
    questions = goal_obj.get("component_questions", [])
    theme = goal_obj.get("unifying_theme", "")
    scope = goal_obj.get("research_scope", "")
    
    # Format component questions
    questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)]) if questions else ""
    
    # Build context dict with all fields
    context = {
        "synthesized_topic": topic,
        "component_questions_list": questions_text,
        "component_questions_count": str(len(questions)),
        "unifying_theme": theme or "",
        "research_scope": scope or ""
    }
    
    # Add any new fields automatically
    for key, value in goal_obj.items():
        if key not in context and key not in ["comprehensive_topic", "component_questions"]:
            context[f"synthesized_{key}"] = str(value) if value else ""
    
    return context
```

## Benefits

1. **Automatic Propagation**: When Phase 1.5 adds a new field to `synthesized_goal`, Phase 2 automatically receives it
2. **Single Source of Truth**: Each phase's output structure is defined in one place
3. **Future-Proof**: Adding new context fields doesn't require updating every phase
4. **Backward Compatible**: Can handle both structured objects and legacy formats
5. **Type Safety**: Clear structure makes it easier to validate and document

## Migration Strategy

### Step 1: Update Phase Outputs to Return Structured Objects
- ✅ Phase 0.5: Already structured `{"role": ..., "rationale": ...}`
- ⚠️ Phase 1: Goals already structured, but return full object
- ⚠️ Phase 1.5: Already structured, ensure all fields passed forward
- ⚠️ Phase 2: Plan steps already structured
- ⚠️ Phase 3: Findings already structured

### Step 2: Update Phase Inputs to Accept Full Objects
- Phase 1.5: Accept full `phase1_output` instead of just `goals`
- Phase 2: Accept full `phase1_output` and `phase1_5_output`
- Phase 4: Accept full `phase1_5_output` and `phase3_output`

### Step 3: Add Context Formatting Helpers
- Create `research/prompts/context_formatters.py`
- Move formatting logic from individual phases to shared helpers
- All phases use helpers to format structured objects for prompts

### Step 4: Update Prompts to Use Structured Context
- Update prompt templates to reference structured context fields
- Prompts automatically get new fields when objects are updated

## Example: Phase 1.5 → Phase 2

### Before (Current):
```python
# Phase 1.5 returns
{
    "synthesized_goal": {
        "comprehensive_topic": "...",
        "component_questions": [...],
        "unifying_theme": "...",
        "research_scope": "..."
    }
}

# Agent extracts individual fields
synthesized = phase1_5_result.get("synthesized_goal", {})
comprehensive_topic = synthesized.get("comprehensive_topic", "")
component_questions = synthesized.get("component_questions", [])

# Phase 2 receives extracted fields
phase2.execute(
    suggested_goals=goals,
    synthesized_goal=synthesized,
    component_questions=component_questions  # Redundant extraction
)

# If Phase 1.5 adds "key_assumptions", Phase 2 doesn't get it automatically
```

### After (Structured):
```python
# Phase 1.5 returns full structured object
phase1_5_output = {
    "synthesized_goal": {
        "comprehensive_topic": "...",
        "component_questions": [...],
        "unifying_theme": "...",
        "research_scope": "...",
        "key_assumptions": [...]  # New field automatically available
    }
}

# Agent passes full object
phase2.execute(
    phase1_output={"suggested_goals": goals},
    phase1_5_output=phase1_5_output,  # Full object
    data_summary=data_summary
)

# Phase 2 formats what it needs, but has access to everything
def execute(self, phase1_output, phase1_5_output, data_summary):
    synthesized_goal = phase1_5_output.get("synthesized_goal", {})
    
    # Format for prompt using helper
    context = format_synthesized_goal_for_context(synthesized_goal)
    # context automatically includes "key_assumptions" if present
    
    # Can also access directly if needed
    assumptions = synthesized_goal.get("key_assumptions", [])
```

## Implementation Checklist

- [ ] Create `research/prompts/context_formatters.py` with formatting helpers
- [ ] Update Phase 0.5 to return structured `research_role` object
- [ ] Update Phase 1 to return full output object
- [ ] Update Phase 1.5 to accept full `phase1_output`
- [ ] Update Phase 2 to accept full `phase1_output` and `phase1_5_output`
- [ ] Update Phase 3 to return structured findings
- [ ] Update Phase 4 to accept full `phase1_5_output` and `phase3_output`
- [ ] Update Agent to pass full objects instead of extracting fields
- [ ] Update all prompt templates to use formatted context
- [ ] Add backward compatibility for legacy formats
- [ ] Document all structured object schemas

## Future Extensions

Once structured, we can easily add:

- `research_role`: `{role, rationale, perspective, methodology, key_questions}`
- `suggested_goals`: `[{goal_text, rationale, uses, sources, priority, estimated_complexity}]`
- `synthesized_goal`: `{comprehensive_topic, component_questions, unifying_theme, research_scope, key_assumptions, expected_outcomes, analysis_approach}`
- `research_plan`: `[{step_id, goal, required_data, chunk_strategy, notes, estimated_time, dependencies, validation_criteria}]`
- `findings`: `[{step_id, findings: {summary, points_of_interest, analysis_details, sources, confidence_score, key_insights, follow_up_questions}}]`

All new fields automatically propagate without code changes in subsequent phases!

