# User Intent Implementation Summary

## Overview

统一在所有 phase 中添加了 **User Intent** 部分，包含 `user_guidance` 和 `user_context` 两个字段。这些字段根据执行阶段的不同，有不同的可用性。

## 字段可用性时间线

### user_guidance (phase_feedback_pre_role)
- **获取时间**: Phase 0.5 **之前**（在 `agent.py` 的 `run_phase0_5_role_generation` 中）
- **可用阶段**: 
  - ✅ Phase 0.5（收集阶段）
  - ✅ Phase 1 及之后的所有阶段

### user_context (phase_feedback_post_phase1 / phase1_user_input)
- **获取时间**: Phase 1 **之后**（在 `agent.py` 的 `run_phase1_discover` 中，用户提供反馈后）
- **可用阶段**:
  - ❌ Phase 0.5（此时还没有用户反馈）
  - ❌ Phase 1（执行时还没有用户反馈）
  - ❌ Phase 1.5（执行时可能还没有保存用户反馈）
  - ✅ Phase 2 及之后的所有阶段（Phase 1 之后）

## Implementation Details

### BasePhase 方法

在 `BasePhase` 中添加了 `_get_user_intent_fields()` 方法：

```python
def _get_user_intent_fields(self, include_post_phase1_feedback: bool = False) -> Dict[str, str]:
    """
    Extract user_guidance and user_context from session metadata.
    
    Args:
        include_post_phase1_feedback: If True, include user_context from Phase 1 feedback.
                                     Only set to True for phases that run AFTER Phase 1.
    
    Returns:
        Dict with 'user_guidance' and 'user_context' fields
    """
    # user_guidance is always available from Phase 0.5 onwards
    user_guidance = self.session.get_metadata("phase_feedback_pre_role", "") or ""
    
    # user_context is only available AFTER Phase 1 completes
    user_context = ""
    if include_post_phase1_feedback:
        user_context = (
            self.session.get_metadata("phase_feedback_post_phase1", "") or
            self.session.get_metadata("phase1_user_input", "") or
            ""
        )
    
    return {
        "user_guidance": user_guidance.strip() if user_guidance else "",
        "user_context": user_context.strip() if user_context else "",
    }
```

### 各 Phase 的配置

| Phase | include_post_phase1_feedback | user_guidance | user_context | 说明 |
|-------|------------------------------|---------------|--------------|------|
| Phase 0.5 | N/A | ✅ 有 | ❌ 无 | 不包含 User Intent 部分（收集阶段） |
| Phase 1 | `False` | ✅ 有 | ❌ 空 | Phase 1 执行时还没有用户反馈 |
| Phase 1.5 | `False` | ✅ 有 | ❌ 空 | Phase 1.5 执行时可能还没有保存用户反馈 |
| Phase 2 Plan | `True` | ✅ 有 | ✅ 有 | Phase 2 在 Phase 1 之后 |
| Phase 2 Synthesize | `True` | ✅ 有 | ✅ 有 | Phase 2 在 Phase 1 之后 |
| Phase 3 | `True` | ✅ 有 | ✅ 有 | Phase 3 在 Phase 1 之后 |
| Phase 4 | N/A | ✅ 有 | ✅ 有 | 通过 Phase4ContextBundle 处理 |

### Prompt 结构

所有 phase（除了 Phase 0.5）的 `instructions.md` 现在都包含：

```markdown
**你的出发点:** {research_role_display}

{research_role_rationale}

**User Intent**

{user_guidance}

{user_context}

---

[其他任务内容]
```

**优先级顺序**:
1. Research Role（你的出发点）
2. User Intent（用户意图）
3. 其他任务内容

## Backend Changes

### Phase 1 Discover
```python
user_intent = self._get_user_intent_fields(include_post_phase1_feedback=False)
context = {
    ...
    "user_guidance": user_intent["user_guidance"],
    "user_context": user_intent["user_context"],  # Will be empty for Phase 1
    ...
}
```

### Phase 1.5 Synthesize
```python
user_intent = self._get_user_intent_fields(include_post_phase1_feedback=False)
context = {
    ...
    "user_guidance": user_intent["user_guidance"],
    "user_context": user_intent["user_context"],  # Will be empty for Phase 1.5
    ...
}
```

### Phase 2 Plan & Phase 2 Synthesize
```python
user_intent = self._get_user_intent_fields(include_post_phase1_feedback=True)
context = {
    ...
    "user_guidance": user_intent["user_guidance"],
    "user_context": user_intent["user_context"],  # Available after Phase 1
    ...
}
```

