# Right Column Design Improvement Plan

**Date:** 2025-11-14
**Status:** Design Plan (Not Implemented)  
**Priority:** High

## Overview

This document outlines a comprehensive design plan for improving the right column (`PhaseInteractionPanel`) to behave like a **chat interface** (similar to Cursor's agent chat) rather than a structured report. The goal is to create a natural, conversational experience where messages flow chronologically with minimal visual structure, helping users focus on the conversation with the AI agent.

---

## Current State Analysis

### Current Implementation

The right column (`PhaseInteractionPanel`) currently displays:
- **Header**: Status indicator, phase number, latency, current action, summarization progress
- **Content Area**: Scrollable timeline of streamed items (`StreamTimeline`)
  - Status statements
  - Content bubbles (collapsible)
  - Active streaming indicators
- **Footer**: User input area (prompt or conversation mode)

### Current Behaviors

1. **Auto-scroll**: Scrolls to bottom when new items arrive (if user is near bottom)
2. **Auto-collapse**: Streaming items auto-collapse after 2-4 seconds (random threshold)
3. **Show More**: Button to load older items (increments by 6)
4. **Collapse State**: Manual toggle per item, with auto-collapse for streaming items
5. **Visible Count**: Shows last N items (default 8, increases with "Show More")

### Identified Issues

1. **Information Overload**: Too many items visible at once, hard to focus
2. **Clutter**: Status statements, content bubbles, and metadata compete for attention
3. **Auto-collapse Timing**: Random 2-4 second threshold may be too aggressive or inconsistent
4. **Scrolling Confusion**: Auto-scroll can interrupt user's manual scrolling
5. **No Priority System**: All items treated equally, no way to highlight important information
6. **No Filtering**: Can't filter by type, phase, or importance
7. **Limited Context**: Hard to see what's currently happening vs. historical items

---

## Design Goals

### Primary Goals

1. **Chat-Like Experience**: 
   - Messages flow naturally like a conversation
   - No section headers, groups, or visual separators
   - Simple chronological order (newest at bottom)
   - Feels like talking to an AI agent, not reading a report

2. **Focus on Active Conversation**: 
   - Streaming messages always visible and expanded
   - Completed messages auto-collapse to summaries
   - Critical messages (prompts, errors) always visible
   - Natural message flow without structure

3. **Smart Collapse Logic**:
   - Auto-collapse completed messages after 3 seconds
   - Keep streaming messages expanded
   - Show summaries when collapsed (like chat previews)
   - User can expand any message to see full content

4. **Natural Scrolling**:
   - Auto-scroll to new messages (if user near bottom)
   - "New content" indicator when scrolled away
   - "Jump to bottom" button for quick return
   - Smooth, chat-like scrolling behavior

---

## Proposed Design

### 1. Content Prioritization System

#### Priority Levels

**Level 1: Critical (Always Visible, Never Auto-Collapse)**
- User input prompts (waiting for user response)
- Error messages
- Phase transitions
- Critical status updates

**Level 2: Active (Visible, Auto-Collapse After Completion)**
- Currently streaming items
- Active processing steps
- Recent completions (last 1-2 completed items)

**Level 3: Recent (Collapsed by Default, Expandable)**
- Completed items from current session
- Recent status updates (non-critical)

**Level 4: Historical (Hidden by Default, "Show More" to Reveal)**
- Older completed items
- Past status statements
- Historical context

#### Chat-Like Visual Flow

**Design Philosophy: Chat Experience, Not Report**

The right column should feel like a natural conversation with the AI agent, similar to Cursor's chat interface. Messages flow naturally from top to bottom, with minimal visual structure.

```
┌─────────────────────────────────────────┐
│ [Header - Status, Phase, Latency]       │
├─────────────────────────────────────────┤
│                                         │
│  ┌───────────────────────────────────┐ │
│  │ 🤖 AI: Analyzing step 3...         │ │ ← Streaming (expanded)
│  │    [Content streaming in real-time] │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │ 🤖 AI: Step 2 completed            │ │ ← Completed (collapsed)
│  │    Analyzed 5 sources...           │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │ 🤖 AI: Step 1 completed            │ │ ← Completed (collapsed)
│  │    Initial analysis done...        │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │ ⚠️  AI: Need your input            │ │ ← Critical (always visible)
│  │    Which approach should I take?   │ │
│  │    [Choice A] [Choice B]           │ │
│  └───────────────────────────────────┘ │
│                                         │
│  [Older messages collapsed...]          │
│  [Show more]                            │
│                                         │
├─────────────────────────────────────────┤
│ [Footer - Input Area]                  │
└─────────────────────────────────────────┘
```

**Key Differences from Report Style:**
- ❌ No section headers ("Active Now", "Recent", "History")
- ❌ No visual separators between sections
- ❌ No grouping labels or counts
- ✅ Natural message flow like chat
- ✅ Simple collapse/expand per message
- ✅ Minimal visual structure
- ✅ Focus on conversation flow

### 2. Smart Collapse Logic

#### Collapse Rules

**Auto-Collapse Triggers:**
1. **On Completion**: Item transitions from "active" to "completed" → Auto-collapse after 3 seconds
2. **On New Active Item**: When a new active item appears → Collapse oldest completed items if more than 3 visible
3. **On User Scroll Away**: If user scrolls up and stays there for 5+ seconds → Collapse completed items below viewport
4. **On Phase Change**: When phase changes → Collapse all items from previous phase (except last 1-2)

**Never Auto-Collapse:**
- Items with `priority: 'critical'` (user prompts, errors)
- Items user manually expanded
- Currently streaming items
- Items completed less than 3 seconds ago

**Manual Override:**
- User can pin items to prevent auto-collapse
- User can set default collapse preference per item type
- User preferences persist across sessions

#### Collapse Animation

- Smooth height transition (300ms)
- Show summary/preview when collapsed
- Visual indicator (chevron/arrow) for expandable state

### 3. Scrolling Behavior

#### Smart Auto-Scroll

**Auto-Scroll Conditions:**
1. **New Critical Item**: Always scroll to show (user input, errors)
2. **New Active Item**: Scroll if user is within 200px of bottom
3. **User Near Bottom**: If user is within 150px of bottom, auto-scroll to new items
4. **User Scrolled Up**: Don't auto-scroll, show "New content" indicator

**Scroll Indicators:**
- **"New content below" badge**: Appears when new items arrive while user is scrolled up
- **"Jump to bottom" button**: Floating button to quickly return to latest content
- **Scroll position memory**: Remember where user was when they manually scroll

#### Scroll Zones

```
┌─────────────────────────────────┐
│ [Scroll Up Zone]                │
│ Historical items (collapsed)    │
│                                 │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │ ← Viewport Top
│                                 │
│ [Focus Zone]                    │
│ Active & Recent items           │
│ (expanded, visible)             │
│                                 │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │ ← Viewport Bottom
│                                 │
│ [Scroll Down Zone]              │
│ New items arriving              │
│ [New content indicator]        │
└─────────────────────────────────┘
```

### 4. Chat-Style Content Flow

#### Natural Message Flow

**No Explicit Grouping:**
- Messages appear in chronological order (newest at bottom)
- No section headers or visual separators
- Messages flow naturally like a chat conversation
- Only visual distinction: expanded vs collapsed state

**Message States:**
1. **Streaming** (expanded, auto-scrolls)
   - Currently being generated
   - Always visible and expanded
   - Real-time content updates

2. **Just Completed** (expanded briefly, then auto-collapses)
   - Recently finished (last 3 seconds)
   - Shows full content
   - Auto-collapses to summary after 3 seconds

3. **Completed** (collapsed by default)
   - Shows summary/preview
   - User can expand to see full content
   - Stays collapsed unless user expands

4. **Critical** (always expanded)
   - User prompts, errors
   - Never auto-collapses
   - Highlighted visually

#### Simple Filtering (Optional)

**Minimal Filtering:**
- 🔍 **Search**: Simple search bar to find messages (optional, hidden by default)
- No complex filters - keep it simple like chat
- Search highlights matching messages
- Can expand/collapse search results

**No Advanced Filters:**
- No phase filters
- No status filters  
- No date filters
- Keep it chat-simple

### 5. Visual Design Improvements

#### Reduced Clutter

**Status Statements:**
- Treat like chat messages (not separate category)
- Smaller, lighter style (like system messages in chat)
- Inline with other messages, no special grouping
- Auto-collapse older status messages

**Content Bubbles:**
- Clearer visual distinction between active and completed
- Active: Primary color border, subtle background glow
- Completed: Neutral border, collapsed by default
- Error: Red border, always expanded

**Metadata:**
- Hide metadata by default
- Show on hover or in expanded view only
- Group metadata in collapsible section

#### Visual Hierarchy

**Color Coding:**
- 🔴 Critical (user prompts, errors): Amber/Red
- 🔵 Active (streaming): Primary blue/yellow
- 🟢 Completed: Neutral gray
- ⚪ Historical: Light gray, collapsed

**Typography:**
- Critical items: Bold, larger font
- Active items: Medium weight, standard size
- Completed items: Regular weight, smaller when collapsed
- Historical items: Lighter weight, minimal

**Spacing:**
- Consistent spacing between messages (like chat)
- No extra spacing for "groups" (no groups exist)
- Natural message flow spacing

### 6. Interaction Improvements

#### Quick Actions

**Per Item:**
- ⭐ **Pin**: Prevent auto-collapse
- 📋 **Copy**: Copy content
- 🔗 **Link**: Jump to related item
- ❌ **Dismiss**: Hide from view (can restore)

**Bulk Actions:**
- "Collapse All Completed"
- "Expand All Active"
- "Clear Historical Items"
- "Export Timeline"

#### Keyboard Shortcuts

- `J` / `K`: Navigate up/down items
- `Space`: Toggle collapse/expand current item
- `G` then `G`: Jump to bottom
- `G` then `T`: Jump to top
- `/`: Focus search
- `Esc`: Clear filters/search

### 7. Simple Message Visibility

#### Chat-Style Visibility

**Default Behavior:**
- Show last ~10-15 messages (like chat)
- New messages appear at bottom
- Older messages auto-collapse
- "Load more" button to see older messages (like infinite scroll in chat)

**No View Modes:**
- No "minimal/standard/full" modes
- Just natural chat flow
- Messages appear and collapse naturally
- User can expand any message they want to see

**Simple Controls:**
- Scroll to see history
- Click "Load more" for older messages
- Expand/collapse individual messages
- No complex view toggles

---

## Implementation Strategy

### Phase 1: Priority System

1. Add priority field to `PhaseTimelineItem` type
2. Implement priority calculation logic:
   - User prompts → `critical`
   - Errors → `critical`
   - Active streaming → `active`
   - Recent completions → `recent`
   - Older items → `historical`
3. Update rendering to respect priority
4. Visual styling based on priority

### Phase 2: Smart Collapse

1. Refine auto-collapse logic:
   - Remove random threshold
   - Use fixed 3-second delay after completion
   - Implement "pin" functionality
   - Track user manual preferences
2. Add collapse animations
3. Improve summary/preview generation
4. Add visual indicators for collapse state

### Phase 3: Scrolling Improvements

1. Implement smart auto-scroll logic
2. Add "New content" indicator
3. Add "Jump to bottom" button
4. Implement scroll position memory
5. Add smooth scroll animations

### Phase 4: Chat-Style Flow

1. Remove all grouping logic and visual separators
2. Implement natural message flow (chronological)
3. Add simple search (optional, minimal UI)
4. Implement "Load more" for older messages
5. Ensure smooth chat-like scrolling

### Phase 5: Visual Polish

1. Reduce visual clutter:
   - Smaller status statements
   - Hide metadata by default
   - Group related items
2. Improve typography hierarchy
3. Add color coding
4. Improve spacing
5. Add animations and transitions

### Phase 6: Chat Polish

1. Remove view mode toggles (no modes needed)
2. Ensure natural message flow
3. Add smooth animations for message appearance
4. Implement chat-like keyboard shortcuts (simple)
5. Remove bulk actions (keep it simple)

---

## Technical Considerations

### Data Structure Changes

```typescript
interface PhaseTimelineItem {
  id: string
  type: 'status' | 'content' | 'prompt'
  priority: 'critical' | 'active' | 'recent' | 'historical'
  status: 'active' | 'completed' | 'error'
  isStreaming: boolean
  message: string
  preview?: string  // For collapsed state
  summary?: string  // Auto-generated summary
  metadata?: Record<string, any>
  timestamp: string
  phase?: string
  isPinned?: boolean  // User pinned to prevent auto-collapse
  defaultCollapsed: boolean
  // ... existing fields
}
```

### State Management

```typescript
interface RightColumnState {
  // Simple search (optional)
  searchQuery: string
  showSearch: boolean
  
  // Collapse state
  collapsedState: Record<string, boolean>
  pinnedItems: Set<string>
  
  // Scrolling
  scrollPosition: number
  isUserScrolled: boolean
  hasNewContentBelow: boolean
  visibleMessageCount: number  // For "load more"
}
```

### Performance Considerations

1. **Virtual Scrolling**: For large timelines (100+ items), consider virtual scrolling
2. **Lazy Rendering**: Only render visible items + buffer
3. **Memoization**: Memoize expensive calculations (summaries, grouping)
4. **Debouncing**: Debounce scroll events and filter changes
5. **Request Animation Frame**: Use RAF for smooth animations

---

## User Experience Flow

### Scenario 1: Normal Research Flow (Chat Experience)

1. User starts research → Chat shows empty state (like new chat)
2. AI message appears → "Starting phase 1 analysis..." (streaming, expanded)
3. Message streams content → User sees real-time updates (like typing indicator)
4. Message completes → Auto-collapses after 3 seconds, shows summary preview
5. New AI message appears → "Analyzing sources..." (streaming, expanded, auto-scrolls)
6. User prompt appears → "Need your input: Which approach?" (always visible, highlighted)
7. User responds → Prompt disappears, new AI message appears
8. Multiple messages complete → All collapse to summaries, only streaming visible
9. User scrolls up to read history → Auto-scroll pauses, "New message" badge appears
10. User clicks "Jump to bottom" → Smoothly scrolls to latest message (like chat)

### Scenario 2: User Wants to Review Chat History

1. User scrolls up → Older messages appear (collapsed, like chat history)
2. User clicks "Load more" → Loads older messages (like infinite scroll in chat)
3. User expands specific message → Message expands, shows full content
4. User pins message → Message never auto-collapses (stays in view)
5. User scrolls through history → Smooth scrolling, natural message flow
6. User clicks "Jump to bottom" → Returns to latest message (like chat)

### Scenario 3: Error or User Prompt (Chat)

1. Error occurs → Error message appears (like chat message, always visible, highlighted)
2. User prompt appears → "⚠️ Need your input: [question]" (highlighted message, input focused)
3. User responds → Prompt message disappears, new AI message appears
4. Error resolved → Error message collapses after 5 seconds (longer than normal, like chat)

---

## Metrics for Success

### User Experience Metrics

1. **Time to Find Important Info**: < 2 seconds to see user prompts/errors
2. **Scroll Interruptions**: < 10% of users report scroll interruptions
3. **Clutter Perception**: > 80% users report reduced clutter
4. **Focus Ability**: > 70% users can easily focus on active work

### Technical Metrics

1. **Render Performance**: < 16ms per frame (60 FPS)
2. **Memory Usage**: < 50MB for 1000 items
3. **Scroll Smoothness**: 60 FPS during scroll
4. **Auto-collapse Accuracy**: < 5% false positives (collapsing when shouldn't)

---

## Open Questions

1. **Auto-collapse Delay**: Is 3 seconds optimal, or should it be configurable?
2. **Message Limit**: How many messages to show before "Load more"? (10-15 seems reasonable)
3. **Search UI**: Should search be always visible or hidden behind a button?
4. **Export Functionality**: Should users be able to export the chat history?
5. **Mobile Experience**: How should this adapt to smaller screens?
6. **Accessibility**: How to ensure screen readers work well with dynamic chat content?
7. **Message Density**: How much spacing between messages feels natural?

---

## Next Steps

1. **Review & Approval**: Review this design plan with stakeholders
2. **Prototype**: Create interactive prototype for key interactions
3. **User Testing**: Test with real users to validate assumptions
4. **Implementation**: Implement in phases as outlined above
5. **Iteration**: Refine based on user feedback

---

## References

- Current implementation: `client/src/components/phaseCommon/PhaseInteractionPanel.tsx`
- Timeline component: `client/src/components/phaseCommon/StreamTimeline.tsx`
- Content bubble: `client/src/components/phaseCommon/StreamContentBubble.tsx`
- Related design: `docs/frontend/USER_GUIDANCE_PAGE_REDESIGN.md`

---

**Document Status:** Design Plan - Ready for Review  
**Last Updated:** 2025-01-27

