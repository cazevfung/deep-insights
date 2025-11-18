# 你的任务（只输出JSON）

基于已收集的发现（无需复述发现原文），先生成一个报告大纲（TOC），包含：
- sections: 数组，每项包含 title（标题）、target_words（建议字数500-800）、purpose（1句用途说明）、supporting_steps（数组）、supporting_evidence（数组）、notes（字符串）字段
- appendices: 必须包含 ["方法与来源说明", "证据附录"]

## 约束
- 章节应覆盖不同角度（玩家心理/行为；系统与经济机制；社区/市场/口碑；对比与争议；未来展望/建议）
- 尽可能把散落零散的点抽象成更重要的议题，形成章节
- 章节数量不宜过多，控制在3-4个章节
- 避免主题前后重复，章节要有清晰边界

## 写作时优先考虑你的style
{{> style_{writing_style}_cn.md}}

## 输出格式（必须是有效的JSON）
{{
  "sections": [
    {{
      "title": "...",
      "target_words": 700,
      "purpose": "...",
      "supporting_steps": ["step_1", "step_3"],
      "supporting_evidence": ["EVID-01", "EVID-05"],
      "notes": "..."
    }}
  ],
  "appendices": ["...", "..."]
}}

## 综合研究主题
{selected_goal}

## Phase 3 线索快照
{phase3_storyline_candidates}

## 关键论点（优先保障）
{phase3_key_claims}

## 核心证据池
{phase3_evidence_highlights}

## 争议与反对观点
{phase3_counterpoints}

## 未解问题 / 信息缺口
{phase3_open_questions}

## 组成问题对齐摘要
{component_alignment_context}

## 数据覆盖提示
{source_mix_context}

## 组成问题（如有）
{component_questions_context}
{user_amendment_context}