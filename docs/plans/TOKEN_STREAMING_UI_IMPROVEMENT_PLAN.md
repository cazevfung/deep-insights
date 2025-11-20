# Token Streaming UI Improvement Plan

## Problem Statement

Throughout all research phases (Phase 0-4), token outputs are being received as streams from the AI API, but they are **NOT being displayed in real-time** to users. Currently, users only see periodic progress messages like "正在接收响应... (190 tokens)" instead of seeing the actual token stream building up in real-time, similar to how Cursor displays AI responses.

The goal is to implement the "Cursor way" of showing streamed token output in real-time in a box, then parse these outputs in real-time and show relevant information structurally in the interface. This will give users confidence that things are happening.

## Current State Analysis

### Infrastructure That Exists

1. **Backend Streaming Support**:
   - `WebSocketUI.display_stream(token: str)` - Sends tokens via WebSocket
   - `WebSocketUI._send_stream_token(token: str)` - Async helper for streaming
   - WebSocket message type: `research:stream_token`

2. **Frontend Streaming Support**:
   - `useWebSocket.ts` handles `research:stream_token` messages
   - `workflowStore.ts` has `streamBuffer` state and `appendStreamToken()` function
   - `ResearchAgentPage.tsx` displays `streamBuffer` in a box (lines 411-417)

3. **Base Phase Infrastructure**:
   - `BasePhase._stream_with_callback()` receives tokens in a callback
   - Currently only sends periodic progress messages, NOT actual tokens

### What's Missing

**The token callback in `_stream_with_callback()` receives tokens but never calls `ui.display_stream()` to send them to the frontend.**

## Identified Issues by Phase

### 🔴 Priority 1: Phase 0 - Summarization (Critical)

**Location**: `research/summarization/content_summarizer.py`

**Current Behavior**:
- Uses `client.stream_completion()` which yields tokens one by one
- Collects all tokens in `response_text += token` loop (lines 155-161, 221-227)
- **NEVER calls `ui.display_stream()` to show tokens in real-time**
- Only sends progress updates via `display_summarization_progress()` (item-level progress, not token-level)

**Code Reference**:
```python
# Lines 154-161 in content_summarizer.py
if hasattr(self.client, 'stream_completion'):
    # Collect all streamed tokens
    for token in self.client.stream_completion(
        messages=messages,
        model=self.model,
        temperature=0.3,
        max_tokens=2000
    ):
        response_text += token  # ← Tokens collected but NOT displayed
```

**Problem**: 
- No access to `ui` object in `ContentSummarizer`
- No real-time token streaming to frontend
- Users see "正在总结 [1/5]: yt_req1" but no actual content being generated

**Impact**: High - Phase 0 can take 5-30 seconds per item, users see nothing happening

---

### 🔴 Priority 2: Phase 0.5 - Role Generation

**Location**: `research/phases/phase0_5_role_generation.py`

**Current Behavior**:
- Uses `_stream_with_callback()` from `BasePhase`
- Callback receives tokens but only updates progress tracker
- Only sends periodic progress messages (every 10 tokens or 2 seconds)
- **Never calls `ui.display_stream()` to show actual tokens**

**Code Reference**:
```python
# Lines 143-157 in base_phase.py
def callback(token: str):
    nonlocal token_count, last_update_time, last_token_time
    token_count += 1
    current_time = time.time()
    last_token_time = current_time
    
    # Update progress tracker
    if self.progress_tracker:
        self.progress_tracker.stream_update(token)
    
    # Send periodic progress updates to UI
    if self.ui and (token_count % 10 == 0 or current_time - last_update_time >= update_interval):
        self.ui.display_message(f"正在接收响应... ({token_count} tokens)", "info")
        last_update_time = current_time
    # ← MISSING: self.ui.display_stream(token) to show actual tokens!
```

**Impact**: Medium - Single API call, but users can't see what role is being generated

---

### 🔴 Priority 3: Phase 1 - Discovery

**Location**: `research/phases/phase1_discover.py`

**Current Behavior**:
- Uses `_stream_with_callback()` (line 77, 145)
- Same issue as Phase 0.5: tokens received but not streamed to UI
- Only shows "正在接收响应... (190 tokens)" type messages

**Impact**: High - Users can't see goals being generated in real-time

---

### 🔴 Priority 4: Phase 2 - Synthesis

**Location**: `research/phases/phase2_synthesize.py`

**Current Behavior**:
- Uses `_stream_with_callback()` (line 82)
- Same issue: tokens received but not streamed
- Users can't see synthesized goal being generated

**Impact**: High - Important phase, users should see synthesis happening

---

### 🔴 Priority 5: Phase 3 - Execute

**Location**: `research/phases/phase3_execute.py`

**Current Behavior**:
- Uses `_stream_with_callback()` multiple times:
  - Line 868: Initial step execution
  - Line 1040: Follow-up retrieval turns
- Same issue: tokens received but not streamed
- Users can't see research findings being generated step by step

**Impact**: Very High - This is the core research phase, users should see insights being generated

---

