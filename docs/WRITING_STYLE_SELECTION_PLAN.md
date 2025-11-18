# Writing Style Selection Feature - Implementation Plan

## Overview

This document outlines the plan to implement a writing style selection feature that allows users to choose from 4 different writing tones/styles at the start of the research workflow. The selected style will be applied consistently across Phases 2, 3, and 4.

## Feature Requirements

### User-Facing Requirements
1. **Style Selection**: User selects one of 4 writing styles at the beginning of the workflow (before Phase 0.5)
2. **Style Persistence**: Selected style is stored in session metadata and persists throughout the workflow
3. **Style Application**: Selected style prompt is included in all prompts for Phases 2, 3, and 4
4. **Backward Compatibility**: Existing sessions without style selection default to "professional" style

### Available Styles

1. **Consultant (咨询顾问风格)** - `style_consultant_cn.md` (already exists)
   - Tone: Professional, restrained, fact-based reasoning
   - Target audience: Business stakeholders/product managers/executives
   - Structure: Conclusion first → Evidence & reasoning → Impact & recommendations
   - Language: Natural Chinese, avoid translation tone and adjective stacking

2. **Explanatory (教学风格)** - `style_explanatory_cn.md` (to be created)
   - Tone: Educational, clear, step-by-step explanations
   - Target audience: Learners, students, general audience seeking understanding
   - Structure: Introduction → Concepts → Examples → Practice/Application
   - Language: Clear, accessible, uses analogies and examples

3. **Creative (UP主风格)** - `style_creative_cn.md` (to be created)
   - Tone: Engaging, conversational, entertaining
   - Target audience: General audience, content consumers
   - Structure: Hook → Story → Insights → Call to action
   - Language: Casual, vivid, uses emojis sparingly, storytelling approach

4. **Persuasive (说服力风格)** - `style_persuasive_cn.md` (to be created)
   - Tone: Convincing, argumentative, compelling
   - Target audience: Decision makers, stakeholders needing to be convinced
   - Structure: Problem → Solution → Benefits → Call to action
   - Language: Strong, confident, uses rhetorical devices, emphasizes benefits

## Implementation Plan

### Phase 1: Create Style Prompt Files

#### 1.1 Create New Style Partial Files

**Location**: `research/prompts/_partials/`

**Files to create**:
1. `style_explanatory_cn.md` - Explanatory/Teaching style
2. `style_creative_cn.md` - Creative/UP主 style  
3. `style_persuasive_cn.md` - Persuasive style

**Content Structure** (following the pattern of `style_consultant_cn.md`):
- **写作人设** (Writing Persona)
- **引用与证据政策** (Citation & Evidence Policy)
- **措辞规范** (Wording Guidelines)
- **语气控制** (Tone Control)

#### 1.2 Style File Naming Convention

- Use consistent naming: `style_{style_name}_cn.md`
- Style identifiers:
  - `professional` → `style_consultant_cn.md` (existing)
  - `explanatory` → `style_explanatory_cn.md`
  - `creative` → `style_creative_cn.md`
  - `persuasive` → `style_persuasive_cn.md`

### Phase 2: Add Style Selection to User Interface

#### 2.1 Add Style Selection to Frontend (Primary Implementation)

**File**: `client/src/pages/UserGuidancePage.tsx`

**This is the first page in the workflow** (route `/`), where users provide research guidance. Style selection should be added here.

**Implementation Details**:
- Add a style selection component/section before or alongside the user guidance textarea
- Display 4 style options as cards or radio buttons with:
  - Style name (Chinese)
  - Brief description
  - Visual indicator (icon or color)
- Store selected style in workflow store or send to backend when creating session
- Default to 'professional' if not selected

**UI Component Structure**:
```tsx
// Add to UserGuidancePage.tsx
const [writingStyle, setWritingStyle] = useState<string>('professional')

const styleOptions = [
  { id: 'professional', name: '咨询顾问风格', description: '专业、克制、以事实与推理为主' },
  { id: 'explanatory', name: '教学风格', description: '清晰、易懂、循序渐进' },
  { id: 'creative', name: 'UP主风格', description: '生动、有趣、引人入胜' },
  { id: 'persuasive', name: '说服力风格', description: '有力、有说服力、强调收益' },
]

// Add style selection UI before or after the guidance textarea
// When submitting, include writingStyle in the session creation request
```

**Backend API Update**:
- Modify `/api/sessions/create` endpoint to accept `writing_style` parameter
- Store `writing_style` in session metadata

#### 2.2 Add Style Selection Method to Console Interface (Fallback)

**File**: `research/ui/console_interface.py`

