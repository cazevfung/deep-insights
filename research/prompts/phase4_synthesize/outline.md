**任务**：在理解以下上下文后，仅输出一个JSON对象，定义最终文章的章节结构。目标是将研究上下文中的洞察串联成自然流畅、层层递进的分析叙事，而不是逐条重复。章节标题要一句完整的话，点题、生动、吸引眼球，不要公式化。第一个章节必须是一个Overview/引言，且内容必须提示简洁；最后一个章节必须是一个总结，且内容必须提示简洁、展望。

### 研究上下文
- 综合主题：{selected_goal}
- 组成问题（需全部覆盖）：
{component_questions_text}
- Phase 3 总结：
{phase3_overall_summary}
- Phase 3 步骤要点：
{phase3_step_synopsis}
- 关键论点与证据速览：
{phase3_key_claims}
- 争议与反对观点：
{phase3_counterpoints}
- 意外洞察 / 待补问题：
{phase3_surprising_findings}
- 证据目录（引用ID须沿用）：
{evidence_catalog}
- 用户强调的优先事项：
{user_priority_notes}

### 输出要求
请生成：
```
{{
  "sections": [
    {{
      "title": "...",
      "target_words": 650,
      "purpose": "这一章节要回答的关键问题或要传达的结论",
      "supporting_steps": ["step_1", "step_3"],
      "supporting_evidence": ["EVID-01", "EVID-05"],
      "notes": "与前后章节的衔接或需要强调的联系"
    }}
  ],
  "appendices": ["方法与来源说明", "证据附录"]
}}
```

约束：
1. 6-10个主体章节，整体应覆盖结论概览、核心机制/洞察、不同视角、风险/争议、缺口与后续方向等关键维度。
2. `title` 使用自然、专业的分析型标题，标题文案中最好能把该部分最重要的entity名词涵盖其中，以帮助读者快速get到重点；`purpose` 用一句话说明该段要解决的问题或阐明的观点，引言的标题文案就必须以"引言："为开头，结语的标题文案就必须以"结语："为开头。
3. `supporting_steps` 标明与该章节关联度最高的 Phase 3 步骤编号或组成问题（如 `step_4`、`question_2`），确保后续写作时能引用正确的上下文。
4. `supporting_evidence` 选取最关键的 `[EVID-##]` 编号或来源类型，帮助后续写作快速定位证据。
5. `notes` 可用于说明与前后章节的衔接、需要强调的对比/延展点、或整合多个步骤的逻辑。
6. 保留附录：`方法与来源说明`、`证据附录`。

仅输出有效JSON，不要添加额外文字。
```