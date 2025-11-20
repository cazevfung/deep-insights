# Phase 3 Step Rerun Trigger Logic Analysis

**Status**: ⚠️ Implementation has several critical issues that need to be addressed

**Created**: 2025-11-20  
**Related**: `backend/app/services/editor_service.py`, `backend/app/routes/research.py`

## Current Implementation Flow

### 1. When Goal Change is Detected

**Location**: `EditorService.apply_changes()` (line 324-331)

**Trigger Point**: 
- Happens **AFTER** loading the artifact
- Happens **BEFORE** saving the updated artifact
- Only for `phase == 'phase3'`

**Detection Method**: `_detect_phase3_goal_change()`
```python
# Step 1: Extract original selected text from artifact content
original_content = self._extract_content_from_artifact(artifact, phase)
selected_text = original_content[selected_range['start']:selected_range['end']]

# Step 2: Call detection with selected_text and replacement_text
step_rerun_info = self._detect_phase3_goal_change(session, selected_text, replacement_text)
```

**Detection Logic** (line 208-296):
1. Loads `phase3` artifact and extracts `plan` array
2. Uses regex pattern: `r'步骤\s*(\d+)\s*[:：]\s*(.+)'` to find "步骤 X: goal"
3. Matches step_id from pattern against plan
4. Compares `old_goal` vs `new_goal`
5. Returns step info if goal changed

**Issues with Detection**:
- ❌ **Fragile**: Relies on text pattern matching - fails if format differs
- ❌ **Context-dependent**: Only works if user edits text that matches the pattern
- ❌ **No validation**: Doesn't verify the step actually exists or is completed
- ❌ **Fallback logic**: Pattern 2 tries to match by substring, which can be inaccurate

### 2. When Plan is Updated

**Location**: `EditorService.apply_changes()` (line 338-357)

**Update Sequence**:
```python
# 1. Update the plan in memory
for step in plan:
    if step.get('step_id') == target_step_id:
        step['goal'] = step_rerun_info['new_goal']
        break

# 2. Save updated plan to phase3 artifact
session.save_phase_artifact("phase3", phase3_data, autosave=True)

# 3. Also save the edited content artifact (line 362)
session.save_phase_artifact(phase_key, artifact_data, autosave=True)
```

**Issues**:
- ⚠️ **Double save**: Artifact is saved twice (plan update + content update)
- ⚠️ **No transaction**: Two separate saves - if second fails, plan is updated but content isn't
- ⚠️ **Race condition**: Between saving and rerun loading the artifact

### 3. When Rerun is Triggered

**Location**: `backend/app/routes/research.py` (line 331-359)

**Trigger Condition**:
```python
if (result.get('metadata', {}).get('step_rerun_required') and 
    request.phase == 'phase3'):
```

**Trigger Method**:
```python
import asyncio
asyncio.create_task(
    workflow_service.rerun_phase3_step(
        batch_id=request.batch_id,
        session_id=session_id,  # ⚠️ Using batch_id as session_id
        step_id=step_id,
        regenerate_report=True
    )
)
```

**Issues**:
- ❌ **Async task**: No error handling - task can fail silently
- ❌ **No await**: Fire-and-forget - no way to know if rerun succeeded
- ❌ **Session ID assumption**: `session_id = request.batch_id` might be wrong
- ❌ **Race condition**: Rerun might load artifact before plan update is saved
- ❌ **No locking**: Concurrent reruns could conflict

## Data Consistency Issues

### Issue 1: Race Condition Between Save and Rerun

**Scenario**:
```
Time T1: apply_changes() saves updated plan to phase3 artifact
Time T2: apply_changes() saves updated content to phase_key artifact  
Time T3: asyncio.create_task() schedules rerun
Time T4: rerun_phase3_step() loads phase3 artifact
```

**Problem**: If T4 happens before T1 completes, rerun sees old plan. If T4 happens after T1 but before T2, rerun sees updated plan but old content.

**Impact**: Rerun might execute with inconsistent state.

### Issue 2: Double Save Without Transaction

**Current Flow**:
```python
# Save 1: Plan update
session.save_phase_artifact("phase3", phase3_data, autosave=True)

# Save 2: Content update  
session.save_phase_artifact(phase_key, artifact_data, autosave=True)
```

**Problem**: If Save 2 fails, plan is updated but content isn't. Artifact is in inconsistent state.

**Impact**: Data corruption - plan says one thing, content says another.

### Issue 3: Rerun Overwrites Plan Update

**Scenario**:
```
1. User edits goal → plan updated in apply_changes()
2. Rerun triggered asynchronously
3. rerun_phase3_step() loads phase3 artifact
4. rerun_phase3_step() might regenerate plan or overwrite it
```

**Problem**: The rerun process might load the artifact, see the updated plan, but then regenerate it or overwrite it during execution.

