# Phase 3 Parsing Duplication Fix

## Problem
Phase 3 steps show duplicate items in `points_of_interest` (especially `notable_evidence`, `key_claims`, etc.), with the same items appearing 3 times.

## Root Cause
The issue was in `_execute_step_paged()` method in `research/phases/phase3_execute.py`:

**Line 476 (before fix):**
```python
agg_poi[k].extend(v[:10])  # cap per-window additions
```

When processing multiple windows (for sequential chunking strategy), the code was extending lists without checking for duplicates. If the same `notable_evidence` or `key_claims` items appeared in multiple windows, they would all be added, resulting in duplicates.

## Solution Implemented

### 1. Deduplication During Merge (Line 469-494)
Added deduplication logic when merging `points_of_interest` from each window:
- Checks if an item already exists by comparing extracted text
- Only adds new items that don't already exist
- Uses `_extract_entry_text()` to get comparable text for each item type

### 2. Final Deduplication Pass (Line 548-570)
Added a final cleanup pass after all windows are processed:
- Iterates through all `points_of_interest` categories
- Removes duplicates based on normalized text comparison
- Ensures no duplicates remain before returning results

### 3. Safeguard in `_finalize_step_output` (Line 787-808)
Added an additional deduplication pass in the finalization step:
- Acts as a final safeguard before output
- Handles any edge cases where duplicates might have slipped through
- Uses the same text-based deduplication logic

## How It Works

1. **During Window Processing**: When merging results from each window, check if the item text already exists before adding
2. **After All Windows**: Final pass to remove any remaining duplicates using normalized text comparison
3. **Before Output**: Final safeguard in `_finalize_step_output` to ensure clean output

## Deduplication Logic

The deduplication uses text-based comparison:
- Extracts the primary text from each item using `_extract_entry_text()`
- Normalizes text (strip, lowercase) for comparison
- Uses a Set to track seen texts for O(1) lookup
- Preserves the first occurrence of each unique item

## Testing

After this fix, verify:
1. ✅ No duplicate items in `notable_evidence`
2. ✅ No duplicate items in `key_claims`
3. ✅ No duplicate items in other `points_of_interest` categories
4. ✅ Items still appear correctly when they should (not over-deduplicated)
5. ✅ Performance is acceptable (deduplication is O(n) per category)

## Files Modified

- `research/phases/phase3_execute.py`:
  - `_execute_step_paged()`: Added deduplication during merge and final pass
  - `_finalize_step_output()`: Added safeguard deduplication

