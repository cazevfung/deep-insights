# User Input Scenarios - Complete Analysis

## Overview
This document catalogs all user input prompts in the research workflow and confirms they all work with the recent bug fix.

## All User Input Prompts

### 1. Pre-Role Feedback (Phase 0.5)
**Location:** `research/agent.py:206-208`
```python
pre_role_feedback = self.ui.prompt_user(
    "在生成研究角色前，你想强调哪些研究重点或背景？(可选，留空表示无额外指导)"
)
```
- **Type:** Free text input
- **Choices:** None
- **Optional:** Yes (user can leave empty)
- **Fix Applied:** ✅ Yes

### 2. Post-Phase1 Feedback (Phase 1 Amendment)
**Location:** `research/agent.py:262`
```python
post_phase1_feedback = self.ui.prompt_user(
    "你想如何修改这些目标？(自由输入，留空表示批准并继续)"
)
```
- **Type:** Free text input
- **Choices:** None
- **Optional:** Yes (user can leave empty)
- **Fix Applied:** ✅ Yes

### 3. Goal Amendment Confirmation (Phase 1)
**Location:** `research/agent.py:273`
```python
proceed = self.ui.prompt_user(
    "是否采用这些修订后的目标并继续？(y/n)", 
    ["y", "n"]
)
```
- **Type:** Multiple choice
- **Choices:** ["y", "n"]
- **Optional:** No (requires selection)
- **Fix Applied:** ✅ Yes

### 4. Plan Execution Confirmation (Phase 3)
**Location:** `research/agent.py:365`
```python
confirm = self.ui.prompt_user(
    "是否继续执行计划? (y/n)", 
    ["y", "n"]
)
```
- **Type:** Multiple choice
- **Choices:** ["y", "n"]
- **Optional:** No (requires selection)
- **Fix Applied:** ✅ Yes

## Backend Implementation

### WebSocketUI.prompt_user()
**File:** `backend/app/services/websocket_ui.py:326-371`

**Flow:**
1. Generates unique `prompt_id`
2. Creates response queue
3. Broadcasts via WebSocket: `research:user_input_required`
4. **Waits indefinitely** for user response (no timeout)
5. Returns response or empty string

**Message Format:**
```python
{
    "type": "research:user_input_required",
    "prompt": str,           # The prompt text
    "choices": list | None,  # ["y", "n"] or None for free text
    "prompt_id": str         # Unique identifier
}
```

## Frontend Implementation

### useWebSocket Hook
**File:** `client/src/hooks/useWebSocket.ts:500-512`

Handles `research:user_input_required` messages and updates state:
```typescript
updateResearchAgentStatus({
    waitingForUser: true,
    userInputRequired: {
        type: data.type,
        prompt_id: data.prompt_id,
        data: {
            prompt: data.prompt,
            choices: data.choices,
        },
    },
})
```

### PhaseInteractionPanel Component
**File:** `client/src/components/phaseCommon/PhaseInteractionPanel.tsx`

**Rendering Logic:**
- Shows amber warning box when `hasProceduralPrompt === true`
- Displays choice buttons if `choiceOptions.length > 0`
- Shows textarea for free text input (works for all scenarios)

**Submit Logic (FIXED):**
1. ✅ Calls `onSendMessage()` and checks return value
2. ✅ Only updates UI if message sent successfully
3. ✅ Shows error notification if send fails
4. ✅ Keeps prompt visible on failure for retry

## Bug Fix Summary

### What Was Fixed
The original issue was that the WebSocket message could fail to send, but the UI would update anyway, causing:
- Backend never received the response
- Backend re-sent the same prompt (seen as duplicates)
- User couldn't respond because UI hid the prompt

### How It Was Fixed

#### 1. Enhanced sendMessage() Return Value
**File:** `client/src/hooks/useWebSocket.ts:703-723`
```typescript
const sendMessage = (type: string, data: any): boolean => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
        try {
            wsRef.current.send(JSON.stringify({ type, ...data }))
            console.log(`✅ WebSocket message sent successfully`)
            return true  // ← Now returns success/failure
        } catch (error) {
            console.error(`❌ Failed to send message`)
            return false
        }
    } else {
        console.error(`❌ WebSocket not connected`)
        return false
    }
}
```

#### 2. Check Send Success Before UI Update
**File:** `client/src/components/phaseCommon/PhaseInteractionPanel.tsx:183-202`

**For Free Text Input (handleSendDraft):**
```typescript
const messageSent = onSendMessage('research:user_input', {
    prompt_id: promptId,
    response,
})

if (messageSent) {
    // Success - hide prompt with animation
    setIsPromptExiting(true)
    setTimeout(() => {
        setPromptSubmitted(true)
        setDraft('')
    }, 300)
} else {
    // Failure - show error, keep prompt visible
    addNotification('消息发送失败，请检查连接后重试', 'error')
}
```

**For Choice Selection (handleChoiceSelect):**
```typescript
const messageSent = onSendMessage('research:user_input', {
    prompt_id: promptId,
    response: choice,
})

if (messageSent) {
    // Success - hide prompt
    setIsPromptExiting(true)
    setTimeout(() => setPromptSubmitted(true), 300)
} else {
    // Failure - show error
    addNotification('消息发送失败，请检查连接后重试', 'error')
}
```

## Verification Checklist

- ✅ **Free text prompts** - Pre-role feedback, Post-phase1 feedback
- ✅ **Y/N choice prompts** - Goal confirmation, Plan confirmation
- ✅ **Message send verification** - Checks WebSocket state before sending
- ✅ **Error handling** - Shows notification on send failure
- ✅ **UI state management** - Only hides prompt on successful send
- ✅ **Console logging** - Clear success/failure indicators
- ✅ **No duplicate prompts** - Backend receives response, won't re-send

## Testing Instructions

### Test Scenario 1: Free Text Input
1. Start research workflow
2. Wait for "在生成研究角色前..." prompt
3. Type some text or leave empty
4. Press Enter or click Submit
5. **Expected:** 
   - Console shows `✅ WebSocket message sent successfully`
   - Prompt disappears with animation
   - Research continues

### Test Scenario 2: Y/N Choice
1. Continue past Phase 1
2. Provide feedback when prompted
3. Wait for "是否采用这些修订后的目标并继续？(y/n)" prompt
4. Click Y or N button
5. **Expected:**
   - Console shows `✅ WebSocket message sent successfully`
   - Prompt disappears
   - Research proceeds based on choice

### Test Scenario 3: Connection Failure
1. Disconnect network or stop backend during prompt
2. Try to submit response
3. **Expected:**
   - Console shows `❌ WebSocket not connected. State: CLOSED`
   - Error notification: "消息发送失败，请检查连接后重试"
   - Prompt stays visible for retry

### Test Scenario 4: Empty Response
1. Wait for any prompt
2. Leave input empty and submit
3. **Expected:**
   - Empty string sent successfully
   - Backend receives empty response
   - Research continues with default/empty value

## Conclusion

**All 4 user input scenarios are now fixed** with the same solution:
1. Message is sent FIRST
2. Success is verified BEFORE UI updates
3. Errors are handled gracefully
4. Users can retry on failure

The fix applies uniformly to:
- ✅ Free text inputs (with or without default values)
- ✅ Multiple choice selections (Y/N or other options)
- ✅ Optional inputs (can be left empty)
- ✅ Required inputs (must select an option)

