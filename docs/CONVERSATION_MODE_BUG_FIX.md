# Conversation Mode vs Prompt Mode Bug Fix

## The Issue You Identified

**EXCELLENT CATCH!** The "send messages at any time" feature (conversation mode) was conflicting with prompt responses!

## Root Cause

The component has **two modes** for sending messages:

### 1. **Prompt Mode** (Procedural Prompt Response)
- Used when AI is waiting for specific user input
- Sends via **WebSocket** with `prompt_id`
- Message type: `research:user_input`
- Backend receives and processes as prompt response

### 2. **Conversation Mode** (Feedback/Chat)
- Used when user sends messages at any time
- Sends via **HTTP API** (not WebSocket)
- No `prompt_id` included
- Backend queues as conversation message

## The Bug

The logic to determine which mode to use was **inconsistent**:

### For UI Rendering:
```typescript
const hasProceduralPrompt =
  waitingForUser && 
  typeof promptId === 'string' && 
  promptId.trim().length > 0 && 
  !promptSubmitted  // ✅ Checks if already submitted
```

### For Message Handling (BEFORE FIX):
```typescript
const isPromptMode = 
  waitingForUser && 
  typeof promptId === 'string' && 
  promptId.trim().length > 0
  // ❌ Missing: && !promptSubmitted
```

### The Problem Flow

1. **Prompt arrives** → `hasProceduralPrompt = true` → Amber box shows
2. **User types and presses Enter**
3. **Handler calculates `isPromptMode`**
4. **If `isPromptMode = false`** (due to missing check):
   - ❌ Goes to `handleConversationSend()`
   - ❌ Sends via HTTP API (not WebSocket)
   - ❌ No `prompt_id` included
   - ❌ **Backend doesn't recognize it as prompt response**
5. **Backend keeps waiting** → Re-sends the same prompt
6. **User sees duplicate prompts** (3x in your logs!)

## The Fix

Made `isPromptMode` **consistent** with `hasProceduralPrompt`:

```typescript
// NOW BOTH USE THE SAME LOGIC:
const isPromptMode = 
  waitingForUser && 
  typeof promptId === 'string' && 
  promptId.trim().length > 0 && 
  !promptSubmitted  // ✅ Added consistency check
```

Also added dependencies to useCallback:
```typescript
// Added promptSubmitted to dependency array
}, [
  addNotification,
  batchId,
  draft,
  handleConversationSend,
  onSendMessage,
  promptId,
  promptSubmitted,  // ✅ Added
  waitingForUser,
])
```

## Enhanced Debugging

Added clear indicators to show which path is taken:

### Prompt Mode (WebSocket):
```
🔵 handleSendDraft called
🔵 isPromptMode: true (must match hasProceduralPrompt)
🔵 Attempting to send user input
✅ WebSocket message sent successfully: type=research:user_input
```

### Conversation Mode (HTTP API):
```
🔵 handleSendDraft called  
🔵 isPromptMode: false (must match hasProceduralPrompt)
🔵 Not in prompt mode, checking for conversation mode
🟣 handleConversationSend called (CONVERSATION MODE - not prompt response!)
🟣 Sending via HTTP API (not WebSocket prompt response)
🟣 Conversation message sent via API
```

## How to Test

1. **Refresh browser** to load the fix
2. **Wait for prompt** (like "在生成研究角色前...")
3. **Check console** for state:
   ```
   🔍 PhaseInteractionPanel state: {
     waitingForUser: true,
     promptId: "...",
     promptSubmitted: false,
     hasProceduralPrompt: true
   }
   ```
4. **Type and press Enter**
5. **You should see BLUE logs** (🔵), **NOT PURPLE logs** (🟣):
   ```
   🔵 handleSendDraft called
   🔵 isPromptMode: true
   🔵 Attempting to send user input
   ✅ WebSocket message sent successfully
   ```

### What to Look For

**✅ GOOD (Prompt Mode - Correct):**
- Blue 🔵 logs
- "Attempting to send user input"
- "WebSocket message sent successfully"
- No duplicate prompts from backend

**❌ BAD (Conversation Mode - Wrong):**
- Purple 🟣 logs
- "CONVERSATION MODE - not prompt response!"
- "Sending via HTTP API"
- Backend keeps re-sending prompt (duplicates)

## Why This Happens

The "send messages at any time" feature made it possible for the handler to:
1. Check if there's an active prompt → Send as prompt response
2. Otherwise → Send as conversation message

But due to the inconsistent condition check, it could incorrectly go to conversation mode even when there's an active prompt, especially if:
- State updates haven't propagated
- Re-renders caused timing issues  
- `promptSubmitted` flag was set prematurely

## Result

Now the mode determination is **consistent** between:
- ✅ UI rendering (`hasProceduralPrompt`)
- ✅ Message handling (`isPromptMode`)
- ✅ Both check the same conditions
- ✅ No ambiguity about which path to take

This ensures that when there's an active prompt, the response ALWAYS goes through WebSocket with the correct `prompt_id`, and the backend can properly process it.