### 🔴 Priority 6: Phase 4 - Final Synthesis

**Location**: `research/phases/phase4_synthesize.py`

**Current Behavior**:
- Uses `_stream_with_callback()` multiple times:
  - Line 91: Outline generation
  - Line 137: Section generation (in loop)
- Same issue: tokens received but not streamed
- Users can't see report being written section by section

**Impact**: Very High - Final report generation, users should see content being written

---

## Solution Plan

### Architecture: Two-Level Display System

**Level 1: Raw Token Stream Box (Cursor-style)**
- Show all streamed tokens in real-time in a scrollable box
- Auto-scroll to bottom as new tokens arrive
- Monospace font for readability
- Clear visual indicator when streaming is active

**Level 2: Structured Information Display**
- Parse streamed content in real-time (when possible)
- Show structured information as it becomes available
- Examples:
  - Phase 1: Show goals as they're generated
  - Phase 3: Show findings as they're extracted
  - Phase 4: Show report sections as they're written

### Implementation Strategy

#### Step 1: Fix Base Phase Token Streaming

**File**: `research/phases/base_phase.py`

**Changes to `_stream_with_callback()`**:

```python
def _stream_with_callback(self, messages: List[Dict[str, str]], **kwargs) -> str:
    """
    Stream API call with progress callback.
    Enhanced to stream tokens to UI in real-time.
    """
    import time
    import threading
    
    # Send "starting" update
    if self.ui:
        self.ui.display_message("正在调用AI API...", "info")
        # Clear previous stream buffer
        self.ui.clear_stream_buffer()
    
    token_count = 0
    last_update_time = time.time()
    last_token_time = time.time()
    update_interval = 2.0  # Update every 2 seconds
    heartbeat_interval = 15.0
    heartbeat_active = True
    
    # Heartbeat thread (existing code)
    def heartbeat_worker():
        # ... existing heartbeat code ...
    
    heartbeat_thread = threading.Thread(target=heartbeat_worker, daemon=True)
    heartbeat_thread.start()
    
    def callback(token: str):
        nonlocal token_count, last_update_time, last_token_time
        
        token_count += 1
        current_time = time.time()
        last_token_time = current_time
        
        # Update progress tracker
        if self.progress_tracker:
            self.progress_tracker.stream_update(token)
        
        # ✨ NEW: Stream token to UI in real-time
        if self.ui:
            self.ui.display_stream(token)  # ← ADD THIS LINE
        
        # Send periodic progress updates to UI (keep existing behavior)
        if self.ui and (token_count % 10 == 0 or current_time - last_update_time >= update_interval):
            self.ui.display_message(f"正在接收响应... ({token_count} tokens)", "info")
            last_update_time = current_time
    
    # ... rest of existing code ...
```

**Key Changes**:
1. Add `self.ui.clear_stream_buffer()` at start
2. Add `self.ui.display_stream(token)` in callback
3. Keep existing progress messages for backward compatibility

---

#### Step 2: Fix Phase 0 Summarization Token Streaming

**File**: `research/summarization/content_summarizer.py`

**Problem**: `ContentSummarizer` doesn't have access to `ui` object.

**Solution**: Pass `ui` object to `ContentSummarizer` and use it for streaming.

**Changes**:

1. **Modify `__init__` to accept `ui` parameter**:
```python
def __init__(self, client=None, config=None, ui=None):
    """
    Initialize content summarizer.
    
    Args:
        client: QwenStreamingClient instance
        config: Config instance
        ui: UI interface for streaming tokens (optional)
    """
    # ... existing code ...
    self.ui = ui
```

2. **Modify `_summarize_transcript()` to stream tokens**:
```python
def _summarize_transcript(self, transcript: str) -> Dict[str, Any]:
    # ... existing setup code ...
    
    try:
        messages = [{"role": "user", "content": full_prompt}]
        response_text = ""
        
        # Check if client has stream_completion
        if hasattr(self.client, 'stream_completion'):
            # ✨ NEW: Clear stream buffer if UI available
            if self.ui:
                self.ui.clear_stream_buffer()
                self.ui.display_message("正在总结转录本内容...", "info")
            
            # Collect all streamed tokens AND stream to UI
            for token in self.client.stream_completion(
                messages=messages,
                model=self.model,
                temperature=0.3,
                max_tokens=2000
            ):
                response_text += token
                # ✨ NEW: Stream token to UI in real-time
                if self.ui:
                    self.ui.display_stream(token)
            
            # ... rest of existing code ...
```

3. **Modify `_summarize_comments()` similarly**:
```python
def _summarize_comments(self, comments: List) -> Dict[str, Any]:
    # ... existing setup code ...
    
    try:
        messages = [{"role": "user", "content": full_prompt}]
        response_text = ""
        
        if hasattr(self.client, 'stream_completion'):
            # ✨ NEW: Clear stream buffer if UI available
            if self.ui:
                self.ui.clear_stream_buffer()
                self.ui.display_message("正在总结评论内容...", "info")
            
            for token in self.client.stream_completion(
                messages=messages,
                model=self.model,
                temperature=0.3,
                max_tokens=2000
            ):
                response_text += token
                # ✨ NEW: Stream token to UI in real-time
                if self.ui:
                    self.ui.display_stream(token)
            
            # ... rest of existing code ...
```

4. **Update Phase 0 to pass `ui` to ContentSummarizer**:
```python
# In phase0_prepare.py, _summarize_content_items()
# Line 124
summarizer = ContentSummarizer(client=self.client, config=self.config, ui=self.ui)
```

---

#### Step 3: Create Consistent Design Language for Token Streaming

**Goal**: Create a reusable, consistent design system for token streaming across all phases using Tailwind CSS and React components.

**Approach**: 
1. Create a reusable `StreamDisplay` component
2. Define design tokens/constants for consistent styling
3. Extend Tailwind config with stream-specific utilities
4. Create a hook for stream state management
5. Use the component consistently across all phases

---

##### 3.1: Create Reusable StreamDisplay Component

**File**: `client/src/components/streaming/StreamDisplay.tsx`

**Purpose**: Single source of truth for token stream display with consistent styling and behavior.

```tsx
import React, { useEffect, useRef, useState } from 'react'
import { useWorkflowStore } from '../../stores/workflowStore'
import Button from '../common/Button'
import Card from '../common/Card'

interface StreamDisplayProps {
  /** Stream content to display */
  content: string
  /** Phase/context identifier for display */
  phase?: string
  /** Whether streaming is currently active */
  isStreaming?: boolean
  /** Optional title override */
  title?: string
  /** Optional subtitle/description */
  subtitle?: string
  /** Whether to show copy button */
  showCopyButton?: boolean
  /** Whether to show collapse/expand button */
  collapsible?: boolean
  /** Custom className for container */
  className?: string
  /** Height constraints */
  minHeight?: string
  maxHeight?: string
}

const StreamDisplay: React.FC<StreamDisplayProps> = ({
  content,
  phase,
  isStreaming = false,
  title,
  subtitle,
  showCopyButton = true,
  collapsible = false,
  className = '',
  minHeight = 'min-h-64',
  maxHeight = 'max-h-96',
}) => {
  const streamRef = useRef<HTMLDivElement>(null)
  const [isExpanded, setIsExpanded] = useState(true)
  const [isCopied, setIsCopied] = useState(false)

  // Auto-scroll to bottom when content changes
  useEffect(() => {
    if (streamRef.current && content && isExpanded) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight
    }
  }, [content, isExpanded])

  // Copy to clipboard handler
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setIsCopied(true)
      setTimeout(() => setIsCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  // Generate phase-specific title if not provided
  const displayTitle = title || getPhaseTitle(phase) || 'AI 响应流'

  if (!content) {
    return null
  }

  return (
    <Card
      className={`stream-display-container ${className}`}
      title={
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2">
            <span>{displayTitle}</span>
            {isStreaming && (
              <span className="stream-indicator" aria-label="Streaming active">
                <span className="stream-dot" />
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {collapsible && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsExpanded(!isExpanded)}
                className="text-xs"
              >
                {isExpanded ? '收起' : '展开'}
              </Button>
            )}
            {showCopyButton && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopy}
                className="text-xs"
              >
                {isCopied ? '已复制' : '复制'}
              </Button>
            )}
          </div>
        </div>
      }
      subtitle={subtitle}
    >
      <div
        className={`stream-content-wrapper ${minHeight} ${isExpanded ? maxHeight : ''} ${
          isExpanded ? 'overflow-auto' : 'overflow-hidden'
        }`}
      >
        {isExpanded ? (
          <div
            ref={streamRef}
            className="stream-content font-mono text-sm whitespace-pre-wrap text-neutral-800 leading-relaxed"
          >
            {content}
          </div>
        ) : (
          <div className="stream-content-preview text-sm text-neutral-400">
            {content.substring(0, 100)}... (已收起)
          </div>
        )}
      </div>
    </Card>
  )
}

// Helper function to get phase-specific titles
function getPhaseTitle(phase?: string): string | null {
  const phaseTitles: Record<string, string> = {
    phase0: '阶段 0: 数据准备 - AI 响应',
    phase0_5: '阶段 0.5: 角色生成 - AI 响应',
    phase1: '阶段 1: 发现 - AI 响应',
    phase2: '阶段 2: 综合 - AI 响应',
    phase3: '阶段 3: 执行 - AI 响应',
    phase4: '阶段 4: 最终综合 - AI 响应',
    summarization: '内容总结 - AI 响应',
  }
  return phase ? phaseTitles[phase] || null : null
}

export default StreamDisplay
```

---

##### 3.2: Define Design Tokens and Constants

**File**: `client/src/components/streaming/streamDesignTokens.ts`

**Purpose**: Centralized design constants for consistent styling across all stream displays.

