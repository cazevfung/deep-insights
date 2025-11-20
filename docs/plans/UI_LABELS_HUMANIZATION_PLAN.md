# UI Labels Humanization Plan

## Overview
This plan addresses all cold, technical, and inhuman labels/buttons/headers/progress markers throughout the application, replacing them with warm, user-friendly, and consistently understandable language.

## Principles
1. **User-Centric Language**: Use language that speaks to users, not systems
2. **Action-Oriented**: Labels should describe what's happening or what users can do
3. **Progress Clarity**: Progress indicators should be clear about current state and next steps
4. **Consistent Naming**: Use consistent terminology across all components
5. **Warmth & Empathy**: Replace technical jargon with friendly, helpful language

---

## Categories of Changes

### 1. Phase/Stage Labels (阶段)

#### Current Issues
- "阶段3" (Phase 3) - Too technical, doesn't explain what it is
- "阶段: 等待中" (Phase: Waiting) - Cold, doesn't help user understand

#### Proposed Changes

| Current | Proposed | Location |
|---------|----------|----------|
| `阶段3` | `深度研究` (Deep Research) | Sidebar.tsx, Phase3SessionPage.tsx |
| `阶段3 - 研究步骤` | `深度研究 - 分析步骤` (Deep Research - Analysis Steps) | Phase3SessionPage.tsx |
| `阶段: ${phase}` | `当前阶段: ${phaseName}` (Current Stage: ${phaseName}) | ResearchAgentPage.tsx |
| `阶段: 等待中` | `准备中...` (Preparing...) | ResearchAgentPage.tsx |

#### Phase Name Mapping
```typescript
const phaseNames: Record<string, string> = {
  '0': '数据准备',
  '0.5': '生成研究角色',
  '1': '生成研究目标',
  '2': '综合研究主题',
  '3': '深度研究',
  '4': '生成最终报告',
  'waiting': '准备中',
  'unknown': '处理中'
}
```

---

### 2. Status Labels (状态标签)

#### Current Issues
- "进行中" (In Progress) - Technical
- "等待" (Waiting) - Passive, unclear
- "失败" (Failed) - Harsh, doesn't help user understand what to do

#### Proposed Changes

| Current | Proposed | Context |
|---------|----------|---------|
| `已完成` | `已完成` (Keep as is) | Status badges |
| `进行中` | `某种努力中` (Processing) | Active status |
| `等待` | `等待Ta的出现` (Waiting) | Pending status |
| `失败` | `OMG出错了` (Something went wrong) | Error status |
| `未开始` | `待启动` (Not Started) | Not started |
| `等待中` | `准备中` (Preparing) | Waiting state |

---

### 3. Progress Stage Labels (进度阶段)

#### Current Issues
- "加载中" (Loading) - Too generic
- "下载中" (Downloading) - Technical
- "转换中" (Converting) - Technical
- "上传中" (Uploading) - Technical
- "转录中" (Transcribing) - Technical
- "提取中" (Extracting) - Technical
- "处理中" (Processing) - Too generic

#### Proposed Changes

| Current | Proposed | Context |
|---------|----------|---------|
| `加载中` | `加载中` (Loading) | Loading stage |
| `下载中` | `下载中` (Downloading) | Download stage |
| `转换中` | `正在转换成人话` (Converting) | Conversion stage |
| `上传中` | `上传处理中` (Uploading) | Upload stage |
| `转录中` | `正在生成文字稿` (Generating transcript) | Transcription stage |
| `提取中` | `正在阅读内容` (Extracting) | Extraction stage |
| `处理中` | `某种努力中` (Processing) | Generic processing |
| `当前阶段: ${stage}` | `当前: ${stageName}` (Current: ${stageName}) | Progress display |

---

### 4. Error Messages (错误消息)

