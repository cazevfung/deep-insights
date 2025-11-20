# UI Simplification Screen Change Plan（界面精简变更计划）

## 1. Purpose（目的）
- Translate the high-level simplification strategy into specific UI targets（将高层策略细化到具体界面）.
- Document severity, owners, and demo sketches for proposed simplifications（记录影响程度、责任人和示意草图）.
- Serve as alignment artifact for design, frontend, and PM before implementation（作为设计、前端与产品对齐的参考）.

## 2. Screen Prioritization Framework（优先级框架）
- **Frequency / 使用频次**: How often the surface is used in core workflows.
- **Severity / 杂乱程度**: Degree of clutter (excess headings, CTAs, info blocks).
- **Impact / 影响力**: Expected reduction in cognitive load after simplification.
- **Feasibility / 可行性**: Estimated effort, dependencies, and readiness of design assets.

Priority score = (Frequency × Impact) + Severity − Feasibility penalty（优先得分公式保持一致）.

## 3. Targeted Screens & Issues（目标界面与问题）

### 3.1 Streaming Dashboard（流媒体监控面板）`StreamDisplay`
- **Frequency / 使用频次**: Daily for analyst monitoring（分析师每天使用）.
- **Severity / 杂乱程度**: High — duplicate section titles and three `primary` CTAs crowd the hero area（顶部多重标题与三个主按钮聚集）.
- **Impact / 影响力**: High — clarifying the main stream action should reduce reaction time（更快定位核心操作）.
- **Feasibility / 可行性**: Medium — layout primitives exist but component tree较复杂.
- **Key Issues / 关键问题**:
  1. Top-level heading, subheading, active stream tag lack spacing（标题与标签贴合）.
  2. `Go Live / 开始直播`, `Refresh / 刷新`, `Export / 导出` 同为主按钮.
  3. Info cards `Stream Stats / 流数据`, `Recent Mentions / 最新提及`, `Alerts / 警报` 同屏并列，分散注意力.

### 3.2 Research Agent Console（研究代理控制台）`AgentConsole`
- **Frequency / 使用频次**: High — core for research sessions（研究流程核心界面）.
- **Severity / 杂乱程度**: High — timeline/control bar/info rail repeat headings; `Pause / 暂停`, `Retry / 重试`, `Generate Summary / 生成摘要`, `Open Notes / 打开笔记` 权重相同.
- **Impact / 影响力**: High — clearer hierarchy improves response time.
- **Feasibility / 可行性**: Medium — 需要布局重构与文案精简.

### 3.3 Session Insights Panel（会话洞察面板）`SessionInsights`
- **Frequency / 使用频次**: Medium.
- **Severity / 杂乱程度**: Medium — `Highlights / 亮点`, `Risks / 风险`, `Opportunities / 机会` 卡片内含段落+嵌套项目.
- **Impact / 影响力**: Medium — 汇总加展开能减轻信息量.
- **Feasibility / 可行性**: High — 模块化卡片易调整.

### 3.4 Dataset Configuration Wizard（数据集配置向导）`DatasetConfigWizard`
- **Frequency / 使用频次**: Medium.
- **Severity / 杂乱程度**: High — 步骤条标题重复，CTA 组合 (`Next / 下一步`, `Preview / 预览`, `Skip / 跳过`, `Save Draft / 保存草稿`) 同屏.
- **Impact / 影响力**: High — 精简导航可减少误操作.
- **Feasibility / 可行性**: Medium — 需调整样式 token 与状态逻辑.

### 3.5 Integrations Manager（集成管理）`IntegrationsManager`
- **Frequency / 使用频次**: Low-Medium（管理员偶尔进入）.
- **Severity / 杂乱程度**: Medium — 每个集成重复信息条与状态徽章.
- **Impact / 影响力**: Medium — 减少视觉噪音利于排障.
- **Feasibility / 可行性**: High — 主要为内容聚合与开关调整.

### 3.6 Admin Controls（后台控制面板）`AdminControls`
- **Frequency / 使用频次**: Low.
- **Severity / 杂乱程度**: Low-Medium — 主要集中在高级设置区.
- **Impact / 影响力**: Low-Medium — 增强一致性.
- **Feasibility / 可行性**: Medium.

## 4. Consolidated Action Plan（整合行动计划）

### Phase A – Critical Surfaces（关键界面，第1-3周）
1. **StreamDisplay（流媒体监控）**
   - Owner: Streaming squad（流媒体小组）.
   - Deliverables: single headline, CTA tier harmonization, collapsible info rail（单一标题、CTA 分级、信息栏折叠）.
2. **AgentConsole（研究控制台）**
   - Owner: Research agent squad（研究代理小组）.
  - Deliverables: timeline focus panel, overflow menu for secondary actions, context drawer refactor（集中时间线面板、二级操作菜单、上下文抽屉重构）.

### Phase B – Supporting Surfaces（支持界面，第4-6周）
1. **DatasetConfigWizard（数据集向导）**
   - Streamline step headings, reduce CTA count, convert help text to tooltips（精简步骤标题、减少按钮、帮助转为提示）.
2. **SessionInsights（会话洞察）**
   - Collapse cards into summary tiles with `View Details` drawers（卡片转摘要+详情抽屉）.

### Phase C – Administrative（后台界面，第7-8周）
1. **IntegrationsManager（集成管理）**
   - Consolidate provider banners, introduce grouped status legend（合并信息条，引入状态图例）.