**New Method** (for CLI/console usage):
```python
def prompt_style_selection(self) -> str:
    """
    Prompt user to select writing style.
    
    Returns:
        Style identifier: 'professional', 'explanatory', 'creative', or 'persuasive'
    """
    # Display numbered list of 4 styles with brief descriptions
    # Accept input: 1, 2, 3, 4 or style name
    # Validate input and return style identifier
    # Default to 'professional' if invalid input
```

#### 2.3 Add Style Selection to Agent Workflow

**File**: `research/agent.py`

**Modification**: `run_research()` method

**Location**: At the very beginning, after session initialization, before Phase 0

**Code Flow**:
```python
def run_research(self, batch_id: str, user_topic: Optional[str] = None, 
                 session_id: Optional[str] = None) -> Dict[str, Any]:
    # ... existing session initialization ...
    
    # NEW: Get writing style from session metadata (set by frontend or CLI)
    writing_style = session.get_metadata("writing_style", "professional")
    # If not set and using console UI, prompt for selection
    if not writing_style or writing_style == "professional":
        if hasattr(self.ui, 'prompt_style_selection'):
            writing_style = self.ui.prompt_style_selection()
            session.set_metadata("writing_style", writing_style)
            session.save()
    
    # Continue with existing workflow...
```

**Note**: For frontend usage, the style is already set when the session is created via the API. For CLI usage, it will prompt if not set.

### Phase 3: Create Style Loading Utility

#### 3.1 Add Style Loader Function

**File**: `research/prompts/loader.py` (or create new `research/prompts/style_loader.py`)

**New Function**:
```python
def load_style_prompt(style_name: str) -> str:
    """
    Load style prompt partial by style name.
    
    Args:
        style_name: Style identifier ('professional', 'explanatory', 'creative', 'persuasive')
    
    Returns:
        Style prompt content as string
    
    Raises:
        FileNotFoundError: If style file doesn't exist
    """
    # Map style names to file names
    style_file_map = {
        'professional': 'style_consultant_cn.md',
        'explanatory': 'style_explanatory_cn.md',
        'creative': 'style_creative_cn.md',
        'persuasive': 'style_persuasive_cn.md',
    }
    
    filename = style_file_map.get(style_name, 'style_consultant_cn.md')
    return load_prompt_partial(filename)
```

**Helper Function**:
```python
def load_prompt_partial(filename: str) -> str:
    """
    Load a partial prompt file from _partials directory.
    
    Args:
        filename: Name of partial file (e.g., 'style_consultant_cn.md')
    
    Returns:
        File content as string
    """
    base = _get_base_dir()
    partials_dir = os.path.join(base, "_partials")
    path = os.path.join(partials_dir, filename)
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"Style partial not found: {filename}")
    
    return _maybe_cached(path)
```

### Phase 4: Integrate Style into Phase Prompts

#### 4.1 Phase 2 Integration

**File**: `research/prompts/phase2_finalize/instructions.md`

**Modification**: Add style partial inclusion at the top
```markdown
{{> style_{writing_style}_cn.md}}

**你的任务**：分析这些研究问题...
```

**File**: `research/phases/phase2_finalize.py`

**Modification**: Add style to context
```python
def execute(self, ...):
    # Get writing style from session
    writing_style = self.session.get_metadata("writing_style", "professional")
    
    context = {
        "writing_style": writing_style,
        # ... existing context ...
    }
    
    messages = compose_messages("phase2_finalize", context=context)
```

**Note**: The prompt loader's `_apply_partials()` function should handle the `{{> style_{writing_style}_cn.md}}` syntax automatically, but we need to ensure the context variable is properly substituted.

#### 4.2 Phase 3 Integration

**File**: `research/prompts/phase3_execute/instructions.md`

**Modification**: Add style partial at the top
```markdown
{{> style_{writing_style}_cn.md}}

**你的任务**：围绕步骤的提问...
```

**File**: `research/phases/phase3_execute.py`

**Modification**: Add style to context in all prompt composition locations
- In `_build_analysis_prompt()` method
- In `_build_context_request_prompt()` method

**Context Addition**:
```python
writing_style = self.session.get_metadata("writing_style", "professional")
context["writing_style"] = writing_style
```

#### 4.3 Phase 4 Integration

**File**: `research/prompts/phase4_synthesize/system.md`

**Modification**: Add style partial at the top
```markdown
{{> style_{writing_style}_cn.md}}

[Rest of system prompt...]
```

**File**: `research/prompts/phase4_synthesize/instructions.md`

**Modification**: Ensure style is referenced in instructions (may already be covered by system message)

**File**: `research/phases/phase4_synthesize.py`

