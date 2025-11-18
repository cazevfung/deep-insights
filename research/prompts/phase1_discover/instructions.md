# 你的任务

基于可用内容标记概览，生成 5-10 个高价值、互不重复的研究问题（中文输出）。

## 生成流程（请在 thinking 中完成）

### 第一步：发散思考阶段
- 在 thinking 中，先不受限制地思考，从多个角度生成尽可能多的候选研究问题（建议 15-25 个）
- 探索不同的 who/what/when/where/why/how 角度
- 考虑不同层次、维度、时间跨度的问题
- 不要过早筛选，先充分发散思考

### 第二步：筛选综合阶段
- 从第一步的候选问题中，筛选并综合成 7-10 个最核心、最有价值的问题
- 优先保留最能直接回应用户需求的问题
- 合并相似或重叠的问题
- 确保问题涵盖核心研究维度
- 去除那些虽然有趣但缺乏深度或可操作性的问题

## 最终输出要求
- 问题数量：严格控制在 7-10 个之间
- 目标应具体、可检验，明确预期产出；与可用标记信息相匹配
- 每个问题不要太冗长，大约12-20字
- 每个问题附带1-2句理由以表达其对我的重要性
- 问题之间不要重复、不要重叠
- 问题须涵盖有效的 who what when where why how 角度方向
- 按重要性排序：先把最能直接回应用户的强有力提问放前面

# 可用内容标记概览
{marker_overview}

# 可选约束（如有提供）
{avoid_list}

# 参考输出格式（必须是有效JSON对象）
{{
  "suggested_goals": [
    {{"id": 1, "goal_text": "...", "rationale": "...", "uses": ["transcript"], "sources": ["youtube"]}},
    {{"id": 2, "goal_text": "...", "rationale": "...", "uses": ["transcript_with_comments"], "sources": ["bilibili", "reddit"]}},
    {{"id": 3, "goal_text": "...", "rationale": "...", "uses": ["transcript"], "sources": ["article"]}},
    {{"id": 4, "goal_text": "...", "rationale": "...", "uses": ["previous_findings"], "sources": []}},
    {{"id": 5, "goal_text": "...", "rationale": "...", "uses": ["transcript"], "sources": ["youtube", "bilibili"]}},
    {{"id": 6, "goal_text": "...", "rationale": "...", "uses": ["transcript"], "sources": ["article"]}},
    {{"id": 7, "goal_text": "...", "rationale": "...", "uses": ["transcript_with_comments"], "sources": ["youtube"]}}
  ]
}}

# 风格要求
{{> style_{writing_style}_cn.md}}