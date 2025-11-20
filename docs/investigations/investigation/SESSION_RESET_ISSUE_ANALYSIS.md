# Session Reset Issue Analysis

## Problem Description

After a complete research session, when the user clicks somewhere in the web app:
1. All research results from that session disappear
2. A new session appears to start
3. When inputting new links, there's an error

## Root Causes Identified

### 1. **State Management Issue: No State Reset on Navigation**

**Location**: `client/src/pages/LinkInputPage.tsx`

**Problem**: 
- The `LinkInputPage` does not check if there's an existing `batchId` in the workflow store before allowing new link input
- When a user navigates to "/" (LinkInputPage) after completing a session, the old state (including `batchId`, `scrapingStatus`, `researchAgentStatus`, `phase3Steps`, `finalReport`) remains in the Zustand store
- The page allows submitting new links even though there's an active/resolved session in memory

**Code Evidence**:
```typescript
// LinkInputPage.tsx - No check for existing batchId
const handleSubmit = async (e: React.FormEvent) => {
  // ... directly formats links without checking if batchId exists
  const response = await apiService.formatLinks(urlList)
  setBatchId(response.batch_id)  // Sets NEW batchId, but old state remains
}
```

### 2. **Incomplete State Reset When batchId Changes**

**Location**: `client/src/stores/workflowStore.ts` (line 193-199)

**Problem**:
- When `setBatchId()` is called with a new batchId, it only resets `workflowStarted` flag
- All other state remains: `scrapingStatus`, `researchAgentStatus`, `phase3Steps`, `finalReport`, `errors`, etc.
- This creates a state mismatch where:
  - New `batchId` is set
  - Old workflow data (scraping items, research goals, phase 3 steps, final report) still exists
  - WebSocket might still be connected to old batchId
  - UI shows mixed state (new batchId + old data)

**Code Evidence**:
```typescript
setBatchId: (batchId) => {
  // Reset workflowStarted when batchId changes
  set((state) => ({
    batchId,
    workflowStarted: state.batchId === batchId ? state.workflowStarted : false,
    // ❌ All other state (scrapingStatus, researchAgentStatus, phase3Steps, finalReport) remains!
  }))
},
```

### 3. **WebSocket Connection State Mismatch**

**Location**: `client/src/hooks/useWebSocket.ts`, `client/src/pages/ScrapingProgressPage.tsx`

**Problem**:
- When navigating to LinkInputPage and submitting new links, the WebSocket connection might still be active for the old `batchId`
- The `ScrapingProgressPage` connects to WebSocket using `batchId`, but if the old batchId state hasn't been cleared, there could be:
  - Multiple WebSocket connections (old + new)
  - WebSocket messages for old batchId updating new batchId's state
  - Connection errors when trying to connect with invalid/old batchId

**Code Evidence**:
```typescript
// ScrapingProgressPage.tsx line 28
useWebSocket(batchId || '')  // Connects with current batchId, but old connections might still be active

// useWebSocket.ts line 55
const wsUrl = `ws://localhost:3000/ws/${batchId}`  // If batchId is stale, wrong connection
```

### 4. **Automatic Navigation Logic Conflict**

**Location**: `client/src/hooks/useProgressNavigation.ts`

**Problem**:
- The `useProgressNavigation` hook automatically navigates based on workflow progress
- When a new `batchId` is set but old state remains:
  - `useCurrentActiveStep` might calculate the wrong step (e.g., thinks all steps are completed because `finalReport` exists)
  - Navigation might jump to wrong page
  - Or navigation might be blocked/confused by conflicting state

**Code Evidence**:
```typescript
// useProgressNavigation.ts
useEffect(() => {
  // Calculates currentActiveStep based on workflow state
  // If old state (finalReport, phase3Steps) exists but new batchId is set,
  // the calculation will be wrong
}, [currentActiveStep, navigate, batchId])
```

### 5. **No State Persistence**

**Location**: Zustand stores (in-memory only)

**Problem**:
- Zustand stores are in-memory only - state is lost on page refresh
- However, the issue occurs WITHOUT page refresh (just clicking/navigating)
- This means the state is being cleared/reset somewhere, OR the state appears cleared because it's mismatched with the current batchId

### 6. **Error When Inputting New Links**

**Likely Causes**:
1. **Backend Conflict**: When formatting new links with an existing batchId in state, the backend creates a new batchId, but the frontend might try to:
   - Connect WebSocket to old batchId
   - Check workflow status for old batchId
   - Load data for old batchId

2. **State Mismatch**: The workflow store has:
   - New `batchId` (from new link submission)
   - Old `scrapingStatus.items` (from previous session)
   - Old `researchAgentStatus` (goals, plan from previous session)
   - Old `phase3Steps` and `finalReport` (from previous session)
   
   This creates a situation where:
   - UI shows old data (from previous session)
   - But `batchId` points to new session
   - WebSocket/API calls use new batchId but state expects old data
   - Results in errors or incorrect behavior

3. **Workflow Start Logic**: In `ScrapingProgressPage.tsx`, when the component mounts:
   - It checks if workflow is running for the `batchId`
   - If `batchId` is new but old state exists, it might try to start a workflow that's already in progress (old one)
   - Or it might try to start workflow for new batchId but with old state causing conflicts

## Why Results "Disappear"

When clicking somewhere and navigating to "/":
1. User navigates to LinkInputPage
2. The workflow store still has old state (scrapingStatus, researchAgentStatus, phase3Steps, finalReport)
3. But the UI might show empty/incorrect state because:
   - The `batchId` might have changed (if user submitted new links)
   - The UI components check for `batchId` match with data
   - The `useProgressNavigation` might navigate away from the page showing results
   - The state appears "cleared" because it's mismatched with current `batchId`

## Summary

The core issue is **state management**: when starting a new session (submitting new links), the old session's state is not properly cleared. This creates a state mismatch where:
- New `batchId` is set
- Old workflow data remains
- WebSocket connections conflict
- UI shows incorrect/mixed state
- Errors occur when trying to operate with mismatched state

## Recommended Fixes (Not Implemented - Analysis Only)

1. **Add state reset in LinkInputPage**: Before allowing new link submission, check if there's an existing `batchId` and reset the workflow store if needed
2. **Complete state reset in setBatchId**: When `batchId` changes, reset ALL workflow state, not just `workflowStarted`
3. **Add "Start New Session" button**: Explicitly allow users to start a new session, which clears all state
4. **WebSocket cleanup**: Ensure WebSocket connections are properly closed when batchId changes
5. **State validation**: Add checks to ensure state consistency (e.g., verify that `batchId` matches the data in `scrapingStatus`, `researchAgentStatus`, etc.)