**Modification**: Add style to context in `_render_system_message()` and all prompt stages
```python
def _render_system_message(self, context: Dict[str, Any]) -> str:
    writing_style = self.session.get_metadata("writing_style", "professional")
    context["writing_style"] = writing_style
    # ... existing code ...
```

### Phase 5: Update Prompt Loader to Handle Dynamic Partials

#### 5.1 Enhance Partial Resolution

**File**: `research/prompts/loader.py`

**Modification**: Update `_apply_partials()` to handle template variables in partial names

**Current Behavior**: `{{> filename.md}}` loads static file
**New Behavior**: `{{> style_{writing_style}_cn.md}}` resolves `{writing_style}` from context

**Implementation**:
```python
def _apply_partials(content: str, phase_dir: str, context: Optional[Dict[str, object]] = None) -> str:
    """
    Apply partial includes, with optional context for dynamic filenames.
    
    Args:
        content: Template content
        phase_dir: Phase directory for relative includes
        context: Optional context dict for variable substitution in partial names
    """
    # ... existing code ...
    
    # When resolving partial filename, check if it contains template variables
    token = text[idx + 3 : end].strip()
    
    # If token contains {variable}, render it with context first
    if context and '{' in token:
        try:
            token = token.format(**context)
        except KeyError:
            # Variable not in context, keep original (will fail with FileNotFoundError)
            pass
    
    # ... rest of existing code ...
```

**Update `compose_messages()` to pass context to `_apply_partials()`**:
```python
def compose_messages(
    phase: str,
    context: Dict[str, object],
    *,
    locale: Optional[str] = None,
    variant: Optional[str] = None,
) -> List[Dict[str, str]]:
    # ... existing code ...
    
    # Apply partials with context for dynamic includes
    instructions_tmpl = _apply_partials(instructions_tmpl, phase_dir, context=context)
    instructions_msg = render_prompt(instructions_tmpl, context)
    
    # ... rest of existing code ...
```

### Phase 6: CLI Support (Optional)

#### 6.1 Add CLI Argument for Style

**File**: `scripts/run_research.py`

**Optional Enhancement**: Add `--style` argument
```python
parser.add_argument(
    "--style",
    choices=["professional", "explanatory", "creative", "persuasive"],
    help="Writing style for the research report (default: prompt user)"
)
```

**Pass to agent**:
```python
result = agent.run_research(
    batch_id=args.batch_id,
    user_topic=args.topic,
    session_id=args.session,
    writing_style=args.style  # NEW
)
```

**Update Agent Method**:
```python
def run_research(
    self,
    batch_id: str,
    user_topic: Optional[str] = None,
    session_id: Optional[str] = None,
    writing_style: Optional[str] = None  # NEW
) -> Dict[str, Any]:
    # ...
    if not writing_style:
        writing_style = session.get_metadata("writing_style")
    if not writing_style:
        writing_style = self.ui.prompt_style_selection()
    session.set_metadata("writing_style", writing_style)
    # ...
```

## File Structure Changes

### New Files to Create

```
research/prompts/_partials/
├── style_consultant_cn.md          (already exists)
├── style_explanatory_cn.md          (NEW)
├── style_creative_cn.md             (NEW)
└── style_persuasive_cn.md           (NEW)
```

### Files to Modify

```
client/src/
└── pages/
    └── UserGuidancePage.tsx          (add style selection UI component)

backend/ (or wherever API routes are)
└── sessions API endpoint              (accept writing_style parameter)

research/
├── agent.py                          (get style from session metadata)
├── phases/
│   ├── phase2_finalize.py            (add style to context)
│   ├── phase3_execute.py              (add style to context)
│   └── phase4_synthesize.py           (add style to context)
├── prompts/
│   ├── loader.py                      (enhance partial resolution)
│   └── phase2_finalize/
│       └── instructions.md          (add style partial)
│   └── phase3_execute/
│       └── instructions.md           (add style partial)
│   └── phase4_synthesize/
│       ├── system.md                 (add style partial)
│       └── instructions.md           (verify style integration)
└── ui/
    └── console_interface.py          (add prompt_style_selection method - for CLI)

scripts/
└── run_research.py                   (optional: add --style CLI arg)
```

## Implementation Steps (Execution Order)

