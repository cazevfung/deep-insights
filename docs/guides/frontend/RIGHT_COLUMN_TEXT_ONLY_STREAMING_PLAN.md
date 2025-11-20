# Right Column Text-Only Streaming Plan

**Date:** 2025-01-27  
**Status:** Design Plan (Not Implemented)  
**Priority:** High

## Overview

This document outlines a plan to replace the current bubble-based JSON output display in the right column with a simpler text-only interface. Processes will be shown as plain text strings that appear "shiny" while streaming and turn gray when completed.

---

## Current State Analysis

### Current Implementation

The right column (`PhaseInteractionPanel`) currently displays:

1. **StreamContentBubble Component** (`client/src/components/phaseCommon/StreamContentBubble.tsx`):
   - Displays streamed content in bubble/card format
   - Shows JSON output when expanded
   - Has collapse/expand functionality
   - Shows preview text when collapsed
   - Displays Phase 0 summaries with specialized components
   - Has pin, copy, and toggle actions

2. **StreamTimeline Component** (`client/src/components/phaseCommon/StreamTimeline.tsx`):
   - Renders a list of `StreamContentBubble` components
   - Handles visibility and pagination
   - Shows status statements separately

3. **Data Structure** (`PhaseTimelineItem` from `usePhaseInteraction.ts`):
   - `isStreaming`: boolean indicating if item is currently streaming
   - `status`: 'active' | 'completed' | 'error'
   - `message`: string containing the full content (often JSON)
   - `preview`: string for collapsed view
   - `metadata`: object with additional context

### Current Issues

1. **JSON Bubbles Clutter**: JSON output displayed in bubbles creates visual clutter
2. **Complex UI**: Bubbles with borders, backgrounds, and actions are visually heavy
3. **Information Overload**: Users see raw JSON instead of process descriptions
4. **Visual Noise**: Multiple bubbles compete for attention

---

## Design Goals

### Primary Goals

1. **Remove All Bubbles**: Replace bubble/card UI with simple text strings
2. **Text-Only Display**: Show processes as plain text without visual containers
3. **Shiny Effect While Streaming**: Active/streaming processes appear with shiny animation
4. **Gray When Completed**: Completed processes turn gray to indicate completion
5. **Process Descriptions**: Show human-readable process descriptions instead of raw JSON

### Visual States

1. **Streaming State** (Shiny):
   - Text appears with shiny/shimmer animation
   - Indicates process is actively running
   - Uses primary color or accent color
   - Animation draws attention to active work

2. **Completed State** (Gray):
   - Text turns gray
   - Indicates process has finished
   - No animation
   - Subtle, non-intrusive appearance

3. **Error State** (Red/Amber):
   - Text appears in error color
   - Indicates process failed
   - May include error icon

---

## Proposed Design

### Visual Design

```
┌─────────────────────────────────────────┐
│ [Header - Status, Phase, Latency]       │
├─────────────────────────────────────────┤
│                                         │
│  正在生成研究角色...                    │ ← Streaming (shiny)
│  正在分析步骤 3: 市场趋势...            │ ← Streaming (shiny)
│  正在综合研究结果...                    │ ← Streaming (shiny)
│                                         │
│  已完成: 步骤 2 分析完成                │ ← Completed (gray)
│  已完成: 步骤 1 初始分析完成            │ ← Completed (gray)
│  已完成: 转录摘要完成                   │ ← Completed (gray)
│                                         │
│  ⚠️  错误: JSON 解析失败                │ ← Error (red)
│                                         │
├─────────────────────────────────────────┤
│ [Footer - Input Area]                  │
└─────────────────────────────────────────┘
```

### Text Format

**Streaming Items:**
- Format: `正在[process description]...`
- Style: Shiny animation, primary/accent color
- Example: `正在生成研究角色...`
- Example: `正在分析步骤 3: 市场趋势分析...`
- Example: `正在综合研究结果...`

**Completed Items:**
- Format: `已完成: [process description]`
- Style: Gray text, no animation
- Example: `已完成: 步骤 2 分析完成`
- Example: `已完成: 转录摘要完成`
- Example: `已完成: 研究角色生成完成`

**Error Items:**
- Format: `⚠️  错误: [error description]`
- Style: Red/amber text, no animation
- Example: `⚠️  错误: JSON 解析失败`
- Example: `⚠️  错误: 网络连接超时`