#### Current Issues
- "未找到批次ID，请先开始研究工作流" - Too technical, blames user
- "请确保研究工作流已完成，或检查批次ID是否正确" - Technical, unhelpful
- "加载报告失败" (Failed to load report) - Harsh, doesn't help
- "报告尚未生成" (Report not yet generated) - Passive

#### Proposed Changes

| Current | Proposed | Location |
|---------|----------|----------|
| `未找到批次ID，请先开始研究工作流` | `还没有开始研究工作，请先添加链接并开始研究` (No research started yet. Please add links and start research) | FinalReportPage.tsx |
| `请确保研究工作流已完成，或检查批次ID是否正确` | `研究可能还在进行中，请稍后再查看报告` (Research may still be in progress. Please check back later) | FinalReportPage.tsx |
| `加载报告失败` | `无法加载报告，请刷新页面重试` (Unable to load report. Please refresh and try again) | FinalReportPage.tsx |
| `报告尚未生成` | `报告正在生成中，请稍候...` (Report is being generated, please wait...) | FinalReportPage.tsx |
| `加载历史记录失败` | `无法加载历史记录，请刷新页面重试` | HistoryPage.tsx |
| `恢复会话失败` | `无法恢复会话，请重试` | HistoryPage.tsx |
| `查看会话失败` | `无法查看会话详情，请重试` | HistoryPage.tsx |
| `删除会话失败` | `无法删除会话，请重试` | HistoryPage.tsx |
| `格式化链接失败` | `链接格式有误，请检查后重试` | LinkInputPage.tsx |
| `取消失败，请重试` | `取消操作失败，请重试` | ScrapingProgressPage.tsx |

---

### 5. Button Labels (按钮标签)

#### Current Issues
- "发送" (Send) - Generic
- "批准并继续" (Approve and Continue) - Formal
- "确定要取消当前抓取任务吗？" - Long, technical

#### Proposed Changes

| Current | Proposed | Location |
|---------|----------|----------|
| `发送` | `发送` (Keep) | ResearchAgentPage.tsx |
| `批准并继续` | `确认继续` (Continue) | ResearchAgentPage.tsx |
| `确定要取消当前抓取任务吗？已完成的链接将被保留，未完成的将被标记为已取消。` | `确定要取消当前任务吗？已完成的链接会保留，未完成的将停止处理。` (Are you sure you want to cancel? Completed links will be kept, unfinished ones will stop processing.) | ScrapingProgressPage.tsx |
| `确定要开始新会话吗？这将清除当前会话的所有数据。` | `确定要开始新会话吗？当前会话的数据将被清除。` (Are you sure you want to start a new session? Current session data will be cleared.) | LinkInputPage.tsx |
| `显示原始数据` / `隐藏原始数据` | `查看原始数据` / `收起原始数据` | Phase3SessionPage.tsx |

---

### 6. Navigation Labels (导航标签)

#### Current Issues
- "链接输入" (Link Input) - Technical
- "抓取进度" (Scraping Progress) - Technical
- "研究代理" (Research Agent) - Technical
- "阶段3" - Already addressed above
- "最终报告" (Final Report) - Formal

#### Proposed Changes

| Current | Proposed | Location |
|---------|----------|----------|
| `链接输入` | `添加链接` (Add Links) | Sidebar.tsx |
| `抓取进度` | `内容收集` (Content Collection) | Sidebar.tsx |
| `研究代理` | `研究规划` (Research Planning) | Sidebar.tsx |
| `阶段3` | `深度研究` (Deep Research) | Sidebar.tsx |
| `最终报告` | `研究报告` (Research Report) | Sidebar.tsx |
| `研究历史` | `历史记录` (History) | Sidebar.tsx |

---

### 7. Page Headers & Titles (页面标题)

#### Current Issues
- "研究代理" (Research Agent) - Technical
- "最终报告" (Final Report) - Formal
- "阶段3 - 研究步骤" - Technical

#### Proposed Changes

