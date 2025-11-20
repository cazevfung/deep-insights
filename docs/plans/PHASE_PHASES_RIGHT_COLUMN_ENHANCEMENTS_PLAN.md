# Phase Right Column Enhanced UX Plan

## 1. Context & Motivation
- The sticky right-column interaction panel persists across all research pages, but the stream currently feels like a static status card plus a plain placeholder.
- Desired behavior is closer to Cursor’s chat workspace: chronological, titled message boxes and inline status statements that communicate real-time progress without overwhelming the user.
- We must strip away the existing summary pill/toolbar experiment and redesign the panel as an interactive chat-like log that combines content bubbles with lightweight status updates per step/phase/workflow.

## 2. Goals
1. **Chat-Like Presentation**: Replace the static summary header with an interactive timeline containing two message types—status statements (e.g., “阶段 0.5 正在等待输入”) and rich content bubbles.
2. **Contextual Metadata**: Make every entry display phase, step id, workflow label, and timestamps so the user instantly understands context.
3. **Progressive Disclosure**: Allow expansion/collapse for verbose content bubbles while keeping status statements compact and auto-expanded.
4. **Simple Status Bar**: Retain a minimal global connection indicator (在线/阶段/延迟) without additional clutter.
5. **Responsive & Accessible**: Maintain usability on narrow screens, respect focus order, and ensure keyboard/screen reader support.

## 3. Deliverables
- Updated `PhaseInteractionPanel` layout:
  - Minimal header (`已连接 • 阶段 X • 延迟 …`).
  - Scrollable timeline that renders a mix of `StatusStatement` and `ContentBubble` components depending on message metadata.
  - Footer user-input area unchanged (choices + textarea).
- Selector utilities:
  - Transform stream buffers into `TimelineItem` objects with `type` (`status` or `content`), `title`, `subtitle`, `badge`, `timestamp`, `body`, `preview`, `isStreaming`, `phase`, `stepRef`.
  - Provide heuristics to classify items as status (short updates, commands, phase-change notices) vs. content (analysis outputs, summaries).
- Components:
  - `StreamStatusStatement`: pill-style card with icon, single-line message, and optional detail tooltip.
  - `StreamContentBubble`: chat bubble with title, subtitle, expandable body, copy button.
  - `StreamTimeline`: orchestrates ordering, “显示更多消息”, and active highlighting.
- Documentation note describing when to use each message type.

## 4. Work Breakdown

### 4.1 UX Alignment & Copy (0.5 day)
- Review Cursor references for how status blips (e.g., “Plan drafted”, “Waiting for approval”) appear between larger outputs.
- Define textual patterns for status items (phase transitions, user prompts, completion notices) vs. content bubbles.
- Confirm icon/emoji usage and translation strings.

### 4.2 Data Modeling (0.5 day)
- Extend `usePhaseInteraction` (or create `usePhaseTimeline`) to produce ordered `TimelineItem[]` with typed entries.
- Determine classification rules: message length threshold, metadata tags (`metadata.status`, `metadata.action`, etc.), fallback to content bubble.
- Include computed flags: `isCollapsible`, `defaultCollapsed`, `isImportant` (for pinned items), `statusVariant` (info/success/warning).

### 4.3 Component Implementation (1.5 days)
- **StreamStatusStatement**: compact card with left accent bar, icon, headline (e.g., “阶段 1 正在执行”), and optional detail line.
- **StreamContentBubble**: chat-style bubble with title, subtitle, expand/collapse, copy.
- **StreamTimeline** wrapper: maps timeline items to components, preserves scroll position, adds “显示更多消息” button and active-stream highlight.

### 4.4 Panel Integration (0.75 day)
- Replace current list with timeline rendering; ensure empty-state copy (`暂无流式内容…`) remains when no items exist.
- Maintain global header + footer structure.

### 4.5 Styling & UX Polish (0.5 day)
- Tailwind classes for timeline connectors, accent bars, and icons.
- Smooth expand/collapse transitions; respect reduced-motion.
- Ensure status statements and content bubbles share consistent spacing.

### 4.6 Testing & QA (0.5 day)
- Selector tests covering item classification, preview truncation, and ordering.
- Component tests verifying collapse toggles and status badge rendering.
- Manual QA: streaming session with mixed status/content, long outputs, mobile view, keyboard navigation, copy actions.

### 4.7 Documentation & Rollout (0.25 day)
- Update `docs/frontend/RIGHT_COLUMN_UX_GUIDE.md` with timeline guidelines and status vs. content rules.
- Add release note summarizing the right-column refresh.

## 5. Risks & Mitigations
- **Misclassification**: If metadata is inconsistent, status/content separation may fail; provide explicit overrides (e.g., treat messages under 120 characters without punctuation as status) and log anomalies.
- **Visual Noise**: Too many status statements may crowd the feed; allow grouping adjacent status items or collapsing older ones automatically.
- **Performance**: Manage DOM size via “显示更多消息” to avoid long lists.
- **State Persistence**: Store collapse state per message id; avoid resetting when streaming updates.

## 6. Success Criteria
- Timeline alternates between compact status statements and expandable content bubbles, mirroring Cursor’s progression narrative.
- Users can read phase/step context directly from each entry without additional clicks.
- Expand/collapse interactions keep the feed tidy while preserving content access.
- No regressions to websocket handling or user input flow; the panel feels lighter despite richer context.

## 7. Stream Layout Sketch
```
┌──────────────────────────────────────────────┐
│ Header                                       │
│ ─ 已连接 • 阶段 0.5 • 延迟 1200ms            │
├──────────────────────────────────────────────┤
│ Scrollable Timeline                          │
│  ┌ Status Statement                          │
│  │  [info icon] 阶段 0.5 正在初始化…        │
│  ├ Content Bubble (expanded, active)         │
│  │  标题: 阶段 0.5 · 目标提炼                │
│  │  标签: workflow/goal-selection            │
│  │  正在流式… (正文全文)                    │
│  ├ Status Statement                          │
│  │  [success icon] 计划生成完成             │
│  ├ Content Bubble (collapsed preview)        │
│  │  标题: 阶段 1 · 数据概览                  │
│  │  内容预览…  [展开] [复制]                │
│  └ [显示更多消息]                            │
├──────────────────────────────────────────────┤
│ Footer (choices + textarea + controls)       │
└──────────────────────────────────────────────┘
```
