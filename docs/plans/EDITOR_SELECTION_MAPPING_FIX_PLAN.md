# Editor Selection Mapping Fix Plan

**Status**: 📋 Planning - Not Implemented

**Created**: 2025-11-20  
**Related Documents**:
- `investigations/EDITOR_SELECTION_TO_JSON_MAPPING_DETAILED.md` - Detailed investigation
- `investigations/EDITOR_SELECTION_MAPPING_ISSUES.md` - Initial analysis
- `plans/AI_CONTENT_EDITOR_EXECUTION_PLAN.md` - Original implementation plan

**Priority**: 🔴 **CRITICAL** - Current implementation will corrupt data for Phase 1/2 editing

---

## Executive Summary

This plan addresses the fundamental architectural mismatch between frontend text selection (flat text with positions) and backend data storage (structured JSON). The fix implements a **field-level editing system** with selection metadata tracking, eliminating position-based string replacement for structured data.

### Key Changes

1. **Selection Metadata Tracking**: Track which array item/object field was selected
2. **Field-Level Updates**: Replace entire field values instead of substring replacement
3. **Structured Content Extraction**: Proper handling of arrays/objects per phase
4. **AI Output Format Specification**: Clear instructions for structured data editing
5. **Validation & Error Handling**: Prevent data corruption with type checking

### Implementation Phases

- **Phase 1**: Immediate Safety (Validation & Error Handling) - 1-2 days
- **Phase 2**: Field-Level Editing for Phase 1/2 - 1 week
- **Phase 3**: Enhanced Phase 3 Support - 3-4 days
- **Phase 4**: Phase 4 Markdown Handling - 2-3 days
- **Phase 5**: Testing & Refinement - 1 week

