**任务**：基于以下上下文撰写完整的研究文章。仅输出 Markdown 正文（禁止输出 JSON 或额外说明）。文章必须系统性地回答全部研究目标，并引用证据目录中的 `[EVID-##]`。

{{> style_consultant_cn.md}}

### 大纲与覆盖约束
- 大纲（可自由改写标题词汇以适配叙事，但不得新增/删除核心章节；需保持与原大纲呼应）：  
`{outline_json}`
  - `supporting_steps` 与 `supporting_evidence` 指示每章应优先引用的 Phase 3 步骤及证据。
  - `notes` 提供章节之间的衔接提示，可在写作时作为过渡参考。
- 覆盖矩阵（必须逐条落实）：  
`{coverage_json}`

### 研究上下文
- 综合主题：{selected_goal}
- 组成问题清单：
{component_questions_text}
- 组成问题与Phase 3 对齐提示：
{goal_alignment_table}
- Phase 3 核心摘要：
{phase3_overall_summary}
- Phase 3 步骤概览：
{phase3_step_synopsis}
- 关键论点与争议线索：
{phase3_key_claims}
{phase3_counterpoints}
- 意外洞察与仍待解决的问题：
{phase3_surprising_findings}
{phase3_open_questions}
- 证据目录（引用ID必须沿用）：  
{evidence_catalog}
- 用户优先事项/补充说明：  
{user_priority_notes}
- 结构化发现原文（可直接引用细节）：  
{scratchpad_digest}
- Phase 3 全量输出（JSON）：  
{phase3_full_payload}

### 写作要点
1. **开篇**：以2-4条要点概述最重要的结论、驱动因素与建议，点明报告整体视角。
2. **结构**：依照大纲顺序展开，可以根据需要调整标题措辞，但须保留章节意图，并在正文中自然承接 `notes` 中的衔接提示。
3. **链接步骤**：写作时优先引用 `supporting_steps` 对应的发现，明确说明各步骤之间的关联、演进或对比，避免逐条罗列。
4. **证据引用**：所有分析性陈述需配套 `[EVID-##]`。如同一证据支撑多个观点，可复用。
5. **语气**：保持前几阶段一致的专业、克制、分析型语调；使用自然中文，重点阐释推理与洞察，不刻意追求文学化描写。
6. **覆盖检查**：确保 `coverage_json` 中的每个 `goal`、`open_questions_to_address` 均被回答或标注缺口，并在缺口处注明后续建议或需要的数据。
7. **附录**：结尾包含 `## 方法与来源说明`（≥400字，说明数据来源/检索方式/局限）与 `## 证据附录`（≥800字，列出每个 `[EVID-##]` 的摘要与来源线索）。正文语调保持一致，附录可更精炼。
8. **缺口提示**：若证据不足，请在对应章节最后增加“缺口与下一步”小节，列出建议补充的信息或验证方向。
9. **辅助产出（可选）**：若 `auxiliary_artifacts_required` = "yes"，在附录后追加：
   - `## FAQ`：至少5条问答，引用现有证据回应决策者可能的追问。
   - `## Slide Bullet Pack`：5-7条汇报用要点，每条附带 `[EVID-##]`。

### 简要自检
- 是否覆盖所有组成问题与覆盖矩阵中的条目？
- 每个章节是否体现了多个步骤之间的联系而非简单复述？
- 关键结论、风险、争议与假设是否明确标注证据来源？
- 正文（不含附录）信息量是否充足，如证据有限是否已说明原因？

输出：仅返回 Markdown 正文，不额外解释，也不要输出 JSON。
