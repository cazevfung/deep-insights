# Editor Selection to JSON Mapping - Detailed Investigation

**Status**: 🔴 Critical Issues Identified - Implementation Not Production Ready

**Created**: 2025-11-20  
**Related Files**: 
- `client/src/utils/textSelection.ts`
- `backend/app/services/editor_service.py`
- `client/src/components/research/ResearchGoalList.tsx`
- `client/src/components/phase3/Phase3StepContent.tsx`
- `research/session.py`
- `research/agent.py`

**Related Investigations**:
- `EDITOR_SELECTION_MAPPING_ISSUES.md` - Initial analysis
- `EDITOR_PHASE3_RERUN_LOGIC_ANALYSIS.md` - Phase 3 rerun issues

---

## Executive Summary

The AI Content Editor feature has a **fundamental architectural mismatch** between how text selections are captured in the frontend (flat text with position indices) and how content is stored in session.json (structured data: objects, arrays, nested fields). This mismatch causes:

1. **Position calculation failures** - Frontend positions don't map to backend JSON structure
2. **Content extraction errors** - Arrays/objects treated as strings
3. **Data corruption risks** - String replacement on structured data
4. **AI output format ambiguity** - No specification for structured data editing

**Impact**: Phase 1 and Phase 2 editing will likely fail or corrupt data. Phase 3 may work for simple cases. Phase 4 should work but may have markdown formatting issues.