2. **AdminControls（后台控制）**
   - Align heading scale, limit primary actions, move dense info into accordions（统一标题层级、限制主按钮、信息折叠）.

## 5. Demo Sketches（文字线框示意）

### 5.1 StreamDisplay（流媒体监控）After Simplification（精简后）

```
┌──────────────────────────────────────────────┐
│ Stream Monitoring / 流监控                   │ ← Single headline / 主标题
│ Status 状态: Live • 220 viewers              │ ← Inline metadata / 行内元信息
├──────────────────────────────────────────────┤
│ [Primary CTA: Manage Stream 管理直播]   ⋮     │ ← Secondary actions / 次级操作
├──────────────────────────────────────────────┤
│ Key Metrics 核心指标                         │
│  ├─ Bitrate 码率: 4.5 Mbps                   │
│  ├─ Dropped Frames 丢帧率: 0.2%              │
│  └─ Alerts 警报: 1 pending → View 查看       │ ← Drawer link / 抽屉链接
├──────────────────────────────────────────────┤
│ Recent Mentions 最新提及 (collapsed 折叠) [+] │ ← Progressive disclosure / 渐进披露
├──────────────────────────────────────────────┤
│ Activity Log 活动日志                        │
└──────────────────────────────────────────────┘
```

### 5.2 AgentConsole（研究控制台）After Simplification（精简后）

```
┌───────────────┬──────────────────────────────┐
│ Session Focus 会话焦点 │ Timeline 时间线      │
│  Goal 目标: Sync NPC memory 同步 NPC 记忆     │
│  Primary Action 主操作: [Resume Session 继续] │
│  Secondary 次级: ⋮                            │
└───────────────┴──────────────────────────────┘
│ Context Drawer 上下文抽屉 (collapsed 默认折叠) │
│  • Latest Findings 最新发现                  │
│  • Data Sources 数据来源                     │
└──────────────────────────────────────────────┘
│ Notes 笔记 (tab)  |  Comments 评论            │
└──────────────────────────────────────────────┘
```

### 5.3 DatasetConfigWizard（数据集向导）After Simplification（精简后）

```
Step 2 of 5 / 第2步（共5步） | Configure Data Source 配置数据源
Headline 标题: Choose ingestion cadence 选择同步频率
Description 描述: Select how often to sync this dataset. 选择同步周期。

[Primary 主操作: Continue 继续]  [Secondary 次级: Save Draft 保存草稿]

Cadence Options 同步选项:
 ( ) Hourly 每小时
 ( ) Daily 每天
 ( ) Weekly 每周
Need help? 需要帮助？ (?) tooltip 提示

Advanced Settings 高级设置 (collapsed 折叠)
```

### 5.4 SessionInsights（会话洞察）After Simplification（精简后）

```
┌──────────────┬──────────────┬──────────────┐
│ Highlight 亮点 │ Risk 风险    │ Opportunity 机会 │
│ • Summary 摘要 │ • Summary 摘要 │ • Summary 摘要 │ ← single bullet each / 单行摘要
│ [View full 查看详情] │ [View full 查看详情] │ [View full 查看详情] │ ← secondary buttons / 次级按钮
└──────────────┴──────────────┴──────────────┘
```

### 5.5 IntegrationsManager（集成管理）After Simplification（精简后）

```
Integrations 集成
Primary CTA 主操作: [Add Integration 添加集成]

Status Legend 状态图例: Connected 已连接 • Pending 待处理 • Error 错误

Slack         Connected 已连接      Manage 管理 ⋮
Salesforce    Pending 待处理        Fix setup 修复设置
GitHub        Error 错误            Resolve 解决
```

### 5.6 AdminControls（后台控制）After Simplification（精简后）

```
Admin Controls 后台控制

User Management 用户管理
[Primary 主操作: Invite user 邀请用户]   ⋮
Guideline 指引: description moved to tooltip 描述移至提示。

System Settings 系统设置 (accordion 手风琴)
  Toggle features 功能开关...

Audit Logs 审计日志
[Secondary 次级: Export CSV 导出]
```

## 6. Dependencies & Prep Work（依赖与准备）
- Design tokens update (`headline`, `subheadline`, `label`, CTA tiers) must land before Phase A（先落地设计 token 更新）.
- Feature flag framework ready for per-route toggling (`uiSimplify.StreamDisplay` 等)（特性开关需支持页面级切换）.
- Analytics events for baseline metrics deployed two weeks ahead of release（发布前两周埋点）.
- Content strategy must deliver revised copy deck prior to wireframe finalization（内容团队先交文案草稿）.

## 7. Validation Plan（验证计划）
- **Usability tests / 可用性测试**: 5 users per critical surface; measure time-to-primary action & clarity.
- **Telemetry comparison / 数据对比**: Monitor CTA usage, drawer opens, bounce rate pre/post.
- **Accessibility audit / 无障碍审查**: Ensure heading structure & focus order meet WCAG 2.1 AA.

## 8. Next Actions（下一步）
1. Kick off StreamDisplay & AgentConsole workshops（启动流媒体与研究控制台工作坊）.
2. Assign design owners for Phase B/C surfaces（指定 Phase B/C 设计负责人）.
3. Prepare content review sessions for simplified copy（安排文案评审）.
4. Schedule validation checkpoints aligned with milestones（设定验证里程碑）.