| Current | Proposed | Location |
|---------|----------|----------|
| `研究代理` | `研究规划` (Research Planning) | ResearchAgentPage.tsx |
| `最终报告` | `研究报告` (Research Report) | FinalReportPage.tsx |
| `阶段3 - 研究步骤` | `深度研究 - 分析步骤` (Deep Research - Analysis Steps) | Phase3SessionPage.tsx |

---

### 8. Progress Indicators (进度指示器)

#### Current Issues
- "总体进度" (Overall Progress) - Technical
- "当前阶段: ${stage}" - Technical
- "词数: ${count}" - Technical
- "完成时间: ${time}" - Formal

#### Proposed Changes

| Current | Proposed | Location |
|---------|----------|----------|
| `总体进度` | `整体进度` (Overall Progress) | LinkProgressItem.tsx |
| `当前阶段: ${stage}` | `当前步骤: ${stageName}` (Current Step: ${stageName}) | LinkProgressItem.tsx |
| `词数: ${count}` | `内容字数: ${count}` (Content Words: ${count}) | LinkProgressItem.tsx |
| `完成时间: ${time}` | `完成于: ${time}` (Completed at: ${time}) | LinkProgressItem.tsx |
| `来源: ${source}` | `来源: ${source}` (Keep) | LinkProgressItem.tsx |
| `处理中...` | `正在处理...` (Processing...) | LinkProgressItem.tsx |

---

### 9. Workflow Stepper Labels (工作流步骤器)

#### Current Issues
- "工作流进度" (Workflow Progress) - Technical
- "收起" / "展开" (Collapse / Expand) - Generic
- Status labels in aria-label - Already addressed above

#### Proposed Changes

| Current | Proposed | Location |
|---------|----------|----------|
| `工作流进度` | `研究进度` (Research Progress) | WorkflowStepper.tsx |
| `收起` / `展开` | `收起进度` / `展开进度` (Collapse Progress / Expand Progress) | WorkflowStepper.tsx |

---

### 10. Research Agent Page Labels (研究代理页面)

#### Current Issues
- "综合目标" (Synthesized Goal) - Technical
- "统一主题:" (Unifying Theme) - Formal
- "组件问题:" (Component Questions) - Technical
- "研究目标" (Research Goals) - Keep but context needed
- "研究计划" (Research Plan) - Keep
- "需要您的输入" (Your Input Required) - Formal
- "请选择:" (Please Choose) - Keep

#### Proposed Changes

| Current | Proposed | Location |
|---------|----------|----------|
| `综合目标` | `研究主题` (Research Topic) | ResearchAgentPage.tsx |
| `统一主题:` | `核心主题:` (Core Theme:) | ResearchAgentPage.tsx |
| `组件问题:` | `相关问题:` (Related Questions:) | ResearchAgentPage.tsx |
| `研究目标` | `研究目标` (Keep) | ResearchAgentPage.tsx |
| `研究计划` | `研究计划` (Keep) | ResearchAgentPage.tsx |
| `需要您的输入` | `需要您的确认` (Your Confirmation Needed) | ResearchAgentPage.tsx |
| `请选择:` | `请选择:` (Keep) | ResearchAgentPage.tsx |
| `请输入您的回复...` | `请输入您的回复或直接点击"继续"以批准...` (Enter your reply or click "Continue" to approve...) | ResearchAgentPage.tsx |
| `步骤 ${id}` | `步骤 ${id}` (Keep) | ResearchAgentPage.tsx |
| `所需数据:` | `需要数据:` (Required Data:) | ResearchAgentPage.tsx |
| `分块策略:` | `处理方式:` (Processing Method:) | ResearchAgentPage.tsx |

---

### 11. Phase 3 Session Page Labels (阶段3会话页面)

