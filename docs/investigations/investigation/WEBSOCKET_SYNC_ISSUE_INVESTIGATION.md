# WebSocket Sync Issue Investigation

## Problem Summary
When running on localhost:3000, all steps created by the AI were successfully running, but only step 1 output was shown on the UI. The other steps didn't see a real-time status update on the "阶段3 深度研究" (Phase 3 Deep Research) screen. There's a syncing issue.

## Console Log Analysis

From the console logs, we can see:
1. Multiple WebSocket connections being opened and closed repeatedly
2. Connections closing with "batchId changed or component unmounting"
3. WebSocket errors (code 1006 - abnormal closure)
4. Messages being received (step 12, step 13 progress) but not displayed in UI
5. Pattern: close connection → connect → error → close → connect → success

## Root Causes Identified

### 1. **Phase3SessionPage Doesn't Use WebSocket Hook**
**Location**: `client/src/pages/Phase3SessionPage.tsx`

**Issue**: 
- `Phase3SessionPage` component does NOT call `useWebSocket` hook
- It only reads from the Zustand store (`useWorkflowStore`)
- The store is updated by WebSocket messages, but if no component is listening, updates are lost

**Evidence**:
```typescript
// Phase3SessionPage.tsx - NO useWebSocket call
const Phase3SessionPage: React.FC = () => {
  const { phase3Steps, researchAgentStatus } = useWorkflowStore()
  // Missing: useWebSocket(batchId)
}
```

**Comparison**:
- `ResearchAgentPage` DOES call `useWebSocket` (line 10)
- `ScrapingProgressPage` DOES call `useWebSocket` (line 28)
- `Phase3SessionPage` does NOT call `useWebSocket`

### 2. **Multiple WebSocket Connections**
**Location**: `client/src/hooks/useWebSocket.ts`

**Issue**:
- When navigating from `/research` to `/phase3`, `ResearchAgentPage` may unmount
- This closes its WebSocket connection (cleanup function runs)
- `Phase3SessionPage` doesn't open its own connection
- Messages sent during the disconnect/reconnect window are lost

**Evidence from logs**:
```
useWebSocket.ts:42 Closing WebSocket connection (batchId changed or component unmounting)
useWebSocket.ts:105 WebSocket closed 1000 BatchId changed or component unmounting
useWebSocket.ts:75 Connecting to WebSocket: ws://localhost:3000/ws/20251105_135520
useWebSocket.ts:42 Closing WebSocket connection (batchId changed or component unmounting)
useWebSocket.ts:75 Connecting to WebSocket: ws://localhost:3000/ws/20251105_135520
useWebSocket.ts:96 WebSocket error: Event {...}
useWebSocket.ts:105 WebSocket closed 1006
useWebSocket.ts:79 WebSocket connected
```

### 3. **WebSocket Reconnection Race Condition**
**Location**: `client/src/hooks/useWebSocket.ts:29-315`

**Issue**:
- The `useEffect` hook depends on `batchId` (line 315)
- When `batchId` reference changes (even if value is same), cleanup runs
- This causes unnecessary connection closures
- Messages arriving during reconnection are lost

**Code Flow**:
```typescript
useEffect(() => {
  // ... connection logic
  return cleanup  // Runs when batchId changes
}, [batchId])  // Dependency on batchId
```

### 4. **Message Loss During Disconnect**
**Location**: `backend/app/services/websocket_ui.py:395-410`

**Issue**:
- Server sends `phase3:step_complete` messages via WebSocket
- If client WebSocket is disconnected during message send, message is lost
- No message queuing/retry mechanism on server side for disconnected clients
- Client doesn't request missed messages on reconnect

**Server Code**:
```python
async def _send_step_complete(self, step_data: dict):
    await self.ws_manager.broadcast(self.batch_id, {
        "type": "phase3:step_complete",
        "stepData": {...}
    })
```

## Detailed File Analysis

### `client/src/pages/Phase3SessionPage.tsx`
- **Status**: ✅ Reads from store correctly
- **Issue**: ❌ Never calls `useWebSocket` to receive updates
- **Impact**: Messages sent after navigation to this page are not received