### Process Description Generation

Instead of showing raw JSON, generate human-readable descriptions from:

1. **Metadata** (`item.metadata`):
   - `component`: e.g., 'role_generation' → '正在生成研究角色'
   - `step_id`: e.g., 3 → '正在分析步骤 3'
   - `goal`: e.g., '市场趋势分析' → '正在分析步骤 3: 市场趋势分析'
   - `stage_label`: e.g., 'phase4-outline' → '正在生成报告大纲'

2. **Phase Information**:
   - `phaseLabel`: e.g., '阶段 1' → '阶段 1: 正在处理...'
   - `stepLabel`: e.g., '初始分析' → '正在执行初始分析...'

3. **Status Messages**:
   - Use existing `generateSummaryText` logic from `StreamContentBubble.tsx`
   - Map component types to Chinese descriptions
   - Include step/goal context when available

---

## Implementation Plan

### Phase 1: Create Text-Only Component

**1.1 Create `ProcessTextItem` Component**

Location: `client/src/components/phaseCommon/ProcessTextItem.tsx`

**Props:**
```typescript
interface ProcessTextItemProps {
  item: PhaseTimelineItem
  isStreaming: boolean
  isCompleted: boolean
  isError: boolean
}
```

**Features:**
- Simple text display (no bubble/card)
- Shiny animation when `isStreaming === true`
- Gray text when `isCompleted === true`
- Error styling when `isError === true`
- Generate process description from metadata

**1.2 Process Description Logic**

Extract and enhance `generateSummaryText` function from `StreamContentBubble.tsx`:

```typescript
const generateProcessDescription = (
  item: PhaseTimelineItem
): string => {
  const { metadata, stepLabel, phaseLabel, status } = item
  
  // Check for stage_label or component (Phase 4 stages)
  const stageLabel = metadata?.stage_label || metadata?.component
  if (stageLabel) {
    const stageMap: Record<string, string> = {
      'phase4-outline': '正在生成报告大纲',
      'phase4-coverage': '正在生成覆盖检查',
      'phase4-article': '正在生成最终报告',
      // ... more mappings
    }
    if (stageMap[stageLabel]) {
      return stageMap[stageLabel]
    }
  }
  
  // Check for step_id (Phase 3 steps)
  if (metadata?.step_id) {
    const goal = metadata?.goal || ''
    const goalPreview = goal.length > 30 ? goal.substring(0, 30) + '...' : goal
    return `正在分析步骤 ${metadata.step_id}${goalPreview ? `: ${goalPreview}` : ''}`
  }
  
  // Check for component
  if (metadata?.component) {
    const componentMap: Record<string, string> = {
      role_generation: '正在生成研究角色',
      goal_generation: '正在生成研究目标',
      synthesis: '正在综合研究结果',
      step_initial: '正在执行初始分析',
      step_followup: '正在执行补充分析',
      // ... more mappings
    }
    const description = componentMap[metadata.component]
    if (description) {
      return description
    }
  }
  
  // Use stepLabel if available
  if (stepLabel) {
    return `正在处理 ${stepLabel}`
  }
  
  // Fallback
  return '正在处理中...'
}
```

**1.3 Shiny Animation**

Use existing `ShinyText` component or create new animation:

```typescript
// Shiny animation CSS
const shinyAnimation = {
  background: 'linear-gradient(90deg, transparent 0%, rgba(148,163,184,0.4) 50%, transparent 100%)',
  backgroundSize: '200% 100%',
  animation: 'shine 2.5s ease-in-out infinite',
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  backgroundClip: 'text',
}
```

Or use Tailwind classes with custom animation:
```css
@keyframes shine {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.shiny-text {
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(148,163,184,0.4) 50%, 
    transparent 100%);
  background-size: 200% 100%;
  animation: shine 2.5s ease-in-out infinite;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
```

### Phase 2: Update StreamTimeline

**2.1 Replace StreamContentBubble with ProcessTextItem**

Location: `client/src/components/phaseCommon/StreamTimeline.tsx`

**Changes:**
- Remove `StreamContentBubble` import
- Import `ProcessTextItem`
- Replace bubble rendering with text item rendering
- Remove collapse/expand logic (text items are always visible)
- Remove pin/copy actions (or make them optional/hidden)

**2.2 Simplify Timeline Layout**

- Remove bubble spacing and borders
- Use simple list layout with consistent spacing
- Remove grouping logic (all items are equal)
- Keep chronological order (newest at bottom)