### Phase 3 Execute
```python
user_intent = self._get_user_intent_fields(include_post_phase1_feedback=True)
context = {
    ...
    "user_guidance": user_intent["user_guidance"],
    "user_context": user_intent["user_context"],  # Available after Phase 1
    ...
}
```

### Phase 4 Synthesize
通过 `Phase4ContextBundle.to_prompt_context()` 处理：
```python
"user_guidance": self.user_initial_guidance or "",
"user_context": self.user_priority_notes or "",
```

## 字段来源

### user_guidance
- **来源**: `session.get_metadata("phase_feedback_pre_role", "")`
- **获取时间**: Phase 0.5 之前，用户被询问 "在生成研究角色前，你想强调哪些研究重点或背景？"
- **保存位置**: `agent.py` line 209: `session.set_metadata("phase_feedback_pre_role", pre_role_feedback or "")`

### user_context
- **来源**: 
  - `session.get_metadata("phase_feedback_post_phase1", "")` (优先)
  - `session.get_metadata("phase1_user_input", "")` (fallback)
- **获取时间**: Phase 1 之后，用户被询问 "你想如何修改这些目标？"
- **保存位置**: `agent.py` lines 281-282:
  ```python
  session.set_metadata("phase_feedback_post_phase1", post_phase1_feedback or "")
  session.set_metadata("phase1_user_input", post_phase1_feedback or "")
  ```

## 注意事项

1. **Phase 0.5**: 不包含 User Intent 部分，因为它是收集 `user_guidance` 的阶段
2. **Phase 1 和 Phase 1.5**: `user_context` 将为空字符串，这是预期的行为
3. **Phase 2 及之后**: `user_context` 可能有内容（如果用户在 Phase 1 后提供了反馈）
4. **空值处理**: 如果字段为空，prompt 中会显示空行，这是可以接受的
5. **向后兼容**: 保留了所有现有字段（如 `user_guidance_context`、`user_initial_guidance` 等）

## 验证 Checklist

- [x] BasePhase 中添加了 `_get_user_intent_fields()` 方法
- [x] Phase 1 使用 `include_post_phase1_feedback=False`
- [x] Phase 1.5 使用 `include_post_phase1_feedback=False`
- [x] Phase 2 Plan 使用 `include_post_phase1_feedback=True`
- [x] Phase 2 Synthesize 使用 `include_post_phase1_feedback=True`
- [x] Phase 3 使用 `include_post_phase1_feedback=True`
- [x] Phase 4 通过 Phase4ContextBundle 正确处理
- [x] 所有 phase 的 prompts 都包含统一的 User Intent 部分
- [x] 所有 phase 都传递了 `research_role_display` 和 `research_role_rationale`
- [x] 优先级顺序正确：Research Role > User Intent > 其他内容

## 测试建议

1. **测试 Phase 1**: 验证 `user_guidance` 有内容，`user_context` 为空
2. **测试 Phase 1.5**: 验证 `user_guidance` 有内容，`user_context` 为空
3. **测试 Phase 2**: 验证 `user_guidance` 和 `user_context` 都有内容（如果用户提供了反馈）
4. **测试 Phase 3**: 验证 `user_guidance` 和 `user_context` 都有内容
5. **测试 Phase 4**: 验证 `user_guidance` 和 `user_context` 都有内容

## 相关文件

### Prompts
- `research/prompts/phase1_discover/instructions.md`
- `research/prompts/phase1_synthesize/instructions.md`
- `research/prompts/phase2_plan/instructions.md`
- `research/prompts/phase2_synthesize/instructions.md`
- `research/prompts/phase3_execute/instructions.md`
- `research/prompts/phase4_synthesize/instructions.md`

### Backend
- `research/phases/base_phase.py` - `_get_user_intent_fields()` 方法
- `research/phases/phase1_discover.py` - 使用 `include_post_phase1_feedback=False`
- `research/phases/phase1_synthesize.py` - 使用 `include_post_phase1_feedback=False`
- `research/phases/phase2_plan.py` - 使用 `include_post_phase1_feedback=True`
- `research/phases/phase2_synthesize.py` - 使用 `include_post_phase1_feedback=True`
- `research/phases/phase3_execute.py` - 使用 `include_post_phase1_feedback=True`
- `research/phases/phase4_context.py` - 通过 Phase4ContextBundle 处理

### Agent
- `research/agent.py` - 获取和保存用户反馈的地方

---

*Last Updated: 2025-11-12*