---

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Frontend Selection Capture](#frontend-selection-capture)
3. [Backend Content Extraction](#backend-content-extraction)
4. [Content Update Logic](#content-update-logic)
5. [AI Output Format](#ai-output-format)
6. [Phase-by-Phase Analysis](#phase-by-phase-analysis)
7. [Root Cause Analysis](#root-cause-analysis)
8. [Failure Scenarios](#failure-scenarios)
9. [Potential Solutions](#potential-solutions)
10. [Recommendations](#recommendations)

---

## System Architecture Overview

### Data Flow Diagram

```
User Selection (DOM)
    ↓
Frontend: getTextSelection()
    ↓
{ text: "研究目标文本", start: 3, end: 9, phase: "phase1" }
    ↓
API Request: EditorApplyRequest
    ↓
Backend: EditorService.apply_changes()
    ↓
Load Artifact from session.json
    ↓
Extract Content (PROBLEM: Array → String conversion)
    ↓
String Replacement (PROBLEM: Position mismatch)
    ↓
Save Artifact (PROBLEM: May corrupt structure)
```

### Key Components

1. **Frontend Selection** (`textSelection.ts`)
   - Captures DOM text selection
   - Calculates character positions
   - Returns flat text representation

2. **Backend Service** (`editor_service.py`)
   - Loads structured artifacts from session.json
   - Extracts content (attempts to convert structure → string)
   - Performs string replacement
   - Saves updated artifact

3. **Session Storage** (`session.py`)
   - Stores artifacts as structured JSON
   - Phase artifacts are objects/arrays, not strings

---

## Frontend Selection Capture

### Implementation (`textSelection.ts`)

```typescript
export function getTextSelection(): TextSelection | null {
  const selection = window.getSelection()
  const range = selection.getRangeAt(0)
  const selectedText = selection.toString().trim()
  
  // Find container element
  let contentContainer = container as HTMLElement
  // Walk up DOM tree to find content container
  
  // Calculate positions relative to container's textContent
  const containerText = contentContainer.textContent || ''
  const preRange = range.cloneRange()
  preRange.selectNodeContents(contentContainer)
  preRange.setEnd(range.startContainer, range.startOffset)
  const start = preRange.toString().length
  const end = start + selectedText.length
  
  return {
    text: selectedText,
    start,  // ← Position in rendered text
    end,    // ← Position in rendered text
    phase: 'phase1',
    element: contentContainer
  }
}
```

### Assumptions Made

✅ **Correct Assumptions**:
- User selects text from rendered DOM
- `textContent` provides flat text representation
- Positions are relative to container element

❌ **Problematic Assumptions**:
- Assumes content is a **single flat string**
- Assumes rendered text **exactly matches** stored content
- Assumes 1:1 character mapping between DOM and JSON

### Example: Phase 1 Goal Selection

**Rendered DOM** (from `ResearchGoalList.tsx`):
```html
<h5>研究目标文本</h5>
<p>背景说明...</p>
```

**User selects**: "研究目标文本"  
**Frontend calculates**: `start=0, end=6` (relative to `<h5>` element's textContent)

**But stored in session.json**:
```json
{
  "goals": [
    {
      "id": 1,
      "goal_text": "研究目标文本",
      "rationale": "背景说明...",
      "uses": ["transcript"]
    }
  ]
}
```

**Problem**: Position `start=0, end=6` in rendered text ≠ position in JSON string representation

---

## Backend Content Extraction

### Implementation (`editor_service.py`)

```python
def _extract_content_from_artifact(self, artifact: Dict[str, Any], phase: str) -> str:
    """Extract content string from phase artifact."""
    data = artifact.get('data', artifact) if isinstance(artifact, dict) else {}
    
    if phase == 'phase1':
        # Try different possible keys
        if isinstance(data, dict):
            return data.get('goals', data.get('content', data.get('output', '')))
        return str(data) if data else ''
    # ... similar for other phases
```

### Actual Artifact Structures

#### Phase 1 Artifact (from `research/agent.py:328-333`)

**Saved Structure**:
```python
artifact = {
    "phase1_result": {
        "suggested_goals": [...],
        "raw_response": {...}
    },
    "goals": [  # ← LIST of goal objects
        {
            "id": 1,
            "goal_text": "研究目标文本",
            "rationale": "背景说明",
            "uses": ["transcript"],
            "status": "ready"
        },
        {
            "id": 2,
            "goal_text": "另一个目标",
            "rationale": "...",
            "uses": ["transcript"],
            "status": "ready"
        }
    ],
    "post_phase1_feedback": ""
}
```

**What `_extract_content_from_artifact` returns**:
```python
data.get('goals')  # Returns: [{"id": 1, "goal_text": "..."}, ...]
# Python converts list to string: "[{'id': 1, 'goal_text': '研究目标文本', ...}, ...]"
```

**Problem**: 
- Returns Python string representation of list
- Format: `"[{'id': 1, 'goal_text': '研究目标文本', ...}]"`
- This does NOT match rendered text: `"1. 研究目标文本\n背景说明...\n\n2. 另一个目标\n..."`
- Character positions are completely different

#### Phase 2 Artifact (from `research/agent.py:391-396`)

**Saved Structure**:
```python
artifact = {
    "phase2_result": {...},
    "synthesized_goal": {
        "comprehensive_topic": "...",
        "unifying_theme": "..."
    },
    "plan": [  # ← LIST of step objects
        {
            "step_id": 1,
            "goal": "步骤目标",
            "required_data": "transcript",
            "data_sources": [...]
        },
        {
            "step_id": 2,
            "goal": "另一个步骤",
            "required_data": "transcript",
            "data_sources": [...]
        }
    ]
}
```

**What `_extract_content_from_artifact` returns**:
```python
data.get('plan')  # Returns: [{"step_id": 1, "goal": "..."}, ...]
# Python string: "[{'step_id': 1, 'goal': '步骤目标', ...}, ...]"
```

**Problem**: Same as Phase 1 - list converted to string representation

#### Phase 3 Artifact

**Main Artifact** (`phase3`):
```json
{
  "phase3_result": {
    "plan": [
      {"step_id": 1, "goal": "...", ...},
      {"step_id": 2, "goal": "...", ...}
    ],
    "findings": [...]
  }
}
```

**Step Artifacts** (`phase3_step_{step_id}`):
```json
{
  "content": "...",  // May be string OR structured object
  "summary": "...",
  "keyClaims": [...],
  "article": "...",
  "analysis": {
    "fiveWhys": [...],
    "assumptions": [...],
    "uncertainties": [...]
  }
}
```

**What `_extract_content_from_artifact` returns**:
- Tries `data.get('content')` first
- If structured, may return wrong field
- If content is concatenated, positions may be wrong

#### Phase 4 Artifact

**Saved Structure**:
```json
{
  "content": "完整的报告文本...\n\n## 章节1\n\n内容..."
}
```

**What `_extract_content_from_artifact` returns**:
```python
data.get('content')  # Returns: "完整的报告文本..."
```

**Status**: ✅ Should work correctly (single string field)

**Potential Issue**: If report is rendered with markdown formatting, positions might mismatch
- Stored: `"**bold** text"`
- Rendered: `"bold text"` (without markdown)
- Position `start=0, end=4` in rendered ≠ position in stored

---

## Content Update Logic

### Implementation (`editor_service.py`)

```python
def _update_content_in_artifact(
    self, 
    artifact: Dict[str, Any], 
    phase: str, 
    selected_range: Dict[str, int],
    replacement_text: str
) -> Dict[str, Any]:
    """Update artifact content with replacement text."""
    # Extract current content (PROBLEM: May return wrong type/format)
    current_content = self._extract_content_from_artifact(artifact, phase)
    
    # String replacement (PROBLEM: Position mismatch)
    start = selected_range['start']
    end = selected_range['end']
    updated_content = current_content[:start] + replacement_text + current_content[end:]
    
    # Update artifact structure
    data = artifact.get('data', {})
    if phase == 'phase1':
        if 'goals' in data:
            data['goals'] = updated_content  # ← PROBLEM: Assigning string to array field!
        else:
            data['content'] = updated_content
    # ... similar for other phases
    
    artifact['data'] = data
    return artifact
```

### Critical Issues

#### Issue 1: Type Mismatch

**For Phase 1**:
```python
# current_content is a string representation of list
current_content = "[{'id': 1, 'goal_text': '研究目标文本', ...}, ...]"

# User selected "研究目标文本" at position 3-9 in rendered text
# But in current_content, "研究目标文本" is at a different position
# String replacement happens at wrong location

# Then assigns string to array field:
data['goals'] = updated_content  # ← String assigned to array field!
```

**Result**: 
- `data['goals']` becomes a string instead of array
- JSON structure is corrupted
- Future phases that expect `goals` to be an array will fail

#### Issue 2: Position Mismatch

**Example Scenario**:

**Rendered Text** (what user sees):
```
1. 研究目标文本
   背景说明：这是一个重要的研究目标

2. 另一个目标
   背景说明：...
```

**User selects**: "研究目标文本"  
**Frontend calculates**: `start=3, end=9` (position in rendered text)

**Stored JSON String** (what backend extracts):
```python
"[{'id': 1, 'goal_text': '研究目标文本', 'rationale': '背景说明：这是一个重要的研究目标', ...}, {'id': 2, ...}]"
```

**Position in JSON string**:
- "研究目标文本" appears at position ~30-36 (inside JSON structure)
- Frontend position `start=3, end=9` is completely wrong

**String replacement**:
```python
updated_content = current_content[:3] + "新文本" + current_content[9:]
# Replaces characters at wrong position!
# Result: Corrupted JSON
```

#### Issue 3: Structure Loss

**Before**:
```json
{
  "goals": [
    {"id": 1, "goal_text": "研究目标文本", "rationale": "..."},
    {"id": 2, "goal_text": "另一个目标", "rationale": "..."}
  ]
}
```

**After string replacement** (if it somehow worked):
```json
{
  "goals": "[{'id': 1, 'goal_text': '新文本', ...}, ...]"  // ← String, not array!
}
```

**Result**: Structure is lost, data is corrupted

---

## AI Output Format

### Current System Prompt (`research/prompts/editor/system.md`)

```
你是一个专业的研究内容编辑助手。你的任务是帮助用户修改研究阶段输出的内容。

当用户选中一段文本并请求修改时，你需要：
1. 理解选中文本的上下文和含义
2. 根据用户的要求，提供精准的修改建议
3. 保持修改后的内容与整体研究目标的一致性
4. 如果用户只是提问，则回答问题而不修改内容

输出格式：
- 如果是修改请求：直接输出修改后的文本
- 如果是问题：直接回答问题
```

### Problems with Current Prompt

#### Problem 1: No Format Specification for Structured Data

**For Phase 1 Goals**:
- User selects: "研究目标文本"
- User asks: "改为：新的研究目标"
- AI outputs: "新的研究目标" (just the text)

**But system needs to know**:
- Which goal object to update? (goal #1, #2, ...)
- Should it update just `goal_text` or entire object?
- Should output be JSON format or plain text?

**Current behavior**: AI outputs plain text, system tries to do string replacement → fails

#### Problem 2: No Context About Data Structure

AI doesn't know:
- That `goals` is an array of objects
- That each goal has `id`, `goal_text`, `rationale`, `uses`, etc.
- That it should preserve the structure

**Result**: AI outputs simple text, system can't properly integrate it

#### Problem 3: Ambiguous Instructions

"直接输出修改后的文本" (directly output modified text) is ambiguous:
- Does it mean output just the selected portion?
- Or output the entire field?
- Or output the entire structure?

---

## Phase-by-Phase Analysis

### Phase 1: Research Goals

**Artifact Structure**:
```json
{
  "phase1_result": {...},
  "goals": [
    {"id": 1, "goal_text": "...", "rationale": "...", "uses": [...], "status": "ready"},
    {"id": 2, "goal_text": "...", "rationale": "...", "uses": [...], "status": "ready"}
  ],
  "post_phase1_feedback": ""
}
```

**Rendered Format** (from `ResearchGoalList.tsx`):
- Each goal rendered as `<li>` with:
  - Goal number badge
  - `<h5>` with `goal.goal_text`
  - `<p>` with `goal.rationale` (if present)
  - Status badge

**Selection Scenario**:
1. User selects text from goal #1's `goal_text`
2. Frontend: `{text: "研究目标文本", start: 3, end: 9, phase: "phase1"}`
3. Backend extracts: `"[{'id': 1, 'goal_text': '研究目标文本', ...}, ...]"` (string)
4. Position mismatch: `start=3` in rendered ≠ position in JSON string
5. String replacement fails or corrupts data
6. `data['goals']` becomes string instead of array

**Risk Level**: 🔴 **CRITICAL** - Will fail or corrupt data

**Failure Modes**:
- String assigned to array field → Type error in future phases
- Position mismatch → Wrong text replaced
- Structure loss → Data corruption

### Phase 2: Research Plan

**Artifact Structure**:
```json
{
  "phase2_result": {...},
  "synthesized_goal": {...},
  "plan": [
    {"step_id": 1, "goal": "步骤目标", "required_data": "...", "data_sources": [...]},
    {"step_id": 2, "goal": "另一个步骤", "required_data": "...", "data_sources": [...]}
  ]
}
```

**Rendered Format**:
- Plan items displayed as list/cards
- Each step shows: step_id, goal, required_data, etc.

**Selection Scenario**:
1. User selects text from step #1's `goal` field
2. Similar issues as Phase 1
3. `data['plan']` becomes string instead of array

**Risk Level**: 🔴 **CRITICAL** - Will fail or corrupt data

### Phase 3: Step Content

**Artifact Structure** (step artifact):
```json
{
  "content": "...",  // May be string OR structured
  "summary": "...",
  "keyClaims": [
    {"claim": "...", "supportingEvidence": "..."}
  ],
  "article": "...",
  "analysis": {
    "fiveWhys": [...],
    "assumptions": [...],
    "uncertainties": [...]
  }
}
```

**Rendered Format** (from `Phase3StepContent.tsx`):
- Summary section
- Key Claims section (list of claim objects)
- Article section
- Analysis section (Five Whys table, assumptions list, uncertainties list)

**Selection Scenario**:
1. User selects text from "summary" section
2. Backend extracts: `data.get('content')` (may be wrong field)
3. If content is structured, extraction may fail
4. Position mismatch if content is concatenated

**Risk Level**: 🟡 **MEDIUM** - May work for simple cases, fail for structured content

**Potential Issues**:
- Wrong field extracted (content vs summary vs article)
- Position mismatch if content is concatenated from multiple fields
- Structure loss if content is structured object

### Phase 4: Final Report

**Artifact Structure**:
```json
{
  "content": "完整的报告文本...\n\n## 章节1\n\n内容..."
}
```

**Rendered Format**:
- Markdown rendered to HTML
- Sections, headings, lists, etc.

**Selection Scenario**:
1. User selects text from rendered report
2. Backend extracts: `data.get('content')` (string)
3. String replacement should work

**Risk Level**: 🟢 **LOW** - Should work, but may have markdown formatting issues

**Potential Issues**:
- Markdown formatting: `**bold**` in stored vs `bold` in rendered
- Position mismatch if markdown is stripped during rendering
- Line breaks: `\n` in stored vs `<br>` in rendered

---

## Root Cause Analysis

### Primary Root Cause: Architectural Mismatch

**Frontend Assumption**: Content is flat text
- Selection positions are character indices in rendered text
- Assumes 1:1 mapping between DOM and data

**Backend Reality**: Content is structured data
- Artifacts are JSON objects/arrays
- No direct mapping between rendered text and JSON structure

**Gap**: No translation layer between these two representations

### Secondary Root Causes

1. **No Selection Context Tracking**
   - System doesn't track which array item was selected
   - System doesn't track which object field was selected
   - System doesn't know how artifact was rendered

2. **Type Coercion Issues**
   - Arrays converted to string representations
   - String representations don't match rendered text
   - Type information is lost

3. **Ambiguous AI Instructions**
   - No format specification for structured data
   - AI doesn't know output format
   - AI doesn't know which part of structure to update

4. **No Validation**
   - No check if extracted content type matches expected type
   - No validation of position ranges
   - No verification that replacement preserves structure

---

## Failure Scenarios

### Scenario 1: Phase 1 Goal Editing

**Steps**:
1. User selects "研究目标文本" from goal #1
2. Frontend: `{text: "研究目标文本", start: 3, end: 9, phase: "phase1"}`
3. Backend extracts: `"[{'id': 1, 'goal_text': '研究目标文本', ...}, ...]"` (string)
4. User asks AI: "改为：新的研究目标"
5. AI outputs: "新的研究目标"
6. Backend tries: `current_content[3:9] = "新的研究目标"`
7. Result: Replaces wrong characters in JSON string
8. Saves: `data['goals'] = corrupted_string`
9. Next phase loads: `goals` is string, not array → **TypeError**

**Impact**: Data corruption, system failure

### Scenario 2: Phase 2 Plan Editing

**Steps**:
1. User selects "步骤目标" from step #1
2. Similar to Scenario 1
3. `data['plan']` becomes string
4. Phase 3 tries to iterate over `plan` → **TypeError**

**Impact**: Phase 3 execution fails

### Scenario 3: Phase 3 Step Content Editing

**Steps**:
1. User selects text from "summary" section
2. Backend extracts `data.get('content')` (may be wrong field)
3. If content is structured object, extraction fails
4. String replacement on wrong field or fails

**Impact**: Content not updated correctly, or update fails silently

### Scenario 4: Phase 4 Report Editing (Markdown)

**Steps**:
1. User selects "bold text" from rendered report
2. Frontend: `start=0, end=9` (in rendered: "bold text")
3. Backend: stored content has `**bold** text` (markdown)
4. Position `start=0, end=9` in rendered ≠ position in stored
5. String replacement at wrong position

**Impact**: Markdown syntax corrupted, rendering fails

---

## Potential Solutions

### Solution 1: Add Selection Metadata (Recommended)

**Approach**: Track which array item/object field was selected

**Implementation**:
```typescript
interface TextSelection {
  text: string
  start: number
  end: number
  phase: string
  // NEW: Add context metadata
  itemId?: number | string      // For arrays: which item (goal_id, step_id)
  fieldName?: string            // For objects: which field (goal_text, summary)
  itemIndex?: number            // For arrays: index in array
}
```

**Frontend Changes**:
- When selecting from goal list, track `itemId` and `fieldName`
- Pass metadata to backend

**Backend Changes**:
- Use metadata to directly update correct field
- Skip string replacement, use field-level updates

**Pros**:
- Direct mapping to structure
- No position calculation needed
- Preserves data structure

**Cons**:
- Requires frontend changes to track metadata
- More complex selection logic

### Solution 2: Bidirectional Mapping

**Approach**: Create rendering functions and reverse mapping

**Implementation**:
```python
# Rendering function: artifact → formatted text
def render_artifact_to_text(artifact, phase):
    if phase == 'phase1':
        goals = artifact['data']['goals']
        return format_goals_as_text(goals)  # "1. goal1\n2. goal2\n..."
    
# Reverse mapping: DOM position → artifact path
def map_position_to_artifact_path(rendered_text, position, artifact, phase):
    # Find which goal/step/field contains this position
    return {
        'path': ['goals', 0, 'goal_text'],  # JSONPath-like
        'field_start': 0,
        'field_end': 10
    }
```

**Pros**:
- Handles any rendering format
- Accurate position mapping

**Cons**:
- Complex to implement
- Requires maintaining rendering logic
- Performance overhead

### Solution 3: Structured AI Output

**Approach**: Update system prompt to specify output format

**Implementation**:
```markdown
输出格式（根据阶段）：
- Phase 1: 输出完整的goal对象JSON: {"id": 1, "goal_text": "新文本", ...}
- Phase 2: 输出完整的step对象JSON: {"step_id": 1, "goal": "新文本", ...}
- Phase 3: 输出字段JSON: {"summary": "新文本"} 或 {"goal_text": "新文本"}
- Phase 4: 直接输出修改后的文本
```

**Backend Changes**:
- Parse AI output as JSON
- Update structure directly
- Validate JSON before saving

**Pros**:
- AI knows what to output
- Direct structure updates
- No position mapping needed

**Cons**:
- AI may output invalid JSON
- Requires JSON parsing and validation
- More complex prompt

### Solution 4: Field-Specific Editing

**Approach**: Replace entire field value, not substring

**Implementation**:
```python
def update_field_in_artifact(artifact, phase, item_id, field_name, new_value):
    if phase == 'phase1':
        goals = artifact['data']['goals']
        for goal in goals:
            if goal['id'] == item_id:
                goal[field_name] = new_value  # Replace entire field
                break
```

**Pros**:
- Simple and direct
- Preserves structure
- No position calculation

**Cons**:
- Requires identifying which field was selected
- User can't edit partial text within field

### Solution 5: Content Normalization

**Approach**: Store both structured data AND rendered text

**Implementation**:
```python
artifact = {
    "data": {
        "goals": [...],  # Structured data
        "goals_text": "1. goal1\n2. goal2\n..."  # Rendered text
    }
}
```

**Selection**: Use rendered text for matching
**Update**: Update structured data based on rendered text changes

**Pros**:
- Accurate position matching
- Preserves structure

**Cons**:
- Data duplication
- Sync issues between two representations
- Storage overhead

---

## Recommendations

### Immediate Actions (Before Production)

1. **Add Validation and Error Handling**
   ```python
   def _extract_content_from_artifact(self, artifact, phase):
       content = ...
       if isinstance(content, (list, dict)):
           logger.error(f"Content extraction returned {type(content)}, expected string")
           raise ValueError(f"Cannot edit structured data as string for {phase}")
       return content
   ```

2. **Add Type Checking**
   ```python
   def _update_content_in_artifact(self, artifact, phase, selected_range, replacement_text):
       data = artifact.get('data', {})
       if phase == 'phase1' and isinstance(data.get('goals'), list):
           raise ValueError("Cannot use string replacement on goals array. Use field-level update.")
   ```

3. **Limit to Simple Cases**
   - Disable editing for Phase 1 and Phase 2 (structured arrays)
   - Only enable for Phase 4 (single string)
   - Phase 3: Only allow editing if content is confirmed to be string

### Short-term Fixes (1-2 weeks)

1. **Implement Field-Level Updates**
   - Add selection metadata tracking
   - Update specific fields instead of string replacement
   - Test with Phase 1 goals and Phase 2 plan

2. **Improve Content Extraction**
   - Handle array structures properly
   - Convert to formatted string that matches rendering
   - Track which item/field was selected

3. **Update AI Prompt**
   - Specify output format for each phase
   - Add examples for structured data
   - Include JSON schema if needed

### Long-term Redesign (1-2 months)

1. **Redesign Selection System**
   - Add comprehensive selection metadata
   - Implement bidirectional mapping
   - Support structured editing (not just text replacement)

2. **Add Rendering Layer**
   - Centralized rendering functions
   - Reverse mapping from DOM to structure
   - Version control for rendering logic

3. **Comprehensive Testing**
   - Test cases for each phase
   - Test position mapping accuracy
   - Test data structure preservation
   - Test edge cases (empty arrays, nested structures, etc.)

### Testing Strategy

1. **Unit Tests**
   - Test `_extract_content_from_artifact` for each phase
   - Test `_update_content_in_artifact` with various structures
   - Test position mapping accuracy

2. **Integration Tests**
   - Test full flow: selection → AI → update → save
   - Test data structure preservation
   - Test error handling

3. **Manual Testing**
   - Test editing in each phase
   - Verify data integrity after edits
   - Check that future phases can use edited data

---

## Conclusion

The current implementation has a **fundamental architectural mismatch** that makes it unsuitable for production use, especially for Phase 1 and Phase 2 editing. The system needs significant redesign to properly handle structured data editing.

**Priority Actions**:
1. 🔴 **CRITICAL**: Add validation to prevent data corruption
2. 🟡 **HIGH**: Implement field-level updates for Phase 1/2
3. 🟢 **MEDIUM**: Improve AI prompt for structured data
4. 🔵 **LOW**: Long-term redesign of selection system

**Risk Assessment**:
- **Phase 1/2 Editing**: 🔴 **DO NOT USE** - Will corrupt data
- **Phase 3 Editing**: 🟡 **USE WITH CAUTION** - May work for simple cases
- **Phase 4 Editing**: 🟢 **SAFE TO USE** - Should work, test markdown formatting

---

## Appendix: Code References

### Frontend
- `client/src/utils/textSelection.ts` - Selection capture
- `client/src/components/research/ResearchGoalList.tsx` - Phase 1 rendering
- `client/src/components/phase3/Phase3StepContent.tsx` - Phase 3 rendering
- `client/src/hooks/useEditorChat.ts` - Editor chat logic

### Backend
- `backend/app/services/editor_service.py` - Core editing logic
- `backend/app/routes/research.py` - API endpoints
- `research/session.py` - Session management
- `research/agent.py` - Artifact creation (lines 328-333, 391-396)

### Prompts
- `research/prompts/editor/system.md` - AI system prompt

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-20  
**Next Review**: After implementing fixes


