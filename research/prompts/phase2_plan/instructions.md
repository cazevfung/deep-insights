**User Intent**
{user_guidance}
{user_context}

**原始研究目标（来自Phase 1）：**
{suggested_goals_list}

**综合研究主题（来自Phase 1.5）：**
{synthesized_goal_context}

**可用数据:** 转录本/文章、评论、元数据（来自 {sources_list}）。

**相关内容的标记概览:**
{marker_overview}

**任务（简化计划）:**
基于选定的研究目标和标记概览，制定一个精炼、可执行的研究计划。

**标记说明:**
- 每个标记对应内容项中的具体信息点
- 你可以通过标记快速判断哪些内容项对每个研究步骤最有价值
- 在研究计划中，请明确指定：
  * 每个步骤需要哪些内容项 (link_id)
  * 需要哪些类型的标记信息 (facts/opinions/datapoints)
  * 是否需要完整的转录/评论内容，还是仅需标记已足够

聚焦于实现目标所需的最小充分步骤。强调灵活性与证据驱动，不做过度模板化设计。请思考，要揭示深层理解，什么才是最具逻辑和洞察力的分析逻辑、如何才能充分分析议题？

请输出一个JSON对象，包含一个按优先级排序的精简步骤列表。每个步骤应包含：
- step_id: 整数
- goal: 该步骤要达成的明确目标
- required_content_items: ["link_id1", "link_id2", ...]  # 需要的内容项（可选）
- required_data: 从 ['transcript','transcript_with_comments','metadata','previous_findings'] 中选择
- marker_relevance: ["FACT: X", "OPINION: Y", ...]  # 相关的标记（可选）
- retrieval_strategy: "markers_only" | "full_content" | "selective_by_markers"  # 检索策略
- chunk_strategy: 从 ['all','sequential','semantic_chunks'] 中选择（必要时）
- notes: 简要说明此步骤的关键方法/评估标准（可空）

**设计哲学 (你的指导原则):**
- **洞见优先:** 不要只罗列任务。每一步都应旨在产出一个具体、有价值的洞见。
- **逻辑流程:** 计划应能讲述一个故事。第1步的发现如何为第2步的分析赋能？r
- **创新方法:** 超越简单的信息提取。你能比较不同来源吗？你能识别未言明的假设吗？你能发现那些*没有被提及*的内容吗？
- **清晰至上:** `method_description` 必须 unambiguous，以便另一个AI可以在没有额外上下文的情况下完美执行。

**输出示例 (此示例展示了一个更详细、多步骤的分析流程，旨在鼓励AI生成更精细的计划):**
```json
{{
  "research_plan": [
    {{
      "step_id": 1,
      "goal": "建立基础性理解",
      "required_data": "transcript",
      "chunk_strategy": "sequential",
      "notes": "高层次扫描，识别结构大纲和中心论点"
    }},
    {{
      "step_id": 2,
      "goal": "提取关键证据点",
      "required_data": "transcript_with_comments",
      "chunk_strategy": "all",
      "notes": "比较不同来源的观点与数据"
    }},
    {{
      "step_id": 3,
      "goal": "识别深层模式",
      "required_data": "previous_findings",
      "chunk_strategy": "all",
      "notes": "综合前两步发现，找出未言明的假设"
    }}
  ]
}}


