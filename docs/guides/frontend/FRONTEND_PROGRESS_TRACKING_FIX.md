# Frontend Progress Tracking Fix Summary

## Problem
The frontend was calculating progress based on **started processes** (`scrapingStatus.total` from `scraping:status`), instead of using the **TOTAL expected processes** that need to run in the entire session (from `batch:initialized`).

This caused:
- Progress bar showing incorrect percentage (e.g., 2/6 = 33% when it should be 2/10 = 20%)
- "总计" (Total) showing started processes count instead of expected total
- Phase transition potentially happening prematurely

## Solution

### 1. Added Expected Total Storage
**File**: `client/src/stores/workflowStore.ts`

Added new fields to `scrapingStatus`:
- `expectedTotal: number` - Stores total from `batch:initialized` (the actual target)
- `completionRate: number` - 0.0 to 1.0 from backend (calculated against expected_total)
- `is100Percent: boolean` - Flag from backend indicating 100% completion
- `canProceedToResearch: boolean` - Explicit flag for research phase transition

### 2. Added Batch Initialized Handler
**File**: `client/src/hooks/useWebSocket.ts`

Added handler for `batch:initialized` message:
```typescript
case 'batch:initialized':
  // Store expected total from batch initialization
  // This is the TOTAL scraping processes that need to run, not just started ones
  updateScrapingStatus({
    expectedTotal: data.total_processes || 0,
  })
```

### 3. Updated Status Handler
**File**: `client/src/hooks/useWebSocket.ts`

Updated `scraping:status` handler to use backend's completion rate and flags:
```typescript
updateScrapingStatus({
  total: data.total || 0,  // Keep for backward compatibility (started processes)
  completed: data.completed || 0,
  failed: data.failed || 0,
  inProgress: data.inProgress || 0,
  items: normalizedItems,
  // Use completion rate and flags from backend (calculated against expected_total)
  completionRate: data.completion_rate ?? 0.0,
  is100Percent: data.is_100_percent ?? false,
  canProceedToResearch: data.can_proceed_to_research ?? false,
})
```

### 4. Fixed Progress Calculation
**File**: `client/src/pages/ScrapingProgressPage.tsx`

Changed progress calculation to use `expectedTotal` and `completionRate`:
```typescript
const overallProgress = scrapingStatus.expectedTotal > 0
  ? scrapingStatus.completionRate > 0
    ? scrapingStatus.completionRate * 100  // Use backend's completion_rate
    : ((scrapingStatus.completed + scrapingStatus.failed) / scrapingStatus.expectedTotal) * 100
  : scrapingStatus.total > 0
  ? ((scrapingStatus.completed + scrapingStatus.failed) / scrapingStatus.total) * 100  // Fallback
  : 0
```

### 5. Fixed Total Display
**File**: `client/src/pages/ScrapingProgressPage.tsx`

Changed "总计" (Total) to show `expectedTotal`:
```typescript
总计: {scrapingStatus.expectedTotal > 0 ? scrapingStatus.expectedTotal : scrapingStatus.total}
```

### 6. Fixed Phase Transition Logic
**Files**: 
- `client/src/pages/ScrapingProgressPage.tsx`
- `client/src/hooks/useWorkflowStep.ts`

Changed completion check to use backend's `is100Percent` flag:
```typescript
// Old (incorrect):
if (scrapingStatus.total > 0 && scrapingStatus.completed + scrapingStatus.failed === scrapingStatus.total)

// New (correct):
if (scrapingStatus.is100Percent || scrapingStatus.canProceedToResearch)
```

## How It Works Now

1. **At Workflow Start**:
   - Backend sends `batch:initialized` with `total_processes` (e.g., 10)
   - Frontend stores this as `expectedTotal`

2. **During Scraping**:
   - Backend sends `scraping:status` with:
     - `total`: Started processes count (e.g., 6)
     - `completion_rate`: Calculated as `(completed + failed) / expected_total` (e.g., 2/10 = 0.2)
     - `is_100_percent`: `false` until all 10 are complete
   - Frontend uses `completion_rate` for progress bar (20%)
   - Frontend displays `expectedTotal` as "总计" (10)

3. **At 100% Completion**:
   - Backend sends `scraping:status` with `is_100_percent: true`
   - Frontend transitions to research phase only when `is100Percent === true`

## Benefits

✅ **Accurate Progress**: Progress bar shows correct percentage based on expected total  
✅ **Correct Total Display**: "总计" shows expected processes, not started ones  
✅ **Prevents Premature Transition**: Research phase only starts when ALL expected processes complete  
✅ **Backend-Frontend Sync**: Frontend uses same calculation logic as backend  
✅ **Backward Compatible**: Falls back to `total` if `expectedTotal` not set yet

## Testing

To verify the fix:
1. Start a workflow with links that will create multiple processes (e.g., YouTube/Bilibili = 2 processes each)
2. Check that "总计" shows the expected total from the beginning
3. Verify progress bar shows correct percentage (completed/expectedTotal, not completed/started)
4. Confirm research phase only starts when all expected processes are 100% complete



