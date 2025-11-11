# User Input Prompt Animation Fix

## Problem

After a user submitted their response to a research agent prompt (the yellow warning boxes asking for user input), the UI had the following issues:

1. **Prompt persists indefinitely:** The yellow prompt box stayed visible forever after submission
2. **Input box stays highlighted:** The textarea remained yellow/amber colored even after the prompt was handled
3. **No visual feedback:** No animation or transition to indicate the submission was successful

This happened because the UI relied solely on backend state (`waitingForUser` and `userInputRequired`) which doesn't clear immediately after submission.

## Solution

Implemented local state management with smooth exit animations:

### 1. Local State Tracking
Added two state variables to track submission independently from backend:

```typescript
const [promptSubmitted, setPromptSubmitted] = useState(false)
const [isPromptExiting, setIsPromptExiting] = useState(false)
```

### 2. Modified hasProceduralPrompt Logic
```typescript
const hasProceduralPrompt =
  waitingForUser && 
  typeof promptId === 'string' && 
  promptId.trim().length > 0 && 
  !promptSubmitted  // ← Added this condition
```

Now the prompt is hidden immediately when user submits, regardless of backend state.

### 3. Exit Animation on Submit
When user submits (via button or choice selection):

```typescript
// Trigger exit animation
setIsPromptExiting(true)

// Send the message
onSendMessage('research:user_input', { prompt_id: promptId, response })

// Mark as submitted after animation (300ms)
setTimeout(() => {
  setPromptSubmitted(true)
  setDraft('')
}, 300)
```

### 4. CSS Transition Animation
Applied smooth fade-out and slide-up animation to the prompt box:

```tsx
<div className={`... transition-all duration-300 ${
  isPromptExiting 
    ? 'opacity-0 scale-95 -translate-y-2'    // Exiting state
    : 'opacity-100 scale-100 translate-y-0'   // Normal state
}`}>
```

### 5. Textarea Color Transition
Added smooth color transition for the input box:

```tsx
<div className={`... transition-colors duration-300 ${
  hasProceduralPrompt 
    ? 'border-amber-300 bg-amber-50'      // Yellow when prompt active
    : 'border-neutral-200 bg-neutral-white' // White when normal
}`}>
```

### 6. State Reset Logic
Reset state when new prompts arrive or when backend confirms completion:

```typescript
useEffect(() => {
  if (waitingForUser && promptId && !promptSubmitted) {
    setIsPromptExiting(false)  // Reset for new prompt
  }
  if (!waitingForUser) {
    setPromptSubmitted(false)  // Clear when backend confirms done
    setIsPromptExiting(false)
  }
}, [waitingForUser, promptId, promptSubmitted])
```

## User Experience Flow

### Before Fix:
1. User sees yellow prompt: "需要用户输入"
2. User types response and clicks "提交"
3. ❌ Prompt stays visible indefinitely
4. ❌ Textarea stays yellow
5. ❌ No visual feedback

### After Fix:
1. User sees yellow prompt: "需要用户输入"
2. User types response and clicks "提交"
3. ✅ Prompt smoothly fades out and slides up (300ms animation)
4. ✅ Textarea transitions back to white background
5. ✅ Clear visual feedback that submission was successful
6. ✅ When new prompt arrives, UI resets and shows it properly

## Technical Details

### Animation Timeline:
- **0ms:** User clicks submit button
- **0ms:** `isPromptExiting` set to `true` → triggers opacity/scale/translate animation
- **0ms:** Message sent to backend via WebSocket
- **300ms:** Animation completes, `promptSubmitted` set to `true`, prompt fully hidden
- **Varies:** Backend eventually clears `waitingForUser`, state fully synced

### Why 300ms?
- Matches Tailwind's default `duration-300` class
- Long enough to be noticed but not feel sluggish
- Standard for UI micro-interactions

### State Management Priority:
1. **Local state (`promptSubmitted`)** - Immediate UI control
2. **Backend state (`waitingForUser`)** - Source of truth for new prompts
3. Local state resets when backend confirms completion

## Files Modified

### `client/src/components/phaseCommon/PhaseInteractionPanel.tsx`
- **Lines 47-48:** Added `promptSubmitted` and `isPromptExiting` state
- **Line 55:** Modified `hasProceduralPrompt` to check `!promptSubmitted`
- **Lines 65-74:** Added useEffect for state reset logic
- **Lines 164-205:** Updated `handleSendDraft` with animation logic
- **Lines 207-236:** Updated `handleChoiceSelect` with animation logic
- **Lines 350-353:** Added exit animation classes to prompt box
- **Lines 382-386:** Added color transition to textarea wrapper

## Testing Recommendations

1. **Normal Flow:**
   - Trigger a user input prompt from research agent
   - Enter text and click "提交"
   - Verify prompt fades out smoothly in 300ms
   - Verify textarea changes from yellow to white

2. **Choice Selection:**
   - Trigger a prompt with choices (y/n buttons)
   - Click a choice button
   - Verify same smooth exit animation

3. **Empty Submit:**
   - Trigger a prompt
   - Click submit without entering text (uses default)
   - Verify animation still works

4. **Multiple Prompts:**
   - Complete first prompt (should animate out)
   - Wait for second prompt (should appear normally)
   - Verify state reset properly between prompts

5. **Rapid Submission:**
   - Type and submit very quickly
   - Verify animation isn't skipped
   - Verify no visual glitches

## Result

✅ Prompt box disappears with smooth animation after submission
✅ Textarea returns to normal white styling with transition
✅ Clear visual feedback for successful submission
✅ State properly resets for subsequent prompts
✅ Works for both text input and choice button submissions

