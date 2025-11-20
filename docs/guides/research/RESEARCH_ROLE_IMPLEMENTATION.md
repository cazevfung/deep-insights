# Research Role Implementation Documentation

## Overview

Research Role 系统用于为每个研究任务提供灵活的思考视角和出发点，而不是固定的专业角色身份。系统设计强调开放性和适应性，让 AI 根据具体问题灵活调整思考方式。

## 设计理念

### 核心原则
- **灵活性优先**: 不锁定固定的专业角色，允许根据问题调整视角
- **问题导向**: 让问题本身引导思考方式，而不是预设的身份
- **用户中心**: 以用户意图为核心，提供有价值的洞察

### 关键转变
- **从**: "你是XX分析师"（固定角色）
- **到**: "你的出发点是..."（灵活的思考视角）

## Phase 0.5: Role Generation

### 系统提示 (`system.md`)
```
你的出发点是{system_role_description}。{research_role_rationale}
你的任务是思考如何最好地帮助用户了解他们的处境，并按此提供洞察思路。

不需要设定固定的专业角色或身份。重点是：
- 理解用户的处境、想了解什么
- 思考什么样的视角和方法能提供有价值的洞察思路
- 保持开放灵活，让问题本身引导思考方式
```

### 任务指令 (`instructions.md`)
```
**数据摘要：**
{data_abstract}
{user_guidance}

**任务：**
以用户intent为核心，思考如何最好地帮助用户理解面临的问题，切身处地从用户intent出发，简单描述：
- 用户想了解什么类型的问题？
- 什么样的思考方式或知识背景会有帮助？
- 应该关注哪些方面来给用户有价值的答案？

**输出格式（必须是有效的JSON）：**
{
  "research_role": "用自然的语言描述：面对这个问题，应该关注什么、从哪些角度思考会有帮助",
  "rationale": "为什么这样的思考方式能帮用户得到有价值的答案"
}
```

### 输出 Schema (`output_schema.json`)
```json
{
  "type": "object",
  "required": ["research_role"],
  "properties": {
    "research_role": {
      "type": "string",
      "description": "Generated role/persona for analysis"
    },
    "rationale": {
      "type": "string",
      "description": "Reason for choosing this role"
    }
  }
}
```

## Phase 1-4: Role Usage

### 系统提示格式（所有 Phase）

所有 phase 的 `system.md` 都使用统一格式：

```
你的出发点是{system_role_description}。{research_role_rationale}
```

**变量说明**:
- `{system_role_description}`: 从 Phase 0.5 生成的 `research_role` 字段值
- `{research_role_rationale}`: 从 Phase 0.5 生成的 `rationale` 字段值（已格式化）

### Instructions 中的处理

**当前实现**: Research Role 信息**不在** `instructions.md` 中显示，只在 `system.md` 中通过 `{system_role_description}` 和 `{research_role_rationale}` 传递。

**优先级顺序**（在 instructions.md 中）:
1. **User Intent** (user_guidance + user_context)
2. 其他任务相关内容

## Backend 实现

### 字段格式化 (`context_formatters.py`)

`format_research_role_for_context()` 函数处理 research_role 对象：

```python
def format_research_role_for_context(role_obj: Optional[Union[str, Dict[str, Any]]]) -> Dict[str, str]:
    """
    Format research_role for prompt context.
    
    Returns:
        Dict with:
        - 'research_role_display': 角色名称（用于显示）
        - 'research_role_rationale': 格式化的理由（带标题）
        - 'system_role_description': 用于 system prompt 的描述
    """
```

**处理逻辑**:
- 如果 `role_obj` 是字典: 提取 `role` 和 `rationale`
- 如果 `role_obj` 是字符串: 向后兼容处理
- 如果 `role_obj` 为空: 返回默认值 "资深数据分析专家"

**Rationale 格式化**:
- 如果有 rationale，格式化为: `"\n**角色选择理由:** {rationale}"`
- 如果没有，返回空字符串

### 各 Phase 的使用

所有 phase（Phase 1 及之后）都通过以下方式获取和传递 research role：

```python
from research.prompts.context_formatters import format_research_role_for_context

research_role = self.session.get_metadata("research_role") if self.session else None
role_context = format_research_role_for_context(research_role)

context = {
    "system_role_description": role_context["system_role_description"],
    "research_role_display": role_context["research_role_display"],  # 当前未在 instructions 中使用
    "research_role_rationale": role_context["research_role_rationale"],
    ...
}
```

## 数据流