```typescript
/**
 * Design tokens for token streaming UI components
 * Ensures consistent styling across all phases
 */

export const streamDesignTokens = {
  // Colors
  colors: {
    containerBg: 'bg-neutral-white',
    containerBorder: 'border-neutral-300',
    textPrimary: 'text-neutral-800',
    textSecondary: 'text-neutral-400',
    textMuted: 'text-neutral-500',
    indicatorActive: 'bg-supportive-green',
    indicatorPulse: 'animate-pulse',
  },

  // Spacing
  spacing: {
    containerPadding: 'p-6',
    contentPadding: 'p-4',
    gap: 'gap-2',
  },

  // Typography
  typography: {
    fontFamily: 'font-mono',
    fontSize: 'text-sm',
    lineHeight: 'leading-relaxed',
    whitespace: 'whitespace-pre-wrap',
  },

  // Sizing
  sizing: {
    minHeight: 'min-h-64',
    maxHeight: 'max-h-96',
    minHeightCompact: 'min-h-32',
    maxHeightCompact: 'max-h-64',
    minHeightExpanded: 'min-h-96',
    maxHeightExpanded: 'max-h-[600px]',
  },

  // Borders & Shadows
  borders: {
    container: 'rounded-lg border border-neutral-300',
    containerHighlight: 'rounded-lg border-2 border-primary-300',
  },

  // Animations
  animations: {
    indicatorPulse: 'animate-pulse',
    fadeIn: 'animate-fade-in',
    slideDown: 'animate-slide-down',
  },
} as const

/**
 * Stream display variants for different use cases
 */
export const streamVariants = {
  default: {
    minHeight: streamDesignTokens.sizing.minHeight,
    maxHeight: streamDesignTokens.sizing.maxHeight,
    showCopyButton: true,
    collapsible: false,
  },
  compact: {
    minHeight: streamDesignTokens.sizing.minHeightCompact,
    maxHeight: streamDesignTokens.sizing.maxHeightCompact,
    showCopyButton: true,
    collapsible: true,
  },
  expanded: {
    minHeight: streamDesignTokens.sizing.minHeightExpanded,
    maxHeight: streamDesignTokens.sizing.maxHeightExpanded,
    showCopyButton: true,
    collapsible: true,
  },
  inline: {
    minHeight: 'min-h-32',
    maxHeight: 'max-h-48',
    showCopyButton: false,
    collapsible: false,
  },
} as const

export type StreamVariant = keyof typeof streamVariants
```

---

##### 3.3: Extend Tailwind Config with Stream Utilities

**File**: `client/tailwind.config.js`