#### Current Issues
- "步骤 ${id}" (Step ${id}) - Generic
- "进行中..." / "未开始" - Already addressed
- "摘要" (Summary) - Keep
- "关键主张" (Key Claims) - Formal
- "支持证据：" (Supporting Evidence) - Formal
- "重要证据" (Notable Evidence) - Formal
- "分析详情" (Analysis Details) - Formal
- "五个为什么 (Five Whys)" - Mixed language
- "假设 (Assumptions)" - Mixed language
- "不确定性 (Uncertainties)" - Mixed language
- "洞察" (Insights) - Keep
- "置信度：" (Confidence) - Technical

#### Proposed Changes

| Current | Proposed | Location |
|---------|----------|----------|
| `步骤 ${id}` | `分析步骤 ${id}` (Analysis Step ${id}) | Phase3SessionPage.tsx |
| `摘要` | `摘要` (Keep) | Phase3SessionPage.tsx |
| `关键主张` | `主要观点` (Key Points) | Phase3SessionPage.tsx |
| `支持证据：` | `证据支持：` (Evidence:) | Phase3SessionPage.tsx |
| `重要证据` | `重要发现` (Important Findings) | Phase3SessionPage.tsx |
| `分析详情` | `深入分析` (Deep Analysis) | Phase3SessionPage.tsx |
| `五个为什么 (Five Whys)` | `五个为什么` (Five Whys) | Phase3SessionPage.tsx |
| `假设 (Assumptions)` | `假设分析` (Assumptions) | Phase3SessionPage.tsx |
| `不确定性 (Uncertainties)` | `不确定性分析` (Uncertainties) | Phase3SessionPage.tsx |
| `洞察` | `洞察` (Keep) | Phase3SessionPage.tsx |
| `置信度：` | `可信度：` (Confidence Level:) | Phase3SessionPage.tsx |
| `暂无步骤数据` | `还没有分析步骤，研究完成后将显示在这里` (No analysis steps yet. They will appear here when research completes.) | Phase3SessionPage.tsx |

---

### 12. Scraping Progress Page Labels (抓取进度页面)

#### Current Issues
- "成功: ${count}" (Success) - Technical
- "失败: ${count}" (Failed) - Harsh
- "进行中: ${count}" (In Progress) - Technical
- "总计: ${count}" (Total) - Keep

#### Proposed Changes

| Current | Proposed | Location |
|---------|----------|----------|
| `成功: ${count}` | `已完成: ${count}` (Completed: ${count}) | ScrapingProgressPage.tsx |
| `失败: ${count}` | `失败: ${count}` (Keep, but add context) | ScrapingProgressPage.tsx |
| `进行中: ${count}` | `处理中: ${count}` (Processing: ${count}) | ScrapingProgressPage.tsx |
| `总计: ${count}` | `总计: ${count}` (Keep) | ScrapingProgressPage.tsx |
| `已完成: ${count}` | `已完成: ${count}` (Keep) | ScrapingProgressPage.tsx |

---

### 13. History Page Labels (历史页面)

#### Current Issues
- Status filter labels - Already addressed above
- "加载中..." (Loading...) - Generic

#### Proposed Changes

| Current | Proposed | Location |
|---------|----------|----------|
| `加载中...` | `正在加载历史记录...` (Loading history...) | HistoryPage.tsx |

---

### 14. Notification Messages (通知消息)

#### Current Issues
- "工作流已完成" (Workflow Completed) - Technical
- "WebSocket连接失败，请刷新页面或检查网络连接" - Technical
- "发送消息失败" (Failed to send message) - Harsh

#### Proposed Changes

| Current | Proposed | Location |
|---------|----------|----------|
| `工作流已完成` | `研究已完成！` (Research completed!) | useWebSocket.ts |
| `WebSocket连接失败，请刷新页面或检查网络连接` | `连接中断，请刷新页面重试` (Connection lost. Please refresh and try again.) | useWebSocket.ts |
| `发送消息失败` | `无法发送消息，请重试` (Unable to send message. Please try again.) | useWebSocket.ts |
| `已清除会话，可以开始新的研究` | `会话已清除，可以开始新的研究` (Session cleared. You can start a new research.) | LinkInputPage.tsx |

