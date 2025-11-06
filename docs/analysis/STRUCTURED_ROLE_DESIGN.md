# Structured Research Role Design Enhancement

## Problem Statement

Currently, `research_role` is stored as a simple string. When we want to pass additional context from Phase 0.5 (like `rationale`) to Phase 1, we need to update multiple places and potentially break backward compatibility.

## Solution: Structured Role Object

Instead of storing `research_role` as a string, we'll structure it as an object/dict containing:
- `role`: The role name (string)
- `rationale`: The reasoning for choosing this role (string)
- Future fields can be easily added (e.g., `perspective`, `methodology`, `key_questions`)

## Benefits

1. **Self-Contained Context**: All role-related information is bundled together
2. **Future-Proof**: Easy to extend without breaking existing code
3. **Better Context Engineering**: Rationale automatically flows to subsequent phases
4. **Backward Compatible**: Can handle both structured (dict) and legacy (string) formats
5. **Consistent Pattern**: Can apply same pattern to other phase outputs

## Implementation

### Phase 0.5: Return Structured Format

```python
# Structure research_role as an object
research_role = {
    "role": role_name,        # e.g., "市场研究与用户行为分析师"
    "rationale": rationale   # e.g., "基于视频转录和评论数据，需要从市场角度分析用户行为模式"
}
```

### Phase 1: Handle Structured Format

```python
# Format research_role for prompt context (backward compatible)
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
```

### Prompt Template Update

```markdown
**研究角色:** {research_role_display}

{research_role_rationale}
```

This way:
- Role name appears clearly
- Rationale provides context automatically
- Empty string if no rationale (clean)
- Works with both structured and legacy formats

## Future Extensions

The structured format makes it easy to add fields later:

```python
research_role = {
    "role": "市场研究与用户行为分析师",
    "rationale": "基于视频转录和评论数据...",
    "perspective": "analytical",  # New field
    "methodology": "mixed",       # New field
    "key_questions": [            # New field
        "用户如何与产品互动？",
        "什么因素影响用户决策？"
    ]
}
```

All subsequent phases automatically get the new context without code changes - just template updates!

## Migration Path

1. Phase 0.5 returns structured format
2. Phase 1 handles both structured (dict) and legacy (string) formats
3. Gradually migrate any legacy string roles to structured format
4. Future phases can assume structured format

