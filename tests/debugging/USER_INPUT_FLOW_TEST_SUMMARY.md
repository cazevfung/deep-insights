# User Input Flow Test: Phase 1 → Phase 2

## Overview

This test verifies that user input collected at the end of Phase 1 is correctly passed to Phase 2 and included in the AI prompt for generating the synthesized research goal.

## Test Location

`tests/test_phase1_to_phase2_user_input.py`

## What the Test Verifies

1. **User Input Collection**: User input provided at the end of Phase 1 is captured correctly
2. **Parameter Passing**: User input is passed as the `user_input` parameter to Phase 2's `execute()` method
3. **Prompt Inclusion**: User input is included in the prompt sent to the AI in Phase 2
4. **Prompt Format**: User input appears in the correct format (`**用户补充说明：**`) in the prompt
5. **AI Consideration**: The AI response reflects that user input was considered (in this test, via a marker in the response)

## Test Flow

```
Phase 1: Generate research goals
    ↓
User provides input: "请重点关注技术实现细节和性能优化方面"
    ↓
Phase 2: Synthesize goals (with user_input parameter)
    ↓
Check: Is user input in the Phase 2 prompt?
```

## Test Implementation Details

### Mock Client
- **MockQwenClient**: Captures all API messages and returns minimal responses
- Stores messages in `captured_messages` list for inspection
- Returns minimal token usage (~30-50 tokens per call)

### Mock UI
- **MockUI**: Simulates user input via `prompt_user()` method
- Returns predefined test input: `"请重点关注技术实现细节和性能优化方面"`

### Verification Steps

1. **Capture Phase 2 API Call**: Verify that Phase 2 made an API call
2. **Extract Prompt**: Get the full prompt text from Phase 2's API call
3. **Check User Input Text**: Verify the exact user input text appears in the prompt
4. **Check User Context Marker**: Verify `**用户补充说明：**` marker is present
5. **Extract User Context Section**: Extract the user context section and verify it matches input
6. **Check AI Response**: Verify AI response reflects user input consideration

## Expected Results

### Test 1: With User Input ✅

**Expected:**
- Phase 2 API call is captured
- User input text appears in prompt: `"请重点关注技术实现细节和性能优化方面"`
- User context marker appears: `**用户补充说明：**`
- Extracted user input matches test input exactly

**Test Passes If:**
- `user_input_in_prompt == True`
- `user_context_marker_in_prompt == True`

### Test 2: Without User Input ✅

**Expected:**
- Phase 2 API call is captured
- User context marker is NOT present when `user_input=None`

**Test Passes If:**
- Phase 2 completes successfully
- User context marker is absent (or present but empty, which is acceptable)

## Code Path Verification

### Phase 2 Code Flow

1. **Phase 2 Execute** (`research/phases/phase2_synthesize.py:12-127`)
   ```python
   def execute(
       self,
       phase1_output: Dict[str, Any],
       data_abstract: str,
       user_input: Optional[str] = None,  # ← User input parameter
       user_topic: Optional[str] = None
   )
   ```

2. **Format User Context** (`research/phases/phase2_synthesize.py:58-63`)
   ```python
   user_context_section = ""
   if user_topic:
       user_context_section += f"**用户研究主题：**\n{user_topic}\n\n"
   if user_input:
       user_context_section += f"**用户补充说明：**\n{user_input}\n\n"  # ← Formats user input
   ```

3. **Compose Messages** (`research/phases/phase2_synthesize.py:66-72`)
   ```python
   context = {
       "goals_list": goals_list,
       "goals_count": len(all_goals),
       "data_abstract": data_abstract,
       "user_context": user_context_section.strip() if user_context_section else "",  # ← Passes to prompt
   }
   messages = compose_messages("phase2_synthesize", context=context)
   ```

4. **Prompt Template** (`research/prompts/phase2_synthesize/instructions.md:8`)
   ```
   {user_context}  # ← Template placeholder for user context
   ```

5. **Agent Orchestration** (`research/agent.py:259-264`)
   ```python
   phase2_result = phase2.execute(
       phase1_result, 
       combined_abstract,
       user_input=amend if amend else None,  # ← Passes user input from Phase 1
       user_topic=user_topic
   )
   ```

## Running the Test

### Prerequisites
- Python 3.9+
- All dependencies installed (loguru, etc.)
- Test should work without actual API calls (uses mock client)

### Command
```bash
python tests/test_phase1_to_phase2_user_input.py
```

### Expected Output
```
================================================================================
Testing User Input Flow: Phase 1 -> Phase 2
================================================================================

[Phase 1] Generating research goals...
Phase 1 generated 2 goals

User provided input: '请重点关注技术实现细节和性能优化方面'

[Phase 2] Synthesizing goals with user input...
Phase 2 generated topic: 综合主题[含用户输入]

================================================================================
Verification Results
================================================================================

1. Phase 2 API call captured: ✅
2. User input text in prompt: ✅ YES
3. User context marker ('用户补充说明') in prompt: ✅ YES
4. Extracted user input from prompt: '请重点关注技术实现细节和性能优化方面'
   Matches test input: ✅ YES

5. AI response reflects user input detection: ✅ YES

--- Phase 2 Prompt Excerpt (showing user context section) ---
**用户补充说明：**
请重点关注技术实现细节和性能优化方面

================================================================================
✅ TEST PASSED: User input from Phase 1 is correctly passed to Phase 2
   - User input is included in Phase 2 prompt
   - User context marker is present
================================================================================

Token Usage Summary:
  Total API calls: 2
  Total tokens: ~60-100
  Input tokens: ~30-50
  Output tokens: ~30-50
```

## Why the Test Might Fail

### Common Failure Scenarios

1. **User input not in prompt**
   - **Cause**: `user_input` parameter not passed to Phase 2's `execute()` method
   - **Location**: Check `research/agent.py:262` - ensure `user_input=amend` is passed

2. **User context marker missing**
   - **Cause**: `user_context_section` not formatted correctly
   - **Location**: Check `research/phases/phase2_synthesize.py:62-63`

3. **Prompt template not rendering**
   - **Cause**: `{user_context}` placeholder not in template or not replaced
   - **Location**: Check `research/prompts/phase2_synthesize/instructions.md:8`

4. **Empty user context when no input**
   - **Cause**: User context section should be empty string when `user_input=None`
   - **Expected**: Template should handle empty `user_context` gracefully

## Token Usage

This test uses **minimal tokens** (~60-100 total) because:
- Mock client returns minimal responses
- No actual API calls are made
- Responses are pre-generated JSON strings

## Conclusion

This test verifies the complete flow of user input from Phase 1 to Phase 2:
- ✅ User input is collected
- ✅ User input is passed as parameter
- ✅ User input is included in prompt
- ✅ AI receives user input in correct format

If the test passes, it confirms that user input provided at the end of Phase 1 is correctly provided to the AI for generating output in Phase 2.

