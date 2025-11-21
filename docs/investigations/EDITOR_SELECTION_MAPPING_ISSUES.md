# Editor Selection Mapping Investigation

## Overview
This document investigates how the system maps user text selections to session.json artifacts and identifies potential issues in the mapping and replacement logic.

## Current Flow

### 1. Frontend Selection Capture (`textSelection.ts`)

**Process:**
1. User selects text in DOM
2. `getTextSelection()` finds the container element (walks up DOM tree looking for `.stream-content-text`, `.prose`, etc.)
3. Calculates `start` and `end` positions using:
   ```typescript
   const containerText = contentContainer.textContent || ''
   const preRange = range.cloneRange()
   preRange.selectNodeContents(contentContainer)
   preRange.setEnd(range.startContainer, range.startOffset)
   const start = preRange.toString().length
   const end = start + selectedText.length
   ```
4. Returns `{ text, start, end, phase, element }`

**Key Issue #1: Position Calculation Assumes Flat Text**
- Positions are calculated relative to `textContent` of a DOM element
- This assumes the content is a single flat string
- But session.json artifacts are **structured data** (objects, arrays, nested structures)

### 2. Backend Content Extraction (`editor_service.py`)

**Process:**
```python
def _extract_content_from_artifact(self, artifact: Dict[str, Any], phase: str) -> str:
    data = artifact.get('data', artifact)
    
    if phase == 'phase1':
        return data.get('goals', data.get('content', data.get('output', '')))
    elif phase == 'phase2':
        return data.get('plan', data.get('questions', data.get('content', '')))
    # ...
```

**Key Issue #2: Type Mismatch - Arrays vs Strings**

**Phase 1 Artifact Structure** (from `research/agent.py:328-333`):
```python
artifact = {
    "phase1_result": phase1_result,
    "goals": goals,  # ← This is a LIST of goal objects!
    "post_phase1_feedback": post_phase1_feedback or "",
}
```

Each goal object has structure:
```python
{
    "id": 1,
    "goal_text": "研究目标文本",
    "uses": ["transcript"],
    "rationale": "背景说明",
    "status": "ready"
}
```

**Problem:**
- `_extract_content_from_artifact` tries to get `data.get('goals')` which returns a **list**, not a string
- When it tries to do `data.get('goals', ...)`, it gets a list, but the function expects a string
- Python's `dict.get()` returns the list directly, which then gets converted to string representation (e.g., `"[{...}, {...}]"`)
- This string representation **does not match** the rendered text in the frontend

**Phase 2 Artifact Structure** (from `research/agent.py:391-396`):
```python
artifact = {
    "phase2_result": phase2_result,
    "synthesized_goal": synthesized,
    "plan": plan,  # ← This is a LIST of step objects!
}
```

**Phase 3 Artifact Structure:**
- Main artifact: `phase3` with `phase3_result.plan` (list of steps)
- Step artifacts: `phase3_step_{step_id}` with step-specific content
- Step content is likely structured (summary, keyClaims, article, analysis, etc.)

**Phase 4 Artifact Structure:**
- Should be a single string (report content), which is the simplest case

### 3. Content Update Logic (`_update_content_in_artifact`)

**Process:**
```python
current_content = self._extract_content_from_artifact(artifact, phase)
# Replace selected range
start = selected_range['start']
end = selected_range['end']
updated_content = current_content[:start] + replacement_text + current_content[end:]
```

**Key Issue #3: String Replacement on Structured Data**

**For Phase 1:**
- `current_content` might be a string representation of a list: `"[{...}, {...}]"`
- User selects text like "研究目标文本" from the rendered UI
- The `start`/`end` positions are relative to the **rendered text** (formatted, human-readable)
- But `current_content` is the **JSON string representation** (with brackets, quotes, etc.)
- **Position mismatch**: `start=10` in rendered text ≠ `start=10` in JSON string

**Example:**
- Rendered text: `"1. 研究目标文本\n2. 另一个目标"`
- JSON string: `"[{\"id\":1,\"goal_text\":\"研究目标文本\",...},{\"id\":2,...}]"`
- User selects "研究目标文本" at position 3-9 in rendered text
- System tries to replace at position 3-9 in JSON string → **Wrong location!**

**For Phase 2:**
- Similar issue with `plan` array

**For Phase 3:**
- Step content might be structured (summary, keyClaims, article, analysis)
- User might select text from "summary" section
- But `_extract_content_from_artifact` might return concatenated content or wrong field
- Position mismatch again

### 4. AI Output Format

**System Prompt** (`research/prompts/editor/system.md`):
```
输出格式：
- 如果是修改请求：直接输出修改后的文本
- 如果是问题：直接回答问题
```

**Key Issue #4: No Format Specification for Structured Data**

**Problem:**
- AI is told to "直接输出修改后的文本" (directly output modified text)
- But for Phase 1 goals, the artifact is a **list of objects**
- AI doesn't know:
  1. Should it output just the modified goal text?
  2. Should it output the entire goals array?
  3. Should it output in JSON format?
  4. Should it output in the same format as displayed?

**Example Scenario:**
- User selects goal text: "研究目标文本"
- User asks: "改为：新的研究目标"
- AI outputs: "新的研究目标" (just the text)
- System tries to replace in JSON: `[{"goal_text": "研究目标文本", ...}]`
- But where exactly? Which goal? How to update the object structure?

### 5. Position Mapping Problems

**Key Issue #5: No Bidirectional Mapping**

**Frontend → Backend:**
- Frontend: Rendered text positions (formatted, human-readable)
- Backend: Raw artifact content (structured JSON)
- **No conversion layer** between these two representations

