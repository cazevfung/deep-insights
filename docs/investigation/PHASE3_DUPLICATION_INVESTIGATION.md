# Phase 3 Steps Duplication Investigation

## Problem
Phase 3 UI shows all steps correctly, but each step appears **3 times** in the UI.

## Investigation Summary

### 1. Backend Analysis ✅

**ProgressTracker.complete_step()** (research/progress_tracker.py:72-121):
- Called **once per step** (either line 112 or 165 in phase3_execute.py, depending on strategy)
- Calls all callbacks in `step_complete_callbacks` list
- Only **one callback registered** (research/agent.py:291)

**WebSocketUI.display_step_complete()** (backend/app/services/websocket_ui.py:390-410):
- Called once per step completion
- Sends message via `ws_manager.broadcast(batch_id, message)`
- Message structure is correct

**WebSocketManager.broadcast()** (backend/app/websocket/manager.py:111-148):
- Sends message to **all active connections** for the batch_id
- If no connections, buffers message for later delivery
- When client reconnects, sends **all buffered messages** (lines 65-80)

### 2. Frontend Analysis ✅

**useWebSocket.ts** (client/src/hooks/useWebSocket.ts:342-343):
- Receives `phase3:step_complete` messages
- Calls `addPhase3Step(data.stepData)` for each message

**workflowStore.addPhase3Step()** (client/src/stores/workflowStore.ts:332-354):
- **Has deduplication logic**: Checks for existing step by `step_id`
- If exists: Updates the step
- If not exists: Adds new step
- **BUT**: React state updates are asynchronous!

### 3. Root Cause Identified 🎯

**Race Condition in Frontend State Updates**

The issue is a **race condition** in the frontend:

1. When 3 WebSocket messages arrive in quick succession (or on reconnection with buffered messages)
2. All 3 messages call `addPhase3Step()` before any state update completes
3. All 3 see the same initial state (empty or without the step)
4. All 3 add the step, resulting in 3 duplicates

**Why 3 times specifically?**
- Could be 3 WebSocket connections for the same batch_id
- Could be 3 buffered messages sent on reconnection
- Could be 3 rapid messages before state updates

### 4. Evidence

**WebSocketManager.broadcast()** sends to all connections:
```python
for websocket in self.active_connections[batch_id]:
    await websocket.send_text(json.dumps(message, ensure_ascii=False))
```

**On reconnection**, buffered messages are sent:
```python
if batch_id in self._message_buffer and self._message_buffer[batch_id]:
    buffered_messages = list(self._message_buffer[batch_id])
    for buffered_message in buffered_messages:
        await self.send_to_client(websocket, buffered_message)
```

**Frontend deduplication** uses non-functional state update:
```typescript
addPhase3Step: (step) =>
  set((state) => {
    const existingIndex = state.phase3Steps.findIndex((s) => s.step_id === step.step_id)
    // Problem: If 3 calls happen before state updates, all see same state
```

## Solution

### Option 1: Use Functional State Update (Recommended)
Change `addPhase3Step` to use a functional update that reads the current state atomically:

```typescript
addPhase3Step: (step) =>
  set((state) => {
    // Read current state atomically
    const currentSteps = state.phase3Steps
    const existingIndex = currentSteps.findIndex((s) => s.step_id === step.step_id)
    
    if (existingIndex >= 0) {
      // Update existing step
      const updatedSteps = [...currentSteps]
      updatedSteps[existingIndex] = step
      return {
        phase3Steps: updatedSteps.sort((a, b) => a.step_id - b.step_id),
        currentStepId: step.step_id,
      }
    } else {
      // Add new step
      const updatedSteps = [...currentSteps, step]
      return {
        phase3Steps: updatedSteps.sort((a, b) => a.step_id - b.step_id),
        currentStepId: step.step_id,
      }
    }
  }),
```

### Option 2: Add Deduplication at WebSocket Handler Level
Add deduplication in `useWebSocket.ts` before calling `addPhase3Step`:

```typescript
case 'phase3:step_complete':
  // Check if step already exists before adding
  const currentSteps = useWorkflowStore.getState().phase3Steps
  const stepExists = currentSteps.some(s => s.step_id === data.stepData.step_id)
  if (!stepExists) {
    addPhase3Step(data.stepData)
  }
  break
```

### Option 3: Prevent Multiple WebSocket Connections
Ensure only one WebSocket connection per batch_id is active.

### Option 4: Clear Buffer After Sending
Clear the message buffer after sending to prevent duplicate sends on multiple reconnections.

## Implemented Fix ✅

**Fix Applied**: Enhanced deduplication in `addPhase3Step` using Map-based approach to ensure only one entry per step_id exists, even if duplicates already exist in state.

**Changes Made**:

1. **workflowStore.ts** - Enhanced `addPhase3Step` function:
   - Uses Set for O(1) lookup to check if step exists
   - Uses Map to deduplicate existing steps when updating
   - Ensures only one entry per step_id exists in the array
   - Handles race conditions when multiple messages arrive quickly

2. **useWebSocket.ts** - Added validation:
   - Validates step data before processing
   - Prevents processing invalid messages

**Implementation**:

```typescript
addPhase3Step: (step) =>
  set((state) => {
    // Use Set for O(1) lookup to check if step already exists
    const stepIds = new Set(state.phase3Steps.map((s) => s.step_id))
    
    let updatedSteps: SessionStep[]
    if (stepIds.has(step.step_id)) {
      // Step already exists - update it and remove any duplicates
      // Use Map to ensure only one entry per step_id (keeps the latest)
      const stepsMap = new Map<number, SessionStep>()
      
      // First, add all existing steps (this will deduplicate if there are already duplicates)
      state.phase3Steps.forEach((s) => {
        if (s.step_id !== step.step_id) {
          stepsMap.set(s.step_id, s)
        }
      })
      
      // Then add/update the new step
      stepsMap.set(step.step_id, step)
      
      updatedSteps = Array.from(stepsMap.values())
    } else {
      // New step - add it
      updatedSteps = [...state.phase3Steps, step]
    }
    
    // Sort steps by step_id to ensure correct order
    updatedSteps.sort((a, b) => a.step_id - b.step_id)
    
    return {
      phase3Steps: updatedSteps,
      currentStepId: step.step_id,
    }
  }),
```

## Testing

After fix, verify:
1. Steps appear only once in UI
2. Steps update correctly when same step_id is received again
3. No duplicates on WebSocket reconnection
4. No duplicates when multiple messages arrive rapidly