### Phase 3: Update PhaseInteractionPanel

**3.1 Remove Bubble-Related State**

Location: `client/src/components/phaseCommon/PhaseInteractionPanel.tsx`

**Remove:**
- `collapsedState` state (no collapsing needed)
- `pinnedItems` state (no pinning needed)
- `handleToggleCollapse` function
- `handlePinItem` function
- Collapse-related UI elements

**Keep:**
- `visibleCount` state (for pagination)
- `handleShowMore` function
- Scroll management
- Auto-scroll logic

**3.2 Simplify Header/Footer**

- Keep header (status, phase, latency)
- Keep footer (input area)
- Remove bubble-related controls

### Phase 4: Handle Completion States

**4.1 Track Completion**

Determine completion from:
- `item.status === 'completed'`
- `item.isStreaming === false` AND `item.status === 'active'` (transitioning)
- Summarization progress: `summarizationProgress.currentItem` updates

**4.2 State Transitions**

```typescript
const getItemState = (item: PhaseTimelineItem): 'streaming' | 'completed' | 'error' => {
  if (item.status === 'error' || item.statusVariant === 'error') {
    return 'error'
  }
  
  if (item.isStreaming && item.status === 'active') {
    return 'streaming'
  }
  
  if (item.status === 'completed') {
    return 'completed'
  }
  
  // Transitioning: was streaming, now not
  if (!item.isStreaming && item.status === 'active') {
    return 'completed' // Treat as completed
  }
  
  return 'completed' // Default to completed
}
```

**4.3 Completion Detection for Summarization**

Track individual item completion in summarization:
- When `summarizationProgress.currentItem` increments, mark previous item as completed
- When `summarizationProgress.currentItem === summarizationProgress.totalItems`, mark last item as completed

### Phase 5: Remove JSON Display

**5.1 Remove JSON Parsing**

- Remove JSON parsing logic from `StreamContentBubble`
- Remove `Phase0SummaryDisplay` integration (or keep for other uses)
- Remove `StreamStructuredView` usage
- Remove JSON tree display

**5.2 Process Description Only**

- Always show process description (never raw JSON)
- Use metadata to generate descriptions
- Fallback to generic messages if metadata unavailable

### Phase 6: Visual Polish

**6.1 Typography**

- Use consistent font size (e.g., `text-sm` or `text-xs`)
- Use appropriate font weight (regular for completed, medium for streaming)
- Ensure good contrast for gray text

**6.2 Spacing**

- Consistent vertical spacing between items (e.g., `space-y-1` or `space-y-2`)
- No extra spacing for groups (no groups exist)
- Natural text flow

**6.3 Colors**

- Streaming: Primary color or accent (e.g., `text-primary-600`)
- Completed: Gray (e.g., `text-neutral-500` or `text-gray-500`)
- Error: Red/amber (e.g., `text-red-600` or `text-amber-600`)

**6.4 Animation**

- Smooth transition from shiny to gray (300ms)
- Shiny animation should be subtle, not distracting
- No animation for completed items

---

## Technical Considerations

### Component Structure

```typescript
// ProcessTextItem.tsx
interface ProcessTextItemProps {
  item: PhaseTimelineItem
}

const ProcessTextItem: React.FC<ProcessTextItemProps> = ({ item }) => {
  const isStreaming = item.isStreaming && item.status === 'active'
  const isCompleted = item.status === 'completed' || (!item.isStreaming && item.status === 'active')
  const isError = item.status === 'error' || item.statusVariant === 'error'
  
  const description = generateProcessDescription(item)
  const displayText = isCompleted 
    ? `已完成: ${description.replace('正在', '').replace('...', '')}`
    : isError
    ? `⚠️  错误: ${description}`
    : description
  
  return (
    <div className={`
      text-sm
      ${isStreaming ? 'text-primary-600 shiny-text' : ''}
      ${isCompleted ? 'text-gray-500' : ''}
      ${isError ? 'text-red-600' : ''}
      transition-colors duration-300
    `}>
      {displayText}
    </div>
  )
}
```

### State Management

**No Changes Needed:**
- `usePhaseInteraction` hook (already provides `isStreaming` and `status`)
- `workflowStore` (already tracks streaming state)
- WebSocket handling (already updates streaming state)