**Total Estimated Time**: 3-4 weeks

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Solution Architecture](#solution-architecture)
3. [Implementation Phases](#implementation-phases)
4. [Detailed Implementation Steps](#detailed-implementation-steps)
5. [Testing Strategy](#testing-strategy)
6. [Rollback Plan](#rollback-plan)
7. [Risk Assessment](#risk-assessment)
8. [Success Criteria](#success-criteria)

---

## Problem Statement

### Current Issues

1. **Type Mismatch**: Arrays/objects converted to strings, losing structure
2. **Position Mismatch**: Frontend positions (rendered text) ≠ backend positions (JSON strings)
3. **Data Corruption**: String replacement on structured data corrupts JSON
4. **AI Ambiguity**: No format specification for structured data output

### Impact

- 🔴 **Phase 1 (Goals)**: Will corrupt data - arrays become strings
- 🔴 **Phase 2 (Plan)**: Will corrupt data - arrays become strings
- 🟡 **Phase 3 (Steps)**: May work for simple cases, fails for structured content
- 🟢 **Phase 4 (Report)**: Should work, but markdown formatting may cause issues

---

## Solution Architecture

### Core Design: Field-Level Editing with Metadata

Instead of string replacement based on character positions, we'll:

1. **Track Selection Context**: Identify which array item and field was selected
2. **Extract Target Field**: Get the specific field value to edit
3. **Update Field Directly**: Replace entire field value, preserving structure
4. **Validate Structure**: Ensure data structure is preserved

### Architecture Diagram

```
User Selection (DOM)
    ↓
Frontend: Enhanced getTextSelection()
    ↓
{ text, start, end, phase, itemId, fieldName, itemIndex }
    ↓
API Request: EditorApplyRequest (with metadata)
    ↓
Backend: EditorService.apply_changes()
    ↓
Load Artifact → Extract Target Field (using metadata)
    ↓
Field-Level Update (preserve structure)
    ↓
Validate Structure → Save Artifact
```

### Key Components

1. **Enhanced Selection Capture** (`textSelection.ts`)
   - Track item ID, field name, item index
   - Identify selection context from DOM

2. **Field Extraction** (`editor_service.py`)
   - Use metadata to extract specific field
   - Handle arrays, objects, nested structures

3. **Field-Level Updates** (`editor_service.py`)
   - Replace entire field value
   - Preserve data structure
   - Validate before saving

4. **AI Prompt Enhancement** (`editor/prompts/system.md`)
   - Phase-specific output format
   - JSON schema for structured data

---

## Implementation Phases

### Phase 1: Immediate Safety (Validation & Error Handling)

**Duration**: 1-2 days  
**Priority**: 🔴 **CRITICAL** - Prevents data corruption

**Goals**:
- Add validation to prevent data corruption
- Add error handling for type mismatches
- Disable editing for Phase 1/2 until fixed
- Add logging for debugging

**Deliverables**:
- Type checking in `_extract_content_from_artifact`
- Validation in `_update_content_in_artifact`
- Error messages for users
- Feature flags to disable problematic phases

### Phase 2: Field-Level Editing for Phase 1/2

**Duration**: 1 week  
**Priority**: 🔴 **CRITICAL** - Core functionality

**Goals**:
- Implement selection metadata tracking
- Implement field-level updates for Phase 1 goals
- Implement field-level updates for Phase 2 plan
- Update frontend to track metadata

**Deliverables**:
- Enhanced `TextSelection` interface with metadata
- Frontend metadata extraction from DOM
- Backend field extraction using metadata
- Field-level update logic
- Phase 1/2 editing working correctly

### Phase 3: Enhanced Phase 3 Support

**Duration**: 3-4 days  
**Priority**: 🟡 **HIGH** - Improve reliability

**Goals**:
- Handle structured Phase 3 step content
- Support editing different fields (summary, article, etc.)
- Improve step content extraction

**Deliverables**:
- Field-level updates for Phase 3 step content
- Support for structured fields (keyClaims, analysis, etc.)
- Improved content extraction logic

### Phase 4: Phase 4 Markdown Handling

**Duration**: 2-3 days  
**Priority**: 🟢 **MEDIUM** - Polish

**Goals**:
- Handle markdown formatting in Phase 4
- Accurate position mapping for markdown
- Preserve markdown syntax

**Deliverables**:
- Markdown-aware position mapping
- Markdown syntax preservation
- Improved Phase 4 editing

### Phase 5: Testing & Refinement

**Duration**: 1 week  
**Priority**: 🔴 **CRITICAL** - Quality assurance

**Goals**:
- Comprehensive testing for all phases
- Edge case handling
- Performance optimization
- Documentation

**Deliverables**:
- Unit tests for all components
- Integration tests for full flow
- Manual testing checklist
- Updated documentation

---

## Detailed Implementation Steps

### Phase 1: Immediate Safety

#### Step 1.1: Add Type Validation

**File**: `backend/app/services/editor_service.py`

**Changes**:
```python
def _extract_content_from_artifact(self, artifact: Dict[str, Any], phase: str) -> str:
    """Extract content string from phase artifact."""
    data = artifact.get('data', artifact) if isinstance(artifact, dict) else {}
    
    if phase == 'phase1':
        goals = data.get('goals')
        if isinstance(goals, list):
            # NEW: Log warning and raise error
            logger.error(
                f"Phase 1 artifact contains goals array, not string. "
                f"Cannot use string-based editing. Use field-level editing instead."
            )
            raise ValueError(
                "Phase 1 goals are stored as an array. "
                "String-based editing is not supported. "
                "Please use field-level editing (coming soon)."
            )
        # Continue with existing logic for backward compatibility
        return data.get('content', data.get('output', ''))
    
    # Similar validation for phase2
    elif phase == 'phase2':
        plan = data.get('plan')
        if isinstance(plan, list):
            logger.error(f"Phase 2 artifact contains plan array, not string.")
            raise ValueError(
                "Phase 2 plan is stored as an array. "
                "String-based editing is not supported. "
                "Please use field-level editing (coming soon)."
            )
        return data.get('content', '')
    
    # ... rest of existing logic
```

**Rationale**: Prevents data corruption by detecting type mismatches early

#### Step 1.2: Add Update Validation

**File**: `backend/app/services/editor_service.py`

**Changes**:
```python
def _update_content_in_artifact(
    self, 
    artifact: Dict[str, Any], 
    phase: str, 
    selected_range: Dict[str, int],
    replacement_text: str
) -> Dict[str, Any]:
    """Update artifact content with replacement text."""
    data = artifact.get('data', {})
    
    # NEW: Validate structure before update
    if phase == 'phase1':
        if isinstance(data.get('goals'), list):
            raise ValueError(
                "Cannot update goals array using string replacement. "
                "Use field-level editing instead."
            )
    elif phase == 'phase2':
        if isinstance(data.get('plan'), list):
            raise ValueError(
                "Cannot update plan array using string replacement. "
                "Use field-level editing instead."
            )
    
    # Continue with existing logic for string-based updates
    # (for Phase 4 and simple Phase 3 cases)
    # ...
```

**Rationale**: Prevents structure corruption by validating before update

#### Step 1.3: Add Feature Flags

**File**: `backend/app/services/editor_service.py`

**Changes**:
```python
class EditorService:
    def __init__(self, config: Config):
        self.config = config
        self.editor_config = config.get_editor_config()
        # NEW: Feature flags
        self.feature_flags = {
            'phase1_editing_enabled': False,  # Disable until fixed
            'phase2_editing_enabled': False,  # Disable until fixed
            'phase3_editing_enabled': True,   # Enable with caution
            'phase4_editing_enabled': True,   # Enable (should work)
        }
    
    async def apply_changes(self, batch_id: str, phase: str, ...):
        # NEW: Check feature flag
        flag_key = f'{phase}_editing_enabled'
        if not self.feature_flags.get(flag_key, False):
            raise ValueError(
                f"Editing for {phase} is currently disabled. "
                f"Please wait for the fix to be deployed."
            )
        
        # Continue with existing logic
        # ...
```

**Rationale**: Allows disabling problematic phases without code changes

#### Step 1.4: Add User-Friendly Error Messages

**File**: `backend/app/routes/research.py`

**Changes**:
```python
@router.post("/editor/apply")
async def editor_apply(request: EditorApplyRequest):
    try:
        editor_service = get_editor_service()
        result = await editor_service.apply_changes(...)
        return result
    except ValueError as e:
        # NEW: User-friendly error messages
        error_msg = str(e)
        if "array" in error_msg.lower() or "string replacement" in error_msg.lower():
            return {
                "status": "error",
                "error": "editing_not_supported",
                "message": (
                    "This content cannot be edited using text selection. "
                    "The content is stored in a structured format. "
                    "Field-level editing support is coming soon."
                ),
                "user_message": error_msg
            }
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"Editor apply error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**Rationale**: Provides clear feedback to users about limitations

---

### Phase 2: Field-Level Editing for Phase 1/2

#### Step 2.1: Enhance TextSelection Interface

**File**: `client/src/types/editor.ts`

**Changes**:
```typescript
export interface TextSelection {
  text: string
  start: number
  end: number
  phase: 'phase1' | 'phase2' | 'phase3' | 'phase4'
  stepId?: string  // For Phase 3
  
  // NEW: Selection metadata
  itemId?: number | string      // ID of the array item (goal.id, step.step_id)
  itemIndex?: number             // Index in array (0, 1, 2, ...)
  fieldName?: string             // Field name within object (goal_text, rationale, goal, etc.)
  fieldPath?: string[]           // JSONPath-like path (['goals', 0, 'goal_text'])
  
  element?: HTMLElement          // DOM element containing the selection
}
```

**Rationale**: Adds metadata needed for field-level editing

#### Step 2.2: Extract Metadata from DOM (Phase 1)

**File**: `client/src/components/research/ResearchGoalList.tsx`

**Changes**:
```typescript
// Add data attributes to goal elements
<li
  key={goalId}
  data-goal-id={goalId}
  data-goal-index={index}
  className={...}
>
  <article>
    <h5
      data-field-name="goal_text"
      data-goal-id={goalId}
      className={...}
    >
      {goal.goal_text || '正在生成研究目标…'}
    </h5>
    {goal.rationale && (
      <p
        data-field-name="rationale"
        data-goal-id={goalId}
        className={...}
      >
        {goal.rationale}
      </p>
    )}
  </article>
</li>
```

**Rationale**: Adds metadata to DOM for extraction

#### Step 2.3: Extract Metadata in Selection Handler

**File**: `client/src/utils/textSelection.ts`

**Changes**:
```typescript
export function getTextSelection(): TextSelection | null {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) {
    return null
  }

  const range = selection.getRangeAt(0)
  const selectedText = selection.toString().trim()
  
  if (!selectedText || selectedText.length === 0) {
    return null
  }

  // Find container element
  let container = range.commonAncestorContainer
  if (container.nodeType === Node.TEXT_NODE) {
    container = container.parentElement!
  }

  // Find content container (existing logic)
  let contentContainer = container as HTMLElement
  // ... existing container finding logic ...

  // NEW: Extract metadata from DOM
  const metadata = extractSelectionMetadata(container as HTMLElement, contentContainer)
  
  // Calculate positions (existing logic)
  const containerText = contentContainer.textContent || ''
  const preRange = range.cloneRange()
  preRange.selectNodeContents(contentContainer)
  preRange.setEnd(range.startContainer, range.startOffset)
  const start = preRange.toString().length
  const end = start + selectedText.length

  return {
    text: selectedText,
    start,
    end,
    phase: 'phase1', // Will be set by caller
    element: contentContainer,
    // NEW: Include metadata
    ...metadata
  }
}

// NEW: Extract metadata from DOM
function extractSelectionMetadata(
  element: HTMLElement,
  container: HTMLElement
): Partial<TextSelection> {
  const metadata: Partial<TextSelection> = {}
  
  // Walk up DOM tree to find metadata attributes
  let current: HTMLElement | null = element
  while (current && current !== container.parentElement) {
    // Check for Phase 1 goal metadata
    if (current.hasAttribute('data-goal-id')) {
      metadata.itemId = parseInt(current.getAttribute('data-goal-id') || '0')
      metadata.itemIndex = parseInt(current.getAttribute('data-goal-index') || '0')
      
      // Find field name from child elements
      const fieldElement = current.querySelector('[data-field-name]')
      if (fieldElement) {
        metadata.fieldName = fieldElement.getAttribute('data-field-name') || undefined
      }
      
      // Build field path
      if (metadata.itemId !== undefined && metadata.fieldName) {
        metadata.fieldPath = ['goals', metadata.itemIndex, metadata.fieldName]
      }
      
      break
    }
    
    // Check for Phase 2 plan metadata (similar pattern)
    if (current.hasAttribute('data-step-id')) {
      metadata.itemId = parseInt(current.getAttribute('data-step-id') || '0')
      metadata.itemIndex = parseInt(current.getAttribute('data-step-index') || '0')
      
      const fieldElement = current.querySelector('[data-field-name]')
      if (fieldElement) {
        metadata.fieldName = fieldElement.getAttribute('data-field-name') || undefined
      }
      
      if (metadata.itemId !== undefined && metadata.fieldName) {
        metadata.fieldPath = ['plan', metadata.itemIndex, metadata.fieldName]
      }
      
      break
    }
    
    current = current.parentElement
  }
  
  return metadata
}
```

**Rationale**: Extracts metadata from DOM attributes

#### Step 2.4: Update API Request Type

**File**: `client/src/types/editor.ts`

**Changes**:
```typescript
export interface EditorApplyRequest {
  batch_id: string
  phase: string
  step_id?: string | null
  selected_range: { start: number; end: number }
  replacement_text: string
  
  // NEW: Selection metadata
  item_id?: number | string
  item_index?: number
  field_name?: string
  field_path?: string[]
}
```

**Rationale**: Includes metadata in API request

#### Step 2.5: Implement Field Extraction (Backend)

**File**: `backend/app/services/editor_service.py`

**Changes**:
```python
def _extract_field_from_artifact(
    self,
    artifact: Dict[str, Any],
    field_path: List[Union[str, int]],
    phase: str
) -> Optional[str]:
    """Extract specific field value from artifact using field path.
    
    Args:
        artifact: Phase artifact
        field_path: Path to field, e.g., ['goals', 0, 'goal_text']
        phase: Phase identifier
    
    Returns:
        Field value as string, or None if not found
    """
    data = artifact.get('data', artifact) if isinstance(artifact, dict) else {}
    
    # Navigate path
    current = data
    for segment in field_path:
        if isinstance(segment, int):
            # Array index
            if isinstance(current, list) and 0 <= segment < len(current):
                current = current[segment]
            else:
                return None
        else:
            # Object key
            if isinstance(current, dict):
                current = current.get(segment)
            else:
                return None
        
        if current is None:
            return None
    
    # Convert to string
    if isinstance(current, str):
        return current
    elif isinstance(current, (int, float, bool)):
        return str(current)
    else:
        # For complex types, return JSON string
        return json.dumps(current, ensure_ascii=False)
    
    return None
```

**Rationale**: Extracts specific field using path

#### Step 2.6: Implement Field-Level Update (Backend)

**File**: `backend/app/services/editor_service.py`

**Changes**:
```python
def _update_field_in_artifact(
    self,
    artifact: Dict[str, Any],
    field_path: List[Union[str, int]],
    new_value: str,
    phase: str
) -> Dict[str, Any]:
    """Update specific field in artifact using field path.
    
    Args:
        artifact: Phase artifact
        field_path: Path to field, e.g., ['goals', 0, 'goal_text']
        new_value: New field value
        phase: Phase identifier
    
    Returns:
        Updated artifact
    """
    # Ensure artifact has proper structure
    if not isinstance(artifact, dict):
        artifact = {'data': artifact}
    
    data = artifact.get('data', {})
    if not isinstance(data, dict):
        data = {'content': data}
        artifact['data'] = data
    
    # Navigate to parent of target field
    current = data
    for i, segment in enumerate(field_path[:-1]):
        if isinstance(segment, int):
            if isinstance(current, list) and 0 <= segment < len(current):
                current = current[segment]
            else:
                raise ValueError(f"Invalid path segment: {segment}")
        else:
            if isinstance(current, dict):
                current = current[segment]
            else:
                raise ValueError(f"Invalid path segment: {segment}")
    
    # Update target field
    target_field = field_path[-1]
    if isinstance(current, dict):
        current[target_field] = new_value
    else:
        raise ValueError(f"Cannot update field in non-dict: {type(current)}")
    
    artifact['data'] = data
    return artifact
```

**Rationale**: Updates specific field preserving structure

#### Step 2.7: Update apply_changes to Use Field-Level Updates

**File**: `backend/app/services/editor_service.py`

**Changes**:
```python
async def apply_changes(
    self,
    batch_id: str,
    phase: str,
    selected_range: Dict[str, int],
    replacement_text: str,
    step_id: Optional[str] = None,
    # NEW: Metadata parameters
    item_id: Optional[Union[int, str]] = None,
    item_index: Optional[int] = None,
    field_name: Optional[str] = None,
    field_path: Optional[List[Union[str, int]]] = None
) -> Dict[str, Any]:
    """Apply changes to phase content and immediately persist."""
    try:
        session = self._load_session(batch_id)
        phase_key = self._get_phase_key(phase, step_id)
        
        artifact = session.get_phase_artifact(phase_key, {})
        if not artifact:
            raise ValueError(f"Phase artifact {phase_key} not found for batch {batch_id}")
        
        # NEW: Use field-level update if metadata is available
        if field_path and field_name:
            # Field-level update
            updated_artifact = self._update_field_in_artifact(
                artifact, field_path, replacement_text, phase
            )
            
            # Validate structure is preserved
            self._validate_artifact_structure(updated_artifact, phase)
            
        else:
            # Fallback to string-based update (for Phase 4 and simple cases)
            # But first validate it's safe
            if phase in ['phase1', 'phase2']:
                raise ValueError(
                    f"Field-level editing required for {phase}. "
                    f"Metadata (item_id, field_name) must be provided."
                )
            
            # Existing string-based logic for Phase 3/4
            updated_artifact = self._update_content_in_artifact(
                artifact, phase, selected_range, replacement_text
            )
        
        # Save immediately
        artifact_data = updated_artifact.get('data', updated_artifact)
        session.save_phase_artifact(phase_key, artifact_data, autosave=True)
        
        # Extract updated content for response
        if field_path:
            updated_content = self._extract_field_from_artifact(
                updated_artifact, field_path, phase
            ) or replacement_text
        else:
            updated_content = self._extract_content_from_artifact(updated_artifact, phase)
        
        return {
            "status": "success",
            "updated_content": updated_content,
            "metadata": {
                "edit_timestamp": datetime.now().isoformat(),
                "persisted": True,
                "will_affect_future_phases": True,
                "phase": phase,
                "step_id": step_id,
                "field_updated": field_name,
                "item_id": item_id
            }
        }
        
    except Exception as e:
        logger.error(f"Error in apply_changes: {e}", exc_info=True)
        raise

def _validate_artifact_structure(self, artifact: Dict[str, Any], phase: str) -> None:
    """Validate that artifact structure is correct after update."""
    data = artifact.get('data', {})
    
    if phase == 'phase1':
        goals = data.get('goals')
        if not isinstance(goals, list):
            raise ValueError(
                f"Phase 1 artifact structure corrupted: goals is {type(goals)}, expected list"
            )
        # Validate each goal has required fields
        for i, goal in enumerate(goals):
            if not isinstance(goal, dict):
                raise ValueError(f"Phase 1 goal {i} is not a dict: {type(goal)}")
            if 'goal_text' not in goal:
                raise ValueError(f"Phase 1 goal {i} missing 'goal_text' field")
    
    elif phase == 'phase2':
        plan = data.get('plan')
        if not isinstance(plan, list):
            raise ValueError(
                f"Phase 2 artifact structure corrupted: plan is {type(plan)}, expected list"
            )
        # Validate each step has required fields
        for i, step in enumerate(plan):
            if not isinstance(step, dict):
                raise ValueError(f"Phase 2 step {i} is not a dict: {type(step)}")
            if 'goal' not in step:
                raise ValueError(f"Phase 2 step {i} missing 'goal' field")
    
    # Additional validation can be added for other phases
```

**Rationale**: Uses field-level updates when metadata available, validates structure

#### Step 2.8: Update Frontend to Send Metadata

**File**: `client/src/hooks/useEditorChat.ts`

**Changes**:
```typescript
const applyChanges = useCallback(async (
  selectedRange: { start: number; end: number },
  replacementText: string
) => {
  try {
    // Get selection with metadata
    const selection = getTextSelection() // This now includes metadata
    
    const request: EditorApplyRequest = {
      batch_id: batchId,
      phase,
      step_id: stepId || null,
      selected_range: selectedRange,
      replacement_text: replacementText,
      // NEW: Include metadata
      item_id: selection?.itemId,
      item_index: selection?.itemIndex,
      field_name: selection?.fieldName,
      field_path: selection?.fieldPath
    }

    const response = await apiService.applyEditorChanges(request)
    // ... rest of existing logic
  } catch (error) {
    // ... error handling
  }
}, [batchId, phase, stepId, onApplySuccess, onError])
```

**Rationale**: Sends metadata to backend

---

### Phase 3: Enhanced Phase 3 Support

#### Step 3.1: Add Phase 3 Metadata Extraction

**File**: `client/src/components/phase3/Phase3StepContent.tsx`

**Changes**:
```typescript
// Add data attributes to step content elements
<div
  ref={containerRef}
  data-step-id={stepId}
  data-phase="phase3"
  className="space-y-6"
>
  {content.summary && (
    <div className={baseSectionClass}>
      <h4>摘要</h4>
      <div
        data-field-name="summary"
        data-step-id={stepId}
        className="text-neutral-700"
      >
        <ReactMarkdown>{content.summary}</ReactMarkdown>
      </div>
    </div>
  )}
  
  {/* Similar for other fields: article, insights, etc. */}
</div>
```

**Rationale**: Adds metadata for Phase 3 step content

#### Step 3.2: Handle Structured Phase 3 Content

**File**: `backend/app/services/editor_service.py`

**Changes**:
```python
def _get_phase3_step_field_path(
    self,
    step_id: str,
    field_name: str
) -> List[Union[str, int]]:
    """Get field path for Phase 3 step content."""
    return [f"phase3_step_{step_id}", field_name]

def _extract_field_from_artifact(
    self,
    artifact: Dict[str, Any],
    field_path: List[Union[str, int]],
    phase: str
) -> Optional[str]:
    """Extract specific field value from artifact using field path."""
    # For Phase 3 step artifacts, field_path might be ['phase3_step_1', 'summary']
    # But artifact key is 'phase3_step_1', so we need to handle this
    
    if phase == 'phase3' and len(field_path) >= 2:
        # Check if first segment is phase key
        phase_key = field_path[0]
        if isinstance(phase_key, str) and phase_key.startswith('phase3_step_'):
            # This is a step artifact, load it separately
            session = self._load_session(...)  # Need session context
            step_artifact = session.get_phase_artifact(phase_key, {})
            if step_artifact:
                # Continue with remaining path
                remaining_path = field_path[1:]
                return self._extract_field_from_artifact(
                    step_artifact, remaining_path, phase
                )
    
    # Existing logic for other cases
    # ...
```

**Rationale**: Handles Phase 3 step artifact structure

---

### Phase 4: Phase 4 Markdown Handling

#### Step 4.1: Markdown-Aware Position Mapping

**File**: `client/src/utils/textSelection.ts`

**Changes**:
```typescript
export function getTextSelection(): TextSelection | null {
  // ... existing selection logic ...
  
  // NEW: For Phase 4, check if content is markdown
  if (phase === 'phase4') {
    // Get the raw markdown content from element
    const rawMarkdown = contentContainer.getAttribute('data-markdown-content')
    if (rawMarkdown) {
      // Map rendered position to markdown position
      const markdownPosition = mapRenderedToMarkdown(
        rawMarkdown,
        renderedText,
        start,
        end
      )
      
      return {
        text: selectedText,
        start: markdownPosition.start,
        end: markdownPosition.end,
        phase: 'phase4',
        element: contentContainer,
        markdownSource: rawMarkdown  // Store for reference
      }
    }
  }
  
  // ... rest of existing logic ...
}

function mapRenderedToMarkdown(
  markdown: string,
  rendered: string,
  renderedStart: number,
  renderedEnd: number
): { start: number; end: number } {
  // Simple approach: Find selected text in markdown
  // More sophisticated: Use markdown parser to map positions
  
  const selectedText = rendered.substring(renderedStart, renderedEnd)
  
  // Find position in markdown (accounting for markdown syntax)
  const markdownIndex = markdown.indexOf(selectedText)
  if (markdownIndex !== -1) {
    return {
      start: markdownIndex,
      end: markdownIndex + selectedText.length
    }
  }
  
  // Fallback: Use rendered positions (may be inaccurate)
  return { start: renderedStart, end: renderedEnd }
}
```

**Rationale**: Maps rendered positions to markdown positions

#### Step 4.2: Store Markdown Source

**File**: `client/src/pages/FinalReportPage.tsx`

**Changes**:
```typescript
<div
  ref={reportContentRef}
  data-markdown-content={finalReport?.content}
  className="prose max-w-none"
>
  <ReactMarkdown>{finalReport?.content}</ReactMarkdown>
</div>
```

**Rationale**: Stores markdown source for position mapping

---

### Phase 5: Testing & Refinement

#### Step 5.1: Unit Tests

**Files**: `backend/tests/test_editor_service.py` (new)

**Test Cases**:
```python
def test_extract_field_from_artifact_phase1():
    """Test extracting goal_text from Phase 1 artifact."""
    artifact = {
        'data': {
            'goals': [
                {'id': 1, 'goal_text': 'Test goal', 'rationale': '...'}
            ]
        }
    }
    field_path = ['goals', 0, 'goal_text']
    result = editor_service._extract_field_from_artifact(artifact, field_path, 'phase1')
    assert result == 'Test goal'

def test_update_field_in_artifact_phase1():
    """Test updating goal_text in Phase 1 artifact."""
    artifact = {
        'data': {
            'goals': [
                {'id': 1, 'goal_text': 'Old goal', 'rationale': '...'}
            ]
        }
    }
    field_path = ['goals', 0, 'goal_text']
    updated = editor_service._update_field_in_artifact(
        artifact, field_path, 'New goal', 'phase1'
    )
    assert updated['data']['goals'][0]['goal_text'] == 'New goal'
    assert isinstance(updated['data']['goals'], list)  # Structure preserved

def test_validate_artifact_structure_phase1():
    """Test structure validation for Phase 1."""
    valid_artifact = {
        'data': {
            'goals': [{'id': 1, 'goal_text': '...'}]
        }
    }
    editor_service._validate_artifact_structure(valid_artifact, 'phase1')  # Should not raise
    
    invalid_artifact = {
        'data': {
            'goals': 'not a list'  # Corrupted
        }
    }
    with pytest.raises(ValueError):
        editor_service._validate_artifact_structure(invalid_artifact, 'phase1')
```

**Rationale**: Ensures field-level updates work correctly

#### Step 5.2: Integration Tests

**Test Cases**:
```python
async def test_phase1_goal_editing_full_flow():
    """Test full flow: select → edit → save → verify."""
    # 1. Create test session with Phase 1 artifact
    # 2. Make API request with metadata
    # 3. Verify artifact is updated correctly
    # 4. Verify structure is preserved
    # 5. Verify future phases can load edited content
```

**Rationale**: Tests end-to-end functionality

#### Step 5.3: Manual Testing Checklist

**Phase 1 Testing**:
- [ ] Select goal text → Edit → Verify goal updated
- [ ] Select rationale → Edit → Verify rationale updated
- [ ] Verify goals array structure preserved
- [ ] Verify Phase 2 can load edited goals

**Phase 2 Testing**:
- [ ] Select step goal → Edit → Verify step updated
- [ ] Verify plan array structure preserved
- [ ] Verify Phase 3 can load edited plan

**Phase 3 Testing**:
- [ ] Select summary → Edit → Verify summary updated
- [ ] Select article → Edit → Verify article updated
- [ ] Verify step content structure preserved

**Phase 4 Testing**:
- [ ] Select text → Edit → Verify report updated
- [ ] Test with markdown formatting
- [ ] Verify markdown syntax preserved

---

## Testing Strategy

### Unit Tests

**Coverage Targets**:
- `_extract_field_from_artifact`: 100% coverage
- `_update_field_in_artifact`: 100% coverage
- `_validate_artifact_structure`: 100% coverage
- `extractSelectionMetadata`: 100% coverage

### Integration Tests

**Test Scenarios**:
1. Phase 1 goal editing → Phase 2 uses edited goal
2. Phase 2 plan editing → Phase 3 uses edited plan
3. Phase 3 step editing → Step content updated
4. Phase 4 report editing → Report updated

### Manual Testing

**Test Matrix**:
| Phase | Field | Expected Result | Status |
|-------|-------|----------------|--------|
| Phase 1 | goal_text | Updated, structure preserved | ⬜ |
| Phase 1 | rationale | Updated, structure preserved | ⬜ |
| Phase 2 | goal | Updated, structure preserved | ⬜ |
| Phase 3 | summary | Updated | ⬜ |
| Phase 3 | article | Updated | ⬜ |
| Phase 4 | content | Updated, markdown preserved | ⬜ |

---

## Rollback Plan

### Immediate Rollback (If Critical Issues Found)

1. **Disable Feature Flags**:
   ```python
   self.feature_flags = {
       'phase1_editing_enabled': False,
       'phase2_editing_enabled': False,
       'phase3_editing_enabled': False,
       'phase4_editing_enabled': False,
   }
   ```

2. **Revert Code Changes**:
   - Git revert to previous commit
   - Or comment out new code paths

3. **Data Recovery**:
   - Restore from backup if data corrupted
   - Or manually fix corrupted artifacts

### Gradual Rollback (If Issues in Specific Phases)

1. **Disable Specific Phase**:
   ```python
   self.feature_flags['phase1_editing_enabled'] = False
   ```

2. **Keep Other Phases Enabled**:
   - Phase 4 editing can remain enabled if working

---

## Risk Assessment

### High Risk Areas

1. **Data Corruption** (Phase 1/2)
   - **Mitigation**: Validation before update, structure checks
   - **Rollback**: Feature flags, data backups

2. **Position Mapping Errors** (Phase 4)
   - **Mitigation**: Markdown-aware mapping, fallback logic
   - **Rollback**: Disable Phase 4 editing if issues

3. **Metadata Extraction Failures**
   - **Mitigation**: Fallback to string-based editing, error handling
   - **Rollback**: Graceful degradation

### Medium Risk Areas

1. **Performance Impact**
   - **Mitigation**: Efficient field extraction, caching
   - **Monitoring**: Track API response times

2. **Edge Cases**
   - **Mitigation**: Comprehensive testing, error handling
   - **Monitoring**: Log errors, track failures

---

## Success Criteria

### Phase 1 Success Criteria

- ✅ Validation prevents data corruption
- ✅ Error messages are user-friendly
- ✅ Feature flags work correctly
- ✅ No data corruption incidents

### Phase 2 Success Criteria

- ✅ Phase 1 goal editing works correctly
- ✅ Phase 2 plan editing works correctly
- ✅ Data structure is preserved
- ✅ Future phases can use edited content
- ✅ All unit tests pass

### Phase 3 Success Criteria

- ✅ Phase 3 step content editing works
- ✅ Structured fields (summary, article, etc.) can be edited
- ✅ Content extraction is accurate

### Phase 4 Success Criteria

- ✅ Phase 4 report editing works
- ✅ Markdown formatting is preserved
- ✅ Position mapping is accurate

### Overall Success Criteria

- ✅ All phases can be edited without data corruption
- ✅ Data structure is always preserved
- ✅ User experience is smooth
- ✅ Performance is acceptable (< 2s for updates)
- ✅ Comprehensive test coverage (> 80%)

---

## Timeline

### Week 1: Phase 1 (Safety) + Phase 2 Start
- Days 1-2: Phase 1 implementation
- Days 3-5: Phase 2 frontend changes
- Days 6-7: Phase 2 backend changes

### Week 2: Phase 2 Completion + Phase 3
- Days 1-3: Phase 2 testing & refinement
- Days 4-7: Phase 3 implementation

### Week 3: Phase 4 + Phase 5 Start
- Days 1-3: Phase 4 implementation
- Days 4-5: Phase 5 unit tests
- Days 6-7: Phase 5 integration tests

### Week 4: Phase 5 Completion
- Days 1-3: Manual testing
- Days 4-5: Bug fixes & refinement
- Days 6-7: Documentation & deployment

---

## Appendix: Code File Changes Summary

### Frontend Files to Modify

1. `client/src/types/editor.ts` - Add metadata to interfaces
2. `client/src/utils/textSelection.ts` - Extract metadata from DOM
3. `client/src/components/research/ResearchGoalList.tsx` - Add data attributes
4. `client/src/components/phase3/Phase3StepContent.tsx` - Add data attributes
5. `client/src/hooks/useEditorChat.ts` - Send metadata in requests
6. `client/src/pages/FinalReportPage.tsx` - Store markdown source

### Backend Files to Modify

1. `backend/app/services/editor_service.py` - Field-level updates, validation
2. `backend/app/routes/research.py` - Error handling, metadata support
3. `research/prompts/editor/system.md` - Enhanced AI prompt

### New Files to Create

1. `backend/tests/test_editor_service.py` - Unit tests
2. `backend/tests/test_editor_integration.py` - Integration tests

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-20  
**Next Review**: After Phase 1 completion