**Impact**: User's goal edit might be lost.

### Issue 4: No Validation of Step State

**Current**: Detection doesn't check if:
- Step is already completed
- Step is currently running
- Step exists in the plan
- Step is the last step (affects report regeneration)

**Impact**: Might trigger rerun for invalid steps or cause unexpected behavior.

### Issue 5: Session ID Mismatch

**Current**: `session_id = request.batch_id`

**Problem**: 
- `batch_id` format: `"20251119_123456"`
- `session_id` might be different format or stored separately
- `rerun_phase3_step()` expects proper session_id

**Impact**: Rerun might fail to load session or load wrong session.

## Recommended Fixes

### Fix 1: Improve Detection Reliability

```python
def _detect_phase3_goal_change(
    self,
    session: ResearchSession,
    selected_range: Dict[str, int],
    replacement_text: str,
    phase_key: str  # Add phase_key to know which step artifact
) -> Optional[Dict[str, Any]]:
    """More reliable detection using step_id from phase_key."""
    # If phase_key is "phase3_step_X", extract step_id directly
    if phase_key.startswith("phase3_step_"):
        step_id = int(phase_key.replace("phase3_step_", ""))
        # Load step-specific artifact to get old goal
        # Compare with replacement_text
        # Return if changed
    # Otherwise, use pattern matching as fallback
```

### Fix 2: Single Atomic Save

```python
# Combine plan update and content update into single save
if step_rerun_info:
    # Update plan
    # Update content
    # Single save with both updates
    session.save_phase_artifact("phase3", combined_data, autosave=True)
else:
    # Just save content
    session.save_phase_artifact(phase_key, artifact_data, autosave=True)
```

### Fix 3: Synchronous Rerun with Error Handling

```python
# Option A: Wait for rerun (blocking but safer)
try:
    await workflow_service.rerun_phase3_step(...)
    result['metadata']['step_rerun_status'] = 'completed'
except Exception as e:
    result['metadata']['step_rerun_status'] = 'failed'
    result['metadata']['step_rerun_error'] = str(e)

# Option B: Queue rerun with proper error handling
rerun_task = asyncio.create_task(...)
rerun_task.add_done_callback(lambda t: log_result(t.result()))
```

### Fix 4: Get Proper Session ID

```python
# Load session properly to get session_id
session = self._load_session(batch_id)
session_id = session.session_id  # Use actual session_id from session object
```

### Fix 5: Add Validation

```python
def _validate_step_rerun(
    self,
    session: ResearchSession,
    step_id: int
) -> Dict[str, Any]:
    """Validate that step can be rerun."""
    phase3_artifact = session.get_phase_artifact("phase3", {})
    plan = phase3_artifact.get('data', {}).get('phase3_result', {}).get('plan', [])
    
    # Check step exists
    step = next((s for s in plan if s.get('step_id') == step_id), None)
    if not step:
        return {'valid': False, 'error': 'Step not found in plan'}
    
    # Check step is completed (optional - might want to rerun in-progress steps)
    # ...
    
    return {'valid': True}
```

## Critical Bug: load_from_path Doesn't Exist

**Location**: `EditorService._load_session()` (line 45-49)

**Current Code**:
```python
def _load_session(self, batch_id: str) -> ResearchSession:
    batches_dir = self.config.get_batches_dir()
    batch_path = batches_dir / batch_id
    if not batch_path.exists():
        raise ValueError(f"Batch {batch_id} not found")
    return ResearchSession.load_from_path(batch_path)  # ❌ This method doesn't exist!
```

**Problem**: `ResearchSession.load_from_path()` doesn't exist in the codebase.

**Fix Required**:
```python
def _load_session(self, batch_id: str) -> ResearchSession:
    # Option 1: Use batch_id as session_id (if they're the same)
    return ResearchSession.load(batch_id)
    
    # Option 2: Find session_id from batch metadata
    # batches_dir = self.config.get_batches_dir()
    # batch_path = batches_dir / batch_id
    # session_file = batch_path / "session.json"  # If session is stored in batch dir
    # # Load and extract session_id, then use ResearchSession.load(session_id)
```

## Summary

**Current State**: 
- ❌ **BROKEN**: `load_from_path()` doesn't exist - code will crash
- ✅ Detection logic works for simple cases (pattern matching)
- ⚠️ Fragile and unreliable for edge cases
- ❌ Race conditions between saves and rerun
- ❌ No error handling for async rerun
- ❌ Potential data inconsistencies
- ❌ Session ID assumption might be wrong

**Recommended Approach**:
1. Use `step_id` from `phase_key` when available (more reliable)
2. Single atomic save for plan + content
3. Proper session_id retrieval
4. Add validation before rerun
5. Better error handling for rerun trigger
6. Consider synchronous rerun or proper async task management

