# Editor UI Troubleshooting Guide

## How the Editor Service Works

### Current Implementation Flow

1. **Text Selection** (`client/src/utils/textSelection.ts`):
   - Listens for `mouseup` events on the content area
   - Uses `window.getSelection()` to get selected text
   - Finds the content container (walks up DOM tree to find `.stream-content-text`, `.prose`, etc.)
   - Calculates start/end positions relative to container
   - Returns `TextSelection` object

2. **Selection Detection** (`client/src/components/streaming/StreamDisplay.tsx`):
   - `handleTextSelect()` callback processes selection
   - Sets selection state if text is selected
   - Logs to console for debugging

3. **Editor Panel Display** (`client/src/components/streaming/StreamDisplay.tsx` line 277):
   - Shows `ContentEditorPanel` only if: `selection && batchId`
   - **Critical**: Both conditions must be true

4. **BatchId Source**:
   - Primary: From `useWorkflowStore((state) => state.batchId)`
   - Fallback: Can be passed as prop `batchId` to `StreamDisplay`
   - For history sessions: Should be set via `setBatchId(batchId)` in `HistoryPage.handleView()`

## Why Editor Might Not Appear

### Issue 1: Missing batchId

**Symptoms**: Selection works (you can select text) but no editor panel appears

**Diagnosis**:
- Open browser console
- Select text - you should see: `[StreamDisplay] Text selected: {...}`
- Check the log - if `batchId: 'MISSING'`, that's the problem

**Fix**:
- For history sessions: Ensure `setBatchId(batchId)` is called when viewing
- Check `HistoryPage.handleView()` - it should call `setBatchId(batchId)` (line 401)
- Verify batchId is in workflow store: `useWorkflowStore.getState().batchId`

### Issue 2: Text Selection Not Working

**Symptoms**: No console logs when selecting text, no selection state

**Possible Causes**:
1. **Content not in StreamDisplay**: If viewing report page, it uses `ReactMarkdown` directly, not `StreamDisplay`
2. **Event listener not attached**: Content area might not be mounted yet
3. **Selection outside content area**: Selection might be in a different component

**Diagnosis**:
- Check if content is rendered via `StreamDisplay` or `PhaseStreamDisplay`
- Check browser console for any errors
- Try selecting text - should see console log

**Fix**:
- Ensure content is displayed via `StreamDisplay` component
- For report page, we'd need to add editor support to `FinalReportPage.tsx`

### Issue 3: ReactMarkdown Content Structure

**Symptoms**: Selection works but positions are wrong or container not found

**Cause**: ReactMarkdown creates nested DOM structure, container detection might fail

**Fix Applied**: Updated `textSelection.ts` to walk up DOM tree and find proper container

## Current Status

### ✅ Working
- Text selection utilities
- Editor panel component
- API endpoints
- Backend service

### ⚠️ Needs Verification
- batchId availability in history sessions
- Text selection with ReactMarkdown content
- Editor panel positioning

### ❌ Known Issues
1. **Report Page**: Uses `ReactMarkdown` directly, not `StreamDisplay` - editor won't work there
2. **History Sessions**: batchId might not be set when just viewing (not resuming)
3. **Selection Detection**: Might not work with all content formats

## Testing Steps

1. **Test with Active Session**:
   - Start a research session
   - Go to research page
   - Select text in phase content
   - Should see editor panel

2. **Test with History Session**:
   - Go to history page
   - Click "查看报告" (View Report) on a completed session
   - Check console: `useWorkflowStore.getState().batchId` should have value
   - Navigate to research page (if phase content is shown there)
   - Select text - should see editor panel

3. **Debug Selection**:
   - Open browser console
   - Select text in any phase content
   - Look for: `[StreamDisplay] Text selected:` log
   - Check `batchId` value in log
   - If missing, check workflow store

## Quick Fixes Applied

1. ✅ Made `batchId` optional prop in `StreamDisplay` (can be passed from parent)
2. ✅ Added fallback: prop batchId → store batchId
3. ✅ Improved text selection to find correct container
4. ✅ Added debug logging
5. ✅ Made `PhaseStreamDisplay` pass batchId through
6. ✅ Added warning message if selection made but no batchId

## Next Steps to Fix

1. **Verify batchId in History Sessions**:
   - Check if `handleView()` properly sets batchId
   - Add batchId to session metadata if needed
   - Pass batchId as prop to components displaying history content

2. **Add Editor to Report Page**:
   - Wrap report content in `StreamDisplay` or add selection support
   - Or create separate editor component for report page

3. **Test Selection with Different Content Types**:
   - Test with Phase 1 goals (list format)
   - Test with Phase 2 plan (structured)
   - Test with Phase 3 steps (nested content)
   - Test with Phase 4 report (long markdown)

