# Scraping Control Center Invalid Tasks Debug Tests

This directory contains debug tests to verify that the scraping control center correctly handles invalid tasks (tasks that are already COMPLETED or FAILED) and prevents them from blocking the queue.

## Problem Fixed

Previously, when tasks became invalid (COMPLETED or FAILED) due to race conditions or previous runs, they would remain in the queue. Workers would repeatedly try to process these invalid tasks, exhaust their retries, and then go idle. However, `wait_for_completion` would see that the queue still had items and keep waiting forever, causing the system to hang.

## Solution

The fix includes:
1. **Prevention**: Invalid tasks are not added to the queue in the first place
2. **Cleanup**: When workers exhaust retries, they check if remaining tasks are invalid and remove them
3. **Detection**: The system properly detects when all valid tasks are complete

## Test Files

### 1. `test_scraping_control_center_invalid_tasks.py`

Unit tests for the scraping control center invalid task handling:
- Test 1: Invalid tasks removed from queue (prevention)
- Test 2: Queue cleanup on retry exhaustion
- Test 3: Workers continue with valid tasks
- Test 4: wait_for_completion with invalid tasks

**Run:**
```bash
python tests/debugging/test_scraping_control_center_invalid_tasks.py
```

### 2. `test_scraping_workflow_invalid_tasks_integration.py`

Integration tests that simulate real-world scenarios:
- Scenario 1: All tasks valid (baseline test)
- Scenario 2: Mixed valid and invalid tasks
- Scenario 3: Race condition simulation (tasks become invalid after queuing)
- Scenario 4: Worker retry exhaustion and cleanup

**Run:**
```bash
python tests/debugging/test_scraping_workflow_invalid_tasks_integration.py
```

## Expected Results

All tests should pass, demonstrating that:
1. Invalid tasks are not added to the queue
2. Invalid tasks are removed when detected
3. Workers can continue processing valid tasks
4. The system completes successfully even when invalid tasks exist

## Debugging

If tests fail, check:
1. Queue size - should only contain valid (PENDING) tasks
2. State tracker - should track all tasks but only queue valid ones
3. Worker logs - should show cleanup of invalid tasks
4. Completion detection - should work even with invalid tasks in tracker

## Related Code Changes

The fixes are in `backend/lib/scraping_control_center.py`:
- `add_task()` and `add_tasks()` - prevent invalid tasks from being queued
- `_assign_task_to_worker()` - cleanup invalid tasks when retries exhausted
- `wait_for_completion()` - correctly detects completion