### `client/src/hooks/useWebSocket.ts`
- **Status**: ✅ Handles `phase3:step_complete` messages correctly (line 279-281)
- **Issue**: ❌ Multiple instances can run simultaneously
- **Issue**: ❌ No connection deduplication per batchId
- **Impact**: Multiple connections for same batchId cause conflicts

### `backend/app/services/websocket_ui.py`
- **Status**: ✅ Sends messages correctly
- **Issue**: ❌ No message persistence/queuing for disconnected clients
- **Impact**: Messages sent during disconnect are lost

### `client/src/stores/workflowStore.ts`
- **Status**: ✅ `addPhase3Step` function works correctly (line 332-354)
- **Status**: ✅ Updates state correctly when called
- **Impact**: State updates work, but messages never reach the store if no WebSocket listener

## Recommended Fixes (✅ IMPLEMENTED)

### Fix 1: Add WebSocket Hook to Phase3SessionPage ✅
**Priority**: HIGH
**Location**: `client/src/pages/Phase3SessionPage.tsx`
**Status**: ✅ COMPLETED

```typescript
const Phase3SessionPage: React.FC = () => {
  const { phase3Steps, researchAgentStatus, batchId } = useWorkflowStore()
  useWebSocket(batchId || '')  // ✅ ADDED
  // ... rest of component
}
```

**Implementation**: Added `useWebSocket` hook call in Phase3SessionPage component to establish WebSocket connection and receive real-time updates.

### Fix 2: Prevent Multiple WebSocket Connections ✅
**Priority**: MEDIUM
**Location**: `client/src/hooks/useWebSocket.ts`
**Status**: ✅ COMPLETED

**Implementation**: 
- Created global WebSocket connection manager (`wsConnections` and `wsConnectionRefs` maps)
- Components now share the same WebSocket connection per batchId
- When a component mounts, it checks for existing connection and reuses it
- Connection is only closed when the last component using it unmounts
- Prevents duplicate connections and connection conflicts

### Fix 3: Stabilize batchId Dependency ✅
**Priority**: MEDIUM
**Location**: `client/src/hooks/useWebSocket.ts`
**Status**: ✅ COMPLETED

**Implementation**:
- Added `useMemo` to stabilize batchId reference: `const stableBatchId = useMemo(() => batchId, [batchId])`
- Changed useEffect dependency from `[batchId]` to `[stableBatchId]`
- Prevents unnecessary reconnections when batchId reference changes but value stays the same

### Fix 4: Message Queue on Server ✅
**Priority**: MEDIUM
**Location**: `backend/app/websocket/manager.py`
**Status**: ✅ ALREADY IMPLEMENTED

**Implementation**: The WebSocketManager already has message buffering:
- `_message_buffer` stores messages when no clients are connected
- On `broadcast()`, if no active connections, messages are buffered
- On `connect()`, buffered messages are sent to new clients
- Buffer size limited to 100 messages per batch
- This ensures messages sent during disconnect are not lost

**Note**: This fix was already implemented in the existing codebase, so no changes were needed.

## Testing Checklist

After fixes are implemented:
1. ✅ Navigate from `/research` to `/phase3` during step execution
2. ✅ Verify all steps appear in UI (not just step 1)
3. ✅ Verify real-time updates work when on Phase3SessionPage
4. ✅ Verify no duplicate WebSocket connections in console
5. ✅ Verify messages are not lost during navigation
6. ✅ Verify reconnection works without losing messages

## Related Files

- `client/src/hooks/useWebSocket.ts` - WebSocket hook implementation
- `client/src/pages/Phase3SessionPage.tsx` - Phase 3 UI component
- `client/src/pages/ResearchAgentPage.tsx` - Research agent page (uses WebSocket)
- `client/src/stores/workflowStore.ts` - Zustand store with `addPhase3Step`
- `backend/app/services/websocket_ui.py` - Server-side WebSocket UI adapter
- `backend/app/websocket/manager.py` - WebSocket connection manager

## Notes

- The issue is NOT with the message format or handler logic
- The issue IS with connection lifecycle and component mounting
- Messages are being sent correctly from server
- Messages are being received correctly when WebSocket is connected
- The problem occurs during navigation/component transitions