1. **Step 1**: Create the 3 new style prompt files (`style_explanatory_cn.md`, `style_creative_cn.md`, `style_persuasive_cn.md`)
2. **Step 2**: Add style selection UI to `UserGuidancePage.tsx` (frontend)
3. **Step 3**: Update backend API to accept `writing_style` parameter in session creation
4. **Step 4**: Enhance `_apply_partials()` in `loader.py` to support dynamic partial names with context variables
5. **Step 5**: Update `run_research()` in `agent.py` to get style from session metadata
6. **Step 6**: Update Phase 2 prompt files and code to include style
7. **Step 7**: Update Phase 3 prompt files and code to include style
8. **Step 8**: Update Phase 4 prompt files and code to include style
9. **Step 9**: (Optional) Add `prompt_style_selection()` method to `ConsoleInterface` for CLI usage
10. **Step 10**: (Optional) Add CLI argument support
11. **Step 11**: Test with all 4 styles across full workflow

## Testing Plan

### Unit Tests
- Test style loading function with all 4 style names
- Test partial resolution with dynamic filenames
- Test style selection UI method

### Integration Tests
- Test full workflow with each style
- Test backward compatibility (sessions without style default to professional)
- Test style persistence across session resume
- Verify style is applied in Phase 2, 3, and 4 outputs

### Manual Testing Checklist
- [ ] Style selection UI appears on UserGuidancePage (first page)
- [ ] All 4 styles can be selected via frontend
- [ ] Selected style is sent to backend when creating session
- [ ] Selected style persists in session metadata
- [ ] Phase 2 output reflects selected style
- [ ] Phase 3 output reflects selected style
- [ ] Phase 4 output reflects selected style
- [ ] Resuming session preserves style selection
- [ ] Default style (professional) works for existing sessions
- [ ] Style selection works in CLI mode (if implemented)

## Backward Compatibility

### Handling Existing Sessions
- Sessions without `writing_style` metadata default to `"professional"`
- Code should use: `session.get_metadata("writing_style", "professional")`
- No breaking changes to existing prompt structure

### Migration Path
- Existing sessions will work without modification
- New sessions will prompt for style selection
- Users can manually set style via session metadata if needed

## Style Prompt Content Guidelines

### Common Structure for All Styles

Each style file should include:

1. **写作人设 (Writing Persona)**
   - Tone description
   - Target audience
   - Output structure
   - Language guidelines

2. **引用与证据政策 (Citation & Evidence Policy)**
   - Direct quote limits
   - Citation usage guidelines
   - Data and example preferences

3. **措辞规范 (Wording Guidelines)**
   - Words/phrases to avoid
   - Preferred alternatives
   - Examples of good vs. bad usage

4. **语气控制 (Tone Control)**
   - Quantification language
   - Conditional language
   - Focus areas (business impact, user experience, etc.)

### Style-Specific Guidelines

#### Explanatory Style (`style_explanatory_cn.md`)
- Emphasize: Clarity, step-by-step explanations, examples
- Use: Analogies, comparisons, "think of it as..." patterns
- Avoid: Jargon without explanation, assumptions of prior knowledge

#### Creative Style (`style_creative_cn.md`)
- Emphasize: Engagement, storytelling, vivid descriptions
- Use: Casual language, rhetorical questions, narrative hooks
- Avoid: Overly formal language, dry academic tone

#### Persuasive Style (`style_persuasive_cn.md`)
- Emphasize: Strong arguments, benefits, clear calls to action
- Use: Rhetorical devices, contrast, emphasis on outcomes
- Avoid: Weak language, uncertainty, passive voice

## Open Questions / Decisions Needed

1. **Style Selection Timing**: Should style be selected before Phase 0.5 (role generation) or after? 
   - **Decision**: Before Phase 0.5, as style might influence role generation
   
2. **Style Change Mid-Workflow**: Should users be able to change style mid-workflow?
   - **Decision**: Not in initial implementation; style is set at start
   
3. **Style in Phase 1**: Should Phase 1 (goal generation) also use the style?
   - **Decision**: No, Phase 1 is about goal generation, not writing style
   
4. **Partial File Extension**: Should we use `.md` extension in partial includes?
   - **Decision**: Yes, keep existing pattern `{{> filename.md}}`

5. **Error Handling**: What happens if style file is missing?
   - **Decision**: Fall back to `style_consultant_cn.md` (professional) with warning

## Success Criteria

✅ User can select from 4 writing styles at workflow start
✅ Selected style is stored in session metadata
✅ Style prompt is included in Phase 2, 3, and 4 prompts
✅ Output from Phases 2, 3, and 4 reflects the selected style
✅ Backward compatibility maintained (defaults to professional)
✅ All 4 styles produce distinct, appropriate outputs

## Notes

- The existing `style_consultant_cn.md` serves as the template for creating the other 3 style files
- The prompt loader's partial system already supports `{{> filename.md}}` syntax
- We need to enhance it to support dynamic filenames with context variables
- Style selection should be a one-time choice per session (not changeable mid-workflow)
- Consider adding style preview/description when prompting user for selection

