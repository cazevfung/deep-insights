# Debugging User Input Issue - Diagnostic Guide

## Current Status
The user input prompt is being received but the response is not being sent to the backend.

## Added Debugging

I've added extensive console logging to trace exactly what's happening when you try to submit input:

### What to Check in Console

When you receive the prompt and try to submit (either by pressing Enter or clicking the button), look for these logs:

#### 1. **Component State** (logs automatically every time state changes)
```
🔍 PhaseInteractionPanel state: {
  waitingForUser: true/false,
  promptId: "...",
  promptSubmitted: true/false,
  hasProceduralPrompt: true/false,
  userInputRequired: { ... }
}
```

**What to check:**
- ✅ `waitingForUser` should be `true`
- ✅ `promptId` should have a value like `"20251110_100512_1_1762769785.323085"`
- ✅ `promptSubmitted` should be `false`
- ✅ `hasProceduralPrompt` should be `true`

#### 2. **When You Press Enter**
```
🔵 Enter key pressed (without Shift)
```

**If this doesn't appear:** The Enter key event isn't being captured

#### 3. **When You Click Submit Button**
```
🔵 Submit button clicked {
  hasProceduralPrompt: true,
  promptId: "...",
  isDisabled: false
}
```

**If this doesn't appear:** The button click isn't being registered (might be disabled)

**What to check:**
- ✅ `isDisabled` should be `false`
- ✅ `promptId` should have a value

#### 4. **When handleSendDraft is Called**
```
🔵 handleSendDraft called {
  waitingForUser: true,
  promptId: "...",
  draft: "...",
  batchId: "..."
}
```

**If this doesn't appear:** The handler isn't being called at all

#### 5. **Prompt Mode Check**
```
🔵 isPromptMode: true
```

**If this shows `false`:** The component doesn't think it's in prompt mode

#### 6. **Sending Message**
```
🔵 Attempting to send user input: {
  promptId: "...",
  response: "...",
  messageType: "research:user_input"
}
```

**If this doesn't appear:** Code exited before reaching send

#### 7. **WebSocket Send Attempt**
```
✅ WebSocket message sent successfully: type=research:user_input
```
OR
```
❌ WebSocket is not connected. State: CLOSED
```

**This tells us if the message was actually sent**

#### 8. **Final Result**
```
🔵 Message send result: ✅ SUCCESS
```
OR
```
🔵 Message send result: ❌ FAILED
```

## Diagnostic Scenarios

### Scenario A: No Console Logs at All
**Problem:** Event handlers aren't firing
**Possible Causes:**
1. Button is disabled
2. Textarea is disabled
3. Event listeners not attached
4. Component not rendering

**Check:**
- Inspect the button/textarea in DevTools
- Check if `disabled` attribute is present
- Look at the component state log

### Scenario B: Button Click Logged, But No handleSendDraft
**Problem:** Handler not being called despite button click
**Possible Causes:**
1. React synthetic event issue
2. Event propagation stopped somewhere
3. Handler reference lost

### Scenario C: handleSendDraft Called, But Exits Early
**Problem:** One of the early return conditions is triggered
**Check the logs for:**
- `🔵 Not in prompt mode` - means `isPromptMode === false`
- `❌ No promptId available` - means `promptId` is falsy

### Scenario D: Message Send Attempted, But Failed
**Problem:** WebSocket is not in OPEN state
**Check:**
- `❌ WebSocket is not connected. State: CLOSED/CONNECTING/CLOSING`
- WebSocket might have disconnected

### Scenario E: Message Sent Successfully, But Backend Doesn't Respond
**Problem:** Backend issue or prompt_id mismatch
**Check backend logs for:**
- If message was received
- If prompt_id matches what backend expects

## Testing Steps

1. **Start fresh research workflow**
2. **Wait for the prompt to appear**
3. **Check console for state log:**
   ```
   🔍 PhaseInteractionPanel state: { ... }
   ```
4. **Type something (or leave empty) and press Enter**
5. **Check console for ALL the logs above in sequence**
6. **Copy all console logs and send them**

## What I Need From You

Please do the following:

1. Open browser DevTools (F12)
2. Go to Console tab
3. Clear the console
4. Wait for the user input prompt to appear
5. Try to submit (either by pressing Enter or clicking button)
6. **Copy ALL console logs** (especially the blue 🔵 and red ❌ ones)
7. Send me the logs

This will tell us exactly where the flow is breaking.

## Expected Working Flow

```
🔍 PhaseInteractionPanel state: { waitingForUser: true, promptId: "...", hasProceduralPrompt: true }
↓
🔵 Enter key pressed (without Shift)
↓
🔵 Submit button clicked { hasProceduralPrompt: true, promptId: "...", isDisabled: false }
↓
🔵 handleSendDraft called { waitingForUser: true, promptId: "...", ... }
↓
🔵 isPromptMode: true
↓
🔵 Attempting to send user input: { promptId: "...", response: "...", ... }
↓
✅ WebSocket message sent successfully: type=research:user_input
↓
🔵 Message send result: ✅ SUCCESS
↓
✅ Message sent successfully, updating UI
```

If any step in this flow is missing, that's where the problem is!