### Phase 0.5 → Phase 1-4

1. **Phase 0.5 生成**:
   ```json
   {
     "research_role": "关注用户体验痛点和实际使用场景",
     "rationale": "因为用户想了解产品在实际使用中的问题"
   }
   ```

2. **保存到 Session**:
   ```python
   self.session.set_metadata("research_role", {
       "role": "关注用户体验痛点和实际使用场景",
       "rationale": "因为用户想了解产品在实际使用中的问题"
   })
   ```

3. **Phase 1-4 使用**:
   - `system_role_description` = "关注用户体验痛点和实际使用场景"
   - `research_role_rationale` = "\n**角色选择理由:** 因为用户想了解产品在实际使用中的问题"
   - 在 `system.md` 中显示为: "你的出发点是关注用户体验痛点和实际使用场景。\n**角色选择理由:** 因为用户想了解产品在实际使用中的问题"

## 关键设计决策

### 1. 不在 Instructions 中显示 Research Role

**决策**: Research Role 信息只在 `system.md` 中传递，不在 `instructions.md` 中显示。

**原因**:
- System prompt 已经提供了足够的上下文
- Instructions 应该专注于任务本身，而不是角色定义
- 减少重复，保持 prompts 简洁

### 2. 使用 "你的出发点是" 而非 "你是"

**决策**: 所有 system prompts 使用 "你的出发点是{system_role_description}"

**原因**:
- 强调这是思考的起点，而非固定身份
- 允许 AI 在分析过程中灵活调整视角
- 更符合"问题导向"而非"角色导向"的设计理念

### 3. Rationale 格式化

**决策**: Rationale 在 system prompt 中格式化为 `\n**角色选择理由:** {rationale}`

**原因**:
- 提供上下文，帮助 AI 理解为什么选择这个视角
- 保持格式一致性
- 如果 rationale 为空，不会显示（空字符串）

## 当前状态

### System Prompts
- ✅ 所有 phase 的 `system.md` 都使用: `你的出发点是{system_role_description}。{research_role_rationale}`
- ✅ Phase 0.5 有额外的指导原则说明

### Instructions
- ✅ 所有 phase 的 `instructions.md` **不包含** research role 信息
- ✅ 直接以 User Intent 开始
- ✅ 保持简洁，专注于任务本身

### Backend
- ✅ `format_research_role_for_context()` 统一处理所有格式转换
- ✅ 所有 phase 都通过 session metadata 获取 research_role
- ✅ 向后兼容：支持字典和字符串格式

## 相关文件

### Prompts
- `research/prompts/phase0_5_role_generation/system.md` - Phase 0.5 系统提示
- `research/prompts/phase0_5_role_generation/instructions.md` - Phase 0.5 任务指令
- `research/prompts/phase0_5_role_generation/output_schema.json` - Phase 0.5 输出格式
- `research/prompts/phase1_discover/system.md` - Phase 1 系统提示
- `research/prompts/phase2_plan/system.md` - Phase 2 系统提示
- `research/prompts/phase3_execute/system.md` - Phase 3 系统提示
- `research/prompts/phase4_synthesize/system.md` - Phase 4 系统提示

### Backend
- `research/prompts/context_formatters.py` - `format_research_role_for_context()` 函数
- `research/phases/phase0_5_role_generation.py` - Phase 0.5 执行逻辑
- `research/phases/phase1_discover.py` - Phase 1 使用 research_role
- `research/phases/phase2_plan.py` - Phase 2 使用 research_role
- `research/phases/phase3_execute.py` - Phase 3 使用 research_role
- `research/phases/phase4_context.py` - Phase 4 使用 research_role

## 示例

### Phase 0.5 输出示例
```json
{
  "research_role": "关注用户实际使用中的痛点和体验问题",
  "rationale": "因为用户想了解产品在实际使用中的问题，需要从用户体验角度分析"
}
```

### Phase 1-4 System Prompt 示例
```
你的出发点是关注用户实际使用中的痛点和体验问题。
**角色选择理由:** 因为用户想了解产品在实际使用中的问题，需要从用户体验角度分析
```

### 格式化后的 Context
```python
{
    "system_role_description": "关注用户实际使用中的痛点和体验问题",
    "research_role_display": "关注用户实际使用中的痛点和体验问题",
    "research_role_rationale": "\n**角色选择理由:** 因为用户想了解产品在实际使用中的问题，需要从用户体验角度分析"
}
```

---

*Last Updated: 2025-11-12*  
*Status: Current Implementation - No Changes Needed*