**Changes**: Add stream-specific utilities and animations.

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // ... existing extensions ...
      
      // Stream-specific animations
      keyframes: {
        'stream-pulse': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        'stream-fade-in': {
          '0%': { opacity: '0', transform: 'translateY(-4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'stream-slide-down': {
          '0%': { opacity: '0', transform: 'translateY(-8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'stream-pulse': 'stream-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'stream-fade-in': 'stream-fade-in 0.3s ease-out',
        'stream-slide-down': 'stream-slide-down 0.4s ease-out',
      },
      
      // Stream-specific spacing (if needed)
      spacing: {
        'stream-indicator': '0.5rem',
        'stream-gap': '0.5rem',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    // Add custom plugin for stream utilities
    function({ addComponents, theme }) {
      addComponents({
        '.stream-display-container': {
          backgroundColor: theme('colors.neutral.white'),
          borderRadius: theme('borderRadius.lg'),
          border: `1px solid ${theme('colors.neutral.300')}`,
          padding: theme('spacing.6'),
        },
        '.stream-indicator': {
          display: 'inline-flex',
          alignItems: 'center',
          gap: theme('spacing.1'),
        },
        '.stream-dot': {
          width: '0.5rem',
          height: '0.5rem',
          borderRadius: '50%',
          backgroundColor: theme('colors.supportive.green'),
          animation: 'stream-pulse 2s infinite',
        },
        '.stream-content-wrapper': {
          position: 'relative',
          overflow: 'auto',
          '&::-webkit-scrollbar': {
            width: '8px',
          },
          '&::-webkit-scrollbar-track': {
            backgroundColor: theme('colors.neutral.light-bg'),
            borderRadius: theme('borderRadius.md'),
          },
          '&::-webkit-scrollbar-thumb': {
            backgroundColor: theme('colors.neutral.400'),
            borderRadius: theme('borderRadius.md'),
            '&:hover': {
              backgroundColor: theme('colors.neutral.500'),
            },
          },
        },
        '.stream-content': {
          fontFamily: theme('fontFamily.mono'),
          fontSize: theme('fontSize.sm'),
          lineHeight: theme('lineHeight.relaxed'),
          whiteSpace: 'pre-wrap',
          color: theme('colors.neutral.800'),
          wordBreak: 'break-word',
        },
        '.stream-content-preview': {
          fontSize: theme('fontSize.sm'),
          color: theme('colors.neutral.400'),
          fontStyle: 'italic',
        },
      })
    },
  ],
}
```

---

##### 3.4: Create Stream State Hook

**File**: `client/src/hooks/useStreamState.ts`

**Purpose**: Centralized hook for managing stream state and detecting active streaming.

```typescript
import { useEffect, useState, useRef } from 'react'
import { useWorkflowStore } from '../stores/workflowStore'

interface UseStreamStateOptions {
  /** Timeout in ms to consider stream inactive */
  inactivityTimeout?: number
  /** Phase identifier */
  phase?: string
}

export function useStreamState(options: UseStreamStateOptions = {}) {
  const { inactivityTimeout = 3000, phase } = options
  const { researchAgentStatus } = useWorkflowStore()
  const [isStreaming, setIsStreaming] = useState(false)
  const lastUpdateRef = useRef<number>(0)
  const timeoutRef = useRef<NodeJS.Timeout>()

  useEffect(() => {
    const streamBuffer = researchAgentStatus.streamBuffer || ''
    const hasContent = streamBuffer.length > 0

    if (hasContent) {
      lastUpdateRef.current = Date.now()
      setIsStreaming(true)

      // Clear existing timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }

      // Set new timeout to mark as inactive
      timeoutRef.current = setTimeout(() => {
        const timeSinceLastUpdate = Date.now() - lastUpdateRef.current
        if (timeSinceLastUpdate >= inactivityTimeout) {
          setIsStreaming(false)
        }
      }, inactivityTimeout)
    } else {
      setIsStreaming(false)
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [researchAgentStatus.streamBuffer, inactivityTimeout])

  return {
    content: researchAgentStatus.streamBuffer || '',
    isStreaming,
    phase,
    hasContent: (researchAgentStatus.streamBuffer || '').length > 0,
  }
}
```

---

##### 3.5: Update ResearchAgentPage to Use StreamDisplay

**File**: `client/src/pages/ResearchAgentPage.tsx`

**Changes**: Replace inline stream display with reusable `StreamDisplay` component.

```tsx
import StreamDisplay from '../components/streaming/StreamDisplay'
import { useStreamState } from '../hooks/useStreamState'

// ... existing code ...

const ResearchAgentPage: React.FC = () => {
  // ... existing code ...
  
  // Get stream state with phase context
  const streamState = useStreamState({
    phase: researchAgentStatus.phase || undefined,
    inactivityTimeout: 3000,
  })

  return (
    <div>
      {/* ... existing content ... */}

      {/* Replace old stream display with new component */}
      <StreamDisplay
        content={streamState.content}
        phase={researchAgentStatus.phase}
        isStreaming={streamState.isStreaming}
        showCopyButton={true}
        collapsible={true}
        subtitle={researchAgentStatus.currentAction}
      />

      {/* ... rest of content ... */}
    </div>
  )
}
```

---

##### 3.6: Create Phase-Specific Stream Wrappers (Optional)

**File**: `client/src/components/streaming/PhaseStreamDisplay.tsx`

**Purpose**: Phase-specific wrappers that add context while maintaining consistency.

```tsx
import React from 'react'
import StreamDisplay from './StreamDisplay'
import { streamVariants, StreamVariant } from './streamDesignTokens'

interface PhaseStreamDisplayProps {
  phase: 'phase0' | 'phase0_5' | 'phase1' | 'phase2' | 'phase3' | 'phase4'
  content: string
  isStreaming?: boolean
  variant?: StreamVariant
  context?: string
}

const phaseConfig = {
  phase0: {
    title: '阶段 0: 数据准备',
    icon: '📊',
    variant: 'default' as StreamVariant,
  },
  phase0_5: {
    title: '阶段 0.5: 角色生成',
    icon: '🎭',
    variant: 'compact' as StreamVariant,
  },
  phase1: {
    title: '阶段 1: 发现',
    icon: '🔍',
    variant: 'default' as StreamVariant,
  },
  phase2: {
    title: '阶段 2: 综合',
    icon: '🔗',
    variant: 'default' as StreamVariant,
  },
  phase3: {
    title: '阶段 3: 执行',
    icon: '⚡',
    variant: 'expanded' as StreamVariant,
  },
  phase4: {
    title: '阶段 4: 最终综合',
    icon: '📝',
    variant: 'expanded' as StreamVariant,
  },
}

export const PhaseStreamDisplay: React.FC<PhaseStreamDisplayProps> = ({
  phase,
  content,
  isStreaming = false,
  variant,
  context,
}) => {
  const config = phaseConfig[phase]
  const displayVariant = variant || config.variant
  const variantStyles = streamVariants[displayVariant]

  return (
    <div className="phase-stream-wrapper">
      <StreamDisplay
        content={content}
        phase={phase}
        isStreaming={isStreaming}
        title={`${config.icon} ${config.title}`}
        subtitle={context}
        {...variantStyles}
      />
    </div>
  )
}
```

---

##### 3.7: Usage Guidelines

**Consistent Usage Across All Phases**:

1. **Always use `StreamDisplay` component** - Never inline stream rendering
2. **Use design tokens** - Reference `streamDesignTokens` for styling
3. **Use `useStreamState` hook** - For consistent state management
4. **Phase-specific variants** - Use `PhaseStreamDisplay` for phase context
5. **Maintain consistency** - All streams should look and behave the same

**Example Usage in Different Phases**:

```tsx
// Phase 0 - Summarization
<StreamDisplay
  content={streamBuffer}
  phase="summarization"
  isStreaming={isStreaming}
  title="内容总结"
  subtitle={`正在处理 ${currentItem}/${totalItems} 项`}
/>

// Phase 1 - Discovery
<PhaseStreamDisplay
  phase="phase1"
  content={streamBuffer}
  isStreaming={isStreaming}
  context={currentAction}
/>

// Phase 3 - Execute (needs more space)
<PhaseStreamDisplay
  phase="phase3"
  content={streamBuffer}
  isStreaming={isStreaming}
  variant="expanded"
  context={`步骤 ${stepId}/${totalSteps}`}
/>
```

---

#### Step 4: Add Stream Start/End Indicators

**Backend**: Send `research:stream_start` and `research:stream_end` messages

**Current State**: 
- `research:stream_start` is sent but only clears buffer
- `research:stream_end` exists but doesn't do anything

**Enhancements**:

1. **Send `research:stream_start` with context**:
```python
# In base_phase.py, _stream_with_callback()
if self.ui:
    self.ui.display_message("正在调用AI API...", "info")
    self.ui.clear_stream_buffer()
    # ✨ NEW: Send stream start with phase context
    coro = self._send_stream_start()
    self._schedule_coroutine(coro)
```

2. **Add `_send_stream_start()` method**:
```python
async def _send_stream_start(self):
    """Send stream start notification."""
    try:
        await self.ws_manager.broadcast(self.batch_id, {
            "type": "research:stream_start",
            "phase": self._get_phase_name(),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to broadcast stream start: {e}")
```

3. **Send `research:stream_end` when complete**:
```python
# In base_phase.py, _stream_with_callback(), after stream completes
if self.ui:
    coro = self._send_stream_end()
    self._schedule_coroutine(coro)
```

---

#### Step 5: Design System Benefits

**Consistency Achieved**:
- ✅ **Single Component**: All phases use the same `StreamDisplay` component
- ✅ **Design Tokens**: Centralized styling constants ensure visual consistency
- ✅ **Tailwind Utilities**: Reusable classes for stream-specific styling
- ✅ **State Management**: Unified hook for stream state across all phases
- ✅ **Phase Customization**: Phase-specific variants while maintaining base consistency

**Maintainability**:
- Changes to stream styling only need to be made in one place
- Design tokens make it easy to update colors, spacing, typography
- Tailwind utilities can be extended without breaking existing components
- New phases can easily adopt the same design language

**User Experience**:
- Consistent look and feel across all phases builds user familiarity
- Same behavior (auto-scroll, copy, collapse) across all streams
- Visual indicators are consistent and recognizable
- Phase-specific context adds clarity without breaking consistency

---

#### Step 6: Real-time JSON Parsing & Structured View (Planned Enhancement)

**Goal**: While tokens are streaming (typically JSON), render two synchronized views:
1. Raw streaming tokens (existing `StreamDisplay`)
2. A structured, continuously updating visualization based on partially parsed JSON

**Key Challenges**:
- Tokens arrive incrementally; JSON may be incomplete at any moment
- Need to avoid blocking UI with expensive parsing
- Must gracefully handle malformed/unfinished JSON until stream completes

**Solution Overview**:
1. **Dual-Buffer Architecture**
   - **Raw Buffer**: Existing `streamBuffer` retains every token for display/debugging
   - **Structured Buffer**: A parser-friendly buffer that attempts incremental JSON parsing
   - Store both buffers in state so components can subscribe as needed

2. **Incremental JSON Parsing Hook** (`useStreamParser`)
   ```typescript
   import { useEffect, useState } from 'react'
   import { useWorkflowStore } from '../stores/workflowStore'
   import { incrementalParseJSON } from '../utils/streaming/jsonIncrementalParser'

   interface ParsedState {
     root: any | null
     status: 'idle' | 'parsing' | 'valid' | 'error'
     error?: string
   }

   export function useStreamParser({ enableRepair = true }: { enableRepair?: boolean } = {}) {
     const { researchAgentStatus } = useWorkflowStore()
     const [parsedState, setParsedState] = useState<ParsedState>({ root: null, status: 'idle' })

     useEffect(() => {
       const buffer = researchAgentStatus.streamBuffer
       if (!buffer) {
         setParsedState({ root: null, status: 'idle' })
         return
       }

       setParsedState(prev => ({ ...prev, status: 'parsing' }))

       try {
         const result = incrementalParseJSON(buffer, { enableRepair })
         setParsedState({ root: result, status: 'valid' })
       } catch (err: any) {
         setParsedState({ root: null, status: 'error', error: err.message })
       }
     }, [researchAgentStatus.streamBuffer, enableRepair])

     return parsedState
   }
   ```

3. **Incremental Parser Utility** (`jsonIncrementalParser.ts`)
   - Attempt to parse JSON with a streaming-friendly algorithm
   - Strategies:
     - Use libraries like [`jsonparse`](https://www.npmjs.com/package/jsonparse) or [`clarinet`](https://www.npmjs.com/package/clarinet) for token events
     - For incomplete JSON, attempt to "repair" using [`jsonrepair`](https://www.npmjs.com/package/jsonrepair) or custom heuristics
     - Maintain parser state between invocations to avoid reparsing entire buffer (optimization)
   - Provide hooks for schema-aware validation (Phase-specific JSON schemas)

   ```typescript
   import { jsonrepair } from 'jsonrepair'
   import createParser from 'jsonparse'

   export function incrementalParseJSON(buffer: string, options: { enableRepair?: boolean } = {}) {
     const { enableRepair = true } = options
     let candidate = buffer

     if (enableRepair) {
       try {
         candidate = jsonrepair(buffer)
       } catch (err) {
         // Best-effort repair failed; fall back to raw buffer
         candidate = buffer
       }
     }

     const parser = createParser()
     let root: any = null

     parser.onValue = function (value: any) {
       if (this.stack.length === 0) {
         root = value
       }
     }

     parser.write(candidate)

     if (root === null) {
       throw new Error('JSON root not completed yet')
     }

     return root
   }
   ```

4. **Structured Viewer Component** (`StreamStructuredView.tsx`)
   ```tsx
   import React from 'react'
   import Card from '../common/Card'
   import { useStreamParser } from '../../hooks/useStreamParser'
   import JSONTree from 'react-json-tree'

   const theme = {
     base00: '#FFFFFF', base01: '#F8F9FB', base02: '#DFE7EC', base03: '#9EB7C7',
     base04: '#5D87A1', base05: '#031C34', base06: '#031C34', base07: '#031C34',
     base08: '#AF2A47', base09: '#D4A03D', base0A: '#FEC74A', base0B: '#2FB66A',
     base0C: '#00B7F1', base0D: '#7592C1', base0E: '#B37AB5', base0F: '#E9853C',
   }

   export const StreamStructuredView: React.FC = () => {
     const { root, status, error } = useStreamParser()

     return (
       <Card title="结构化视图" subtitle={status === 'parsing' ? '解析中…' : undefined}>
         {status === 'error' && (
           <p className="text-xs text-supportive-orange mb-2">解析未完成: {error}</p>
         )}
         {status === 'valid' && root ? (
           <div className="stream-structured-wrapper">
             <JSONTree data={root} theme={theme} invertTheme={false} hideRoot={false} />
           </div>
         ) : (
           <p className="text-sm text-neutral-400">等待完整 JSON…</p>
         )}
       </Card>
     )
   }
   ```
   - Uses [`react-json-tree`](https://github.com/reduxjs/redux-devtools/tree/main/packages/react-json-tree) for a readable tree view (can be swapped for custom renderer)
   - Applies the same design tokens for consistent styling
   - Shows parser state (parsing/valid/error)

5. **Integrate with StreamDisplay**
   - Add tabs or side-by-side layout to toggle between "Raw" and "Structured"
   - `StreamDisplay` can accept `children` or a `secondaryView` prop to render `StreamStructuredView`
   - Example integration:
     ```tsx
     <StreamDisplay
       content={streamState.content}
       phase={researchAgentStatus.phase}
       isStreaming={streamState.isStreaming}
       subtitle={researchAgentStatus.currentAction}
       secondaryView={<StreamStructuredView />}
       viewMode="split"  // raw + structured side-by-side
     />
     ```
   - Update design tokens to include layout rules for split view (`stream-view-tabs`, `stream-view-split`)

6. **Schema-Aware Enhancements (Phase-specific)**
   - Optional: Provide JSON schema per phase (e.g., `phase1_discover_output_schema.json` already exists)
   - Validate parsed JSON against schema using [`ajv`](https://ajv.js.org/)
   - Highlight schema violations in UI (e.g., display warnings next to fields)
   - `StreamStructuredView` can accept a `schema` prop to show validation state per node

7. **Handling Non-JSON Streams**
   - Detect if buffer appears to be JSON (starts with `{` or `[` and has matching tokens)
   - If not JSON, fall back to raw-only view with a message "当前响应不是 JSON 格式"
   - Provide toggle for users to disable parsing (e.g., `enableRepair` switch)

8. **Performance Considerations**
   - Debounce parsing to avoid re-running on every single token: e.g., parse every 250ms while streaming
   - Use Web Worker for parsing large responses to keep UI responsive
   - Release parser state when stream completes to avoid memory leaks

9. **Testing Strategy**
   - Unit tests for `incrementalParseJSON` with partial JSON fragments
   - UI tests to ensure structured view updates as JSON becomes valid
   - Schema validation tests per phase
   - Stress tests with large JSON payloads and malformed JSON

**Deliverables for Step 6**:
- `useStreamParser` hook
- `jsonIncrementalParser.ts` utility (with repair + event hooks)
- `StreamStructuredView` component
- Updated `StreamDisplay` supporting raw/structured views (tabs or split)
- Optional `PhaseStreamStructuredView` wrappers with schema validation

---

## Implementation Order

### Phase 1: Backend Token Streaming (High Priority)
1. ✅ Fix `BasePhase._stream_with_callback()` to stream tokens
2. ✅ Fix Phase 0 Summarization to stream tokens (pass `ui` to `ContentSummarizer`)

### Phase 2: Frontend Design System (High Priority)
3. ✅ Create `StreamDisplay` component with consistent styling
4. ✅ Create design tokens file (`streamDesignTokens.ts`)
5. ✅ Extend Tailwind config with stream utilities
6. ✅ Create `useStreamState` hook for state management
7. ✅ Update `ResearchAgentPage` to use `StreamDisplay`

### Phase 3: Design System Completion (Medium Priority)
8. ✅ Create `PhaseStreamDisplay` wrapper for phase-specific context
9. ✅ Add usage guidelines and examples
10. ✅ Test consistent styling across all phases

### Phase 4: Verification (Medium Priority)
11. ✅ Verify Phase 0.5 streams tokens (should work after Phase 1 fix)
12. ✅ Verify Phase 1 streams tokens (should work after Phase 1 fix)
13. ✅ Verify Phase 2 streams tokens (should work after Phase 1 fix)
14. ✅ Verify Phase 3 streams tokens (should work after Phase 1 fix)
15. ✅ Verify Phase 4 streams tokens (should work after Phase 1 fix)

### Phase 5: Enhancements (Low Priority)
16. ⏳ Add stream start/end indicators with phase context
17. ⏳ Add visual indicators for active streaming (already in design system)
18. ⏳ Add copy to clipboard functionality (already in design system)
19. ⏳ Add collapsible/expandable stream box (already in design system)

### Phase 6: Real-time JSON Parsing & Structured View (Planned)
20. ⏳ Implement `useStreamParser` hook and incremental parser utility
21. ⏳ Create `StreamStructuredView` component and integrate with `StreamDisplay`
22. ⏳ Add optional schema validation per phase
23. ⏳ Add user controls (raw/structured toggle, repair toggle)
24. ⏳ Performance tuning (debounce, Web Worker)
25. ⏳ Update tests for structured parsing and schema validation
26. ⏳ Final UX review for raw + structured dual display

---

## Testing Plan

### Unit Tests
1. Test `_stream_with_callback()` calls `ui.display_stream()` for each token
2. Test `ContentSummarizer` streams tokens when `ui` is provided
3. Test frontend receives and displays tokens correctly

### Integration Tests
1. Test Phase 0 summarization shows tokens in real-time
2. Test all phases (0.5, 1, 2, 3, 4) show tokens in real-time
3. Test multiple concurrent streams don't interfere

### User Experience Tests
1. Verify tokens appear smoothly without lag
2. Verify auto-scroll works correctly
3. Verify stream box is readable and not overwhelming

---

## Expected Impact

### User Experience
- **Before**: Users see "正在接收响应... (190 tokens)" - no idea what's being generated
- **After**: Users see actual tokens streaming in real-time, giving confidence that AI is working

### Confidence Building
- Users can see AI generating responses step by step
- Users can see when AI is stuck or making progress
- Users can see the quality of responses as they're generated

### Debugging
- Developers can see exactly what AI is generating
- Easier to identify issues with prompts or parsing
- Better understanding of API behavior

---

## Notes

1. **Performance**: Streaming tokens shouldn't significantly impact performance. WebSocket messages are lightweight.

2. **Rate Limiting**: Current implementation already batches progress updates (every 10 tokens or 2 seconds). Token streaming can be more frequent since it's just appending to a buffer.

3. **Memory**: Stream buffer is cleared at the start of each new stream, so memory usage should be bounded.

4. **Backward Compatibility**: Existing progress messages are kept, so if streaming fails, users still see progress updates.

5. **API Support**: All phases use `QwenStreamingClient` which supports streaming. Phase 0 uses the same client, so streaming should work there too.

---

## WebSocket Message Flow

### Current Flow (Broken)
```
Backend: Receives tokens → Updates progress tracker → Sends progress message (every 10 tokens)
Frontend: Receives progress message → Updates "正在接收响应... (190 tokens)"
Result: No actual token content shown
```

### New Flow (Fixed)
```
Backend: Receives tokens → Updates progress tracker → Sends token via display_stream() → Sends progress message (periodic)
Frontend: Receives token → Appends to streamBuffer → Displays in stream box → Auto-scrolls
Result: Users see actual tokens streaming in real-time
```

---

## Summary

**Root Cause**: The token callback in `_stream_with_callback()` receives tokens but never calls `ui.display_stream()` to send them to the frontend.

**Solution**: 
1. Add `self.ui.display_stream(token)` call in the callback
2. Pass `ui` object to `ContentSummarizer` and stream tokens there too
3. Enhance frontend display with auto-scroll and better styling

**Impact**: Users will see all AI responses streaming in real-time across all phases, giving them confidence that the system is working and showing exactly what's being generated.

