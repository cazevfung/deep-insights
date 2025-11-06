**上下文（简要）**
{scratchpad_summary}

{previous_chunks_context}

**相关内容的标记概览**
{marker_overview}

**已检索的完整内容**
{retrieved_content}

**任务（精简与创意）**
围绕步骤目标 "{goal}" 做证据驱动分析。

**语言要求（重要）:**
- **所有输出必须使用中文**：无论源内容使用何种语言（英语、日语、韩语等），所有分析结果、摘要、洞察、论点、证据描述等都必须用中文表述。
- **跨语言术语引用**：当遇到专业术语、专有名词、品牌名称或关键概念时：
  - 优先使用中文表述，并在首次出现时提供原文（括号标注）
  - 示例：`机器学习（Machine Learning）`、`用户体验（User Experience, UX）`、`生成式人工智能（Generative AI）`
  - 对于没有标准中文翻译的术语，使用中文音译或描述性翻译，并附原文
  - 示例：`ChatGPT`、`Transformer架构`、`强化学习（Reinforcement Learning）`
- **引用原文的处理**：
  - 在`quote`字段中，如果原文是外文，保留原文并添加中文翻译
  - 格式：`"原文内容（中文翻译）"` 或 `"中文翻译[原文: Original Text]"`
  - 在`supporting_evidence`、`description`等字段中，优先使用中文，必要时提供原文对照
- **一致性**：确保整个输出中同一术语的中文表述保持一致

**标记说明:**
- 标记概览显示了所有可用内容项中的关键信息点
- 你可以通过标记快速判断哪些内容项对当前步骤最有价值
- 如果需要更多上下文，可以请求完整的内容项

**检索能力说明:**
你可以通过以下方式请求更多内容：
1. 请求完整内容项: 指定 link_id 和内容类型 (transcript/comments/both)
2. 基于标记检索: 指定相关标记，系统会检索包含该标记的完整上下文
3. 按话题检索: 指定话题领域，系统会检索相关内容

请分析可用的标记，然后：
- 如果需要更多上下文来完成分析，请在 `requests` 字段中明确请求
- 如果标记已足够，直接进行分析

以主要内容（转录/文章）为锚；评论仅用于验证与发现争议。优先采用"5 Whys"方法深入原因链，保持创意与灵活性，避免模板化与重复。

方法要点：
- 5 Whys：围绕核心现象连续追问“为什么”，记录原因链，直到可行动的根因层级。
- 矛盾与空白：主动标注矛盾、缺失与不确定；区分事实与推断。
- 非重复：同一点只表述一次，后续请做交叉引用。

{{> json_formatting.md}}

**输出（必须是有效JSON）**
{{
  "step_id": 1,
  "requests": [
    {{
      "id": "req_1",
      "request_type": "full_content_item",
      "source_link_id": "link_id_1",
      "content_types": ["transcript", "comments"],
      "reason": "需要完整内容以深入分析标记 'FACT: X' 的相关证据链",
      "priority": "high"
    }},
    {{
      "id": "req_2",
      "request_type": "by_marker",
      "marker_text": "FACT: 玩家留存率在赛季重置后下降了30%",
      "source_link_id": "link_id_1",
      "content_type": "transcript",
      "context_window": 2000,
      "reason": "需要该事实标记的完整上下文以了解细节"
    }},
    {{
      "id": "req_3",
      "request_type": "by_topic",
      "topic": "排名系统",
      "source_link_ids": ["link_id_1", "link_id_2"],
      "content_types": ["transcript", "comments"],
      "limit_items": 2,
      "reason": "需要所有关于排名系统的讨论内容"
    }}
  ],
  "missing_context": [
    {{"need": "...", "source": "transcript|comments|metadata", "search_hint": "..."}}
  ],
  "findings": {{
    "summary": "本步骤的核心发现（避免重复，聚焦结论+关键证据）。所有输出必须使用中文，即使源内容为其他语言。",
    "points_of_interest": {{
      "key_claims": [{{"claim": "核心论点（中文表述，必要时附原文）", "supporting_evidence": "支持证据（中文，原文引用需标注）"}}],
      "notable_evidence": [{{"evidence_type": "quote|data|example", "description": "证据描述（中文）", "quote": "原文引用（如需，格式：原文（中文翻译））"}}],
      "controversial_topics": [{{"topic": "争议话题（中文）", "opposing_views": ["观点1（中文）", "观点2（中文）"], "intensity": "high|medium|low"}}],
      "surprising_insights": ["意外洞察（中文表述）"],
      "specific_examples": [{{"example": "具体例子（中文，术语附原文）", "context": "上下文说明（中文）"}}],
      "open_questions": ["开放问题（中文）"]
    }},
    "analysis_details": {{
      "five_whys": ["为什么1: ...（中文）", "为什么2: ...（中文）", "为什么3: ...（中文）", "为什么4: ...（中文）", "为什么5: ...（中文）"],
      "assumptions": ["假设1（中文）", "假设2（中文）"],
      "uncertainties": ["不确定性1（中文）", "不确定性2（中文）"]
    }}
  }},
  "insights": "关键洞察（一句话要点，必须使用中文）",
  "confidence": 0.0
}}