---

### 15. Time Formatting (时间格式化)

#### Current Issues
- "X秒前" (X seconds ago) - Keep
- "X分钟前" (X minutes ago) - Keep
- "X小时前" (X hours ago) - Keep
- "生成时间: ${time}" (Generated at: ${time}) - Formal

#### Proposed Changes

| Current | Proposed | Location |
|---------|----------|----------|
| `生成时间: ${time}` | `撰写于: ${time}` (Generated at: ${time}) | FinalReportPage.tsx |

---

## Implementation Checklist

### Phase 1: Core Components (High Priority)
- [ ] **Sidebar.tsx** - Navigation labels
- [ ] **LinkProgressItem.tsx** - Status and progress labels
- [ ] **StatusBadge.tsx** - Status badge labels
- [ ] **WorkflowStepper.tsx** - Workflow progress labels

### Phase 2: Page Components (High Priority)
- [ ] **ResearchAgentPage.tsx** - Research agent labels
- [ ] **Phase3SessionPage.tsx** - Phase 3 labels and headers
- [ ] **FinalReportPage.tsx** - Error messages and headers
- [ ] **ScrapingProgressPage.tsx** - Progress labels

### Phase 3: Supporting Components (Medium Priority)
- [ ] **HistoryPage.tsx** - History page labels
- [ ] **LinkInputPage.tsx** - Input page labels
- [ ] **useWebSocket.ts** - Notification messages
- [ ] **Button.tsx** - Button loading states

### Phase 4: Backend Messages (If applicable)
- [ ] Review backend error messages sent to frontend
- [ ] Update any backend status messages

---

## Files to Modify

### Frontend Files (Client)
1. `client/src/components/layout/Sidebar.tsx`
2. `client/src/components/progress/LinkProgressItem.tsx`
3. `client/src/components/progress/StatusBadge.tsx`
4. `client/src/components/workflow/WorkflowStepper.tsx`
5. `client/src/pages/ResearchAgentPage.tsx`
6. `client/src/pages/Phase3SessionPage.tsx`
7. `client/src/pages/FinalReportPage.tsx`
8. `client/src/pages/ScrapingProgressPage.tsx`
9. `client/src/pages/HistoryPage.tsx`
10. `client/src/pages/LinkInputPage.tsx`
11. `client/src/hooks/useWebSocket.ts`
12. `client/src/components/common/Button.tsx`

### Potential Backend Files (If needed)
- Review backend error messages and status strings sent to frontend

---

## Testing Checklist

After implementation:
- [ ] All navigation labels are user-friendly
- [ ] All status labels are clear and warm
- [ ] All error messages are helpful and actionable
- [ ] All progress indicators are descriptive
- [ ] Phase names are consistent across the app
- [ ] No technical jargon remains in user-facing text
- [ ] All buttons have clear, action-oriented labels
- [ ] Time formatting is consistent
- [ ] Notification messages are friendly and helpful

---

## Notes

1. **Consistency**: Ensure all similar concepts use the same terminology
2. **Context**: Some labels may need context-specific variations
3. **Accessibility**: Maintain aria-labels and screen reader compatibility
4. **Internationalization**: If i18n is planned, ensure all strings are externalized
5. **User Testing**: Consider user testing after changes to ensure clarity

---

## Summary

This plan addresses **15 categories** of UI labels across **12+ frontend files**, replacing cold, technical language with warm, user-friendly, and consistently understandable text. The changes focus on:

- **Clarity**: Making it clear what's happening and what users can do
- **Warmth**: Using friendly, empathetic language
- **Consistency**: Using the same terminology throughout
- **Action-Oriented**: Focusing on what users can do, not system states
- **Helpfulness**: Error messages that guide users, not blame them