**Missing Logic:**
1. **Rendering Logic**: How is artifact data rendered to DOM?
   - Phase 1: Goals array → formatted list
   - Phase 2: Plan array → formatted list
   - Phase 3: Step content object → formatted sections
   - Phase 4: Report string → markdown

2. **Reverse Mapping**: How to map rendered position back to artifact structure?
   - Need to know which goal/step/section the selection is in
   - Need to know the field within that structure
   - Need to calculate position within that specific field

## Specific Issues by Phase

### Phase 1 (Research Goals)

**Artifact Structure:**
```json
{
  "phase1_result": {...},
  "goals": [
    {"id": 1, "goal_text": "目标1", "rationale": "...", ...},
    {"id": 2, "goal_text": "目标2", "rationale": "...", ...}
  ]
}
```

**Rendered Format:**
- Likely: "1. 目标1\n背景说明...\n\n2. 目标2\n..."
- Or: Each goal in a card/list item

**Problems:**
1. `_extract_content_from_artifact` returns list as string representation
2. Position mismatch between rendered text and JSON string
3. AI output format unclear (just text? full object? JSON?)
4. No way to identify which goal was selected
5. No way to update specific goal object fields

### Phase 2 (Research Plan)

**Artifact Structure:**
```json
{
  "phase2_result": {...},
  "synthesized_goal": {...},
  "plan": [
    {"step_id": 1, "goal": "步骤目标", "required_data": "...", ...},
    {"step_id": 2, "goal": "步骤目标", ...}
  ]
}
```

**Problems:**
1. Similar to Phase 1 - array structure
2. Plan items have multiple fields (goal, required_data, etc.)
3. User might select just "goal" text, but system doesn't know which field

### Phase 3 (Step Content)

**Artifact Structure:**
```json
{
  "content": "...",  // or structured:
  "summary": "...",
  "keyClaims": [...],
  "article": "...",
  "analysis": {...}
}
```

**Problems:**
1. `_extract_content_from_artifact` tries `data.get('content')` first
2. But step content might be structured, not a single string
3. User might select from "summary" but system updates "content"
4. Position mismatch if content is concatenated

### Phase 4 (Final Report)

**Artifact Structure:**
```json
{
  "content": "完整的报告文本..."
}
```

**Status:** ✅ This is the simplest case - single string field
- Should work correctly if `_extract_content_from_artifact` returns `data.get('content')`
- Position mapping should work if rendered text matches stored content exactly

**Potential Issue:**
- If report is rendered with markdown formatting, positions might still mismatch
- E.g., `**bold**` in markdown vs `bold` in rendered text

## Root Causes

### 1. **Architectural Mismatch**
- Frontend assumes **flat text** representation
- Backend stores **structured data** (objects, arrays)
- No translation layer between these two representations

### 2. **Insufficient Context**
- System doesn't track:
  - Which specific item in an array was selected
  - Which field within an object was selected
  - How the artifact was rendered to create the DOM

### 3. **Ambiguous AI Instructions**
- System prompt doesn't specify output format for structured data
- AI doesn't know whether to output just text or full structure

### 4. **Position Calculation Assumptions**
- Assumes 1:1 mapping between rendered text and stored content
- Doesn't account for:
  - Formatting (markdown, HTML)
  - Structure (arrays, objects)
  - Rendering transformations

## Potential Solutions (Not Implemented)

### Solution 1: Add Selection Metadata
- Track which array item/object field was selected
- Store selection context (goal_id, step_id, field_name)
- Use this to directly update the correct part of the structure

### Solution 2: Bidirectional Mapping
- Create rendering functions that convert artifact → DOM
- Create reverse mapping functions that convert DOM position → artifact path
- Use JSONPath or similar to identify exact location in structure

### Solution 3: Structured AI Output
- Update system prompt to specify output format based on phase
- For arrays: Output JSON for the specific item
- For objects: Output JSON for the specific field
- Parse AI output and update structure directly

### Solution 4: Field-Specific Editing
- Instead of text range replacement, use field-level updates
- Identify which field was selected (goal_text, summary, etc.)
- Replace entire field value, not substring

### Solution 5: Content Normalization
- Store both structured data AND rendered text representation
- Use rendered text for selection matching
- Use structured data for updates
- Keep them in sync

## Recommendations

1. **Immediate Fix**: Add validation and error handling
   - Detect when content extraction returns wrong type
   - Log warnings when position mapping seems incorrect
   - Fallback to field-level updates when string replacement fails

2. **Short-term Fix**: Improve content extraction
   - Handle array structures properly (convert to formatted string)
   - Track which item/field was selected
   - Use field-level updates for structured data

3. **Long-term Fix**: Redesign selection system
   - Add selection metadata (item_id, field_name)
   - Implement bidirectional mapping
   - Support structured editing (not just text replacement)

4. **Testing**: Add test cases for each phase
   - Test selection in Phase 1 goals array
   - Test selection in Phase 2 plan array
   - Test selection in Phase 3 structured content
   - Test selection in Phase 4 report string
   - Verify position mapping accuracy

## Current Risk Assessment

**High Risk:**
- Phase 1 goal editing: Will likely fail or corrupt data
- Phase 2 plan editing: Will likely fail or corrupt data
- Phase 3 step content editing: May work for simple cases, fail for structured content

**Medium Risk:**
- Phase 4 report editing: Should work but may have position mismatches with markdown

**Low Risk:**
- Simple text replacement in single-string fields

## Conclusion

The current implementation has a fundamental architectural mismatch between:
- Frontend: Flat text selection with position indices
- Backend: Structured data (objects, arrays) in session.json

This mismatch causes:
1. Position calculation errors
2. Content extraction failures
3. Incorrect updates to structured data
4. Potential data corruption

The system needs significant redesign to properly handle structured data editing, or it should be limited to simple string fields only.