**Optional Enhancements:**
- Track completion timestamps for better state transitions
- Add completion callbacks for smoother transitions

### Performance

**Optimizations:**
- Memoize `generateProcessDescription` to avoid recalculation
- Use `React.memo` for `ProcessTextItem` if needed
- Virtual scrolling not needed (text items are lightweight)

### Accessibility

**Considerations:**
- Ensure sufficient color contrast for gray text
- Add `aria-live` region for streaming updates
- Use semantic HTML (e.g., `<p>` or `<div>` with `role="status"`)
- Screen reader announcements for state changes

---

## Migration Strategy

### Step 1: Create New Component (Non-Breaking)

1. Create `ProcessTextItem.tsx` alongside existing components
2. Test with sample data
3. Verify shiny animation and gray states

### Step 2: Add Feature Flag (Optional)

1. Add feature flag to control text-only vs. bubble display
2. Allow gradual migration
3. Test with real data

### Step 3: Update StreamTimeline

1. Replace `StreamContentBubble` with `ProcessTextItem`
2. Remove collapse/expand logic
3. Test timeline rendering

### Step 4: Update PhaseInteractionPanel

1. Remove bubble-related state and handlers
2. Simplify UI
3. Test user interactions

### Step 5: Remove Old Components (Optional)

1. Keep `StreamContentBubble` for potential future use
2. Or remove if no longer needed
3. Clean up unused imports

---

## Testing Checklist

### Visual Testing

- [ ] Streaming items show shiny animation
- [ ] Completed items show gray text
- [ ] Error items show red/amber text
- [ ] Smooth transition from shiny to gray
- [ ] Text is readable and properly sized
- [ ] Spacing is consistent

### Functional Testing

- [ ] Process descriptions are accurate
- [ ] State transitions work correctly (streaming → completed)
- [ ] Summarization progress updates trigger completion
- [ ] Multiple concurrent processes display correctly
- [ ] Error states display correctly

### Edge Cases

- [ ] Items with missing metadata show fallback text
- [ ] Items with unknown component types show generic text
- [ ] Rapid state changes don't cause flickering
- [ ] Long process descriptions don't break layout

---

## Open Questions

1. **Shiny Animation Style**: 
   - Should it be subtle or more prominent? --more prominent, referencing cursor agent design
   - Should it use gradient or solid color with animation? --gradient
   - Should it pulse or shimmer? --shimmer, referencing cursor agent design

2. **Completed Text Format**:
   - Should it always say "已完成:" or just show gray text? it should say 已完成 + show that string in gray
   - Should it include completion timestamp? ok, but show it as very light gray
   - Should it show duration? no

3. **Process Descriptions**:
   - How detailed should descriptions be? very simple one-liner
   - Should they include step numbers, goals, etc.? no
   - Should they be configurable? No, keep it simple and fixed.

4. **Error Handling**:
   - Should errors be dismissible? yes
   - Should errors show more details on hover/click? click to expand
   - Should errors persist or auto-dismiss? auto-dismiss

5. **Status Statements**:
   - Should status statements (from `StreamStatusStatement`) also be text-only? text only.
   - Should they be integrated with process items? yes integrate.
   - Should they have different styling? you decide.

6. **Pagination**:
   - How many text items to show before "Load more"? you decide.
   - Should completed items auto-hide after a certain time? you decide.
   - Should there be a "Clear completed" action? no.

---

## Success Criteria

### User Experience

1. **Clarity**: Users can easily see what processes are running
2. **Simplicity**: No visual clutter from bubbles
3. **Feedback**: Clear indication of streaming vs. completed states
4. **Readability**: Text is easy to read and understand

### Technical

1. **Performance**: No performance degradation from animations
2. **Maintainability**: Code is simpler and easier to maintain
3. **Accessibility**: Meets accessibility standards
4. **Compatibility**: Works across browsers and devices

---

## References

- Current implementation: `client/src/components/phaseCommon/StreamContentBubble.tsx`
- Timeline component: `client/src/components/phaseCommon/StreamTimeline.tsx`
- Panel component: `client/src/components/phaseCommon/PhaseInteractionPanel.tsx`
- Shiny text component: `client/src/components/common/ShinyText.tsx`
- Related design: `docs/frontend/RIGHT_COLUMN_DESIGN_IMPROVEMENT.md`

---

**Document Status:** Design Plan - Ready for Review  
**Last Updated:** 2025-01-27

