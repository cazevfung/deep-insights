# AI Content Editor Execution Plan

## Executive Summary

This plan outlines the implementation of an AI-powered content editor feature that allows users to interactively edit research phase content (Phase 1-4) by highlighting text and requesting changes or asking questions through an AI assistant powered by Qwen-Plus.

### Key Capabilities
- **Text Selection & Highlighting**: Users can select any portion of displayed phase content
- **Context-Aware AI Interaction**: Selected text + full context up to that point is sent to Qwen-Plus
- **Dual Modes**: 
  - **Question Mode**: Ask questions about selected content
  - **Edit Mode**: Request amendments/changes to selected content
- **Seamless Integration**: Works within existing phase display components (PhaseStreamDisplay, Phase3StepContent, etc.)
- **Real-time Updates**: Changes are reflected immediately in the UI and persisted to backend

### Reference Services Analysis

#### 302_document_editor-main
- **AI Chat Component** (`AiChat.tsx`): Sidebar chat interface with selected text support
- **API Route** (`/api/chat/route.ts`): Handles chat requests with content + selected text context
- **Key Pattern**: 
  - User selects text → stored in global state (`chatSelectText`)
  - Chat sends: `{ content, selected, record }` to API
  - API constructs prompt with title, full content, and selected text
  - Streaming response via OpenAI-compatible API

#### AiEditor-main
- **AI Model Architecture**: Abstract `AiModel` class with `chat(selectedText, prompt, listener)` method
- **Chat Configuration**: Supports `appendEditorSelectedContentEnable` to auto-append selected content
- **Message Processing**: `messagesToPayloadProcessor` for custom payload formatting
- **Key Pattern**:
  - Editor maintains selection state
  - AI chat automatically includes selected content in context
  - Supports insertion/replacement of AI responses back into editor

### Design Principles

1. **Non-Intrusive**: Editor functionality appears on-demand (when text is selected)
2. **Context Preservation**: Always includes full phase context up to selection point
3. **Phase-Aware**: Understands which phase content is being edited
4. **Incremental Updates**: Changes affect only the selected portion, not entire phase output
5. **User Control**: Clear distinction between viewing AI response and applying changes

---

## Architecture Overview

### Component Hierarchy

```
Research Session Page
├── PhaseStreamDisplay (Phase 1, 2, 4)
│   └── StreamDisplay
│       └── [Content with selection support]
│       └── ContentEditorPanel (appears on selection)
│           ├── SelectedTextPreview
│           ├── EditorChatInterface
│           └── ApplyChangesButton
│
└── Phase3SessionPage (Phase 3)
    └── Phase3StepList
        └── Phase3StepContent
            └── [Content with selection support]
            └── ContentEditorPanel (appears on selection)
```

### Data Flow

```
User Action: Select text in phase content
    ↓
Frontend: Capture selection + phase context
    ↓
Frontend: Show ContentEditorPanel with selected text
    ↓
User: Type question/edit request
    ↓
Frontend: POST /api/research/editor/chat
    {
        batch_id: string,
        phase: 'phase1' | 'phase2' | 'phase3' | 'phase4',
        step_id?: string,  // For Phase 3 steps
        selected_text: string,
        selected_range: { start: number, end: number },
        full_context: string,  // Content up to selection point
        user_message: string,
        conversation_history?: Array<{role, content}>
    }
    ↓
Backend: EditorService
    ├── Load phase content from batch storage
    ├── Construct context: full_content + selected_text + user_message
    ├── Call Qwen-Plus API (qwen-plus model)
    └── Return streaming response
    ↓
Frontend: Display AI response
    ↓
User: Option to apply changes
    ↓
Frontend: POST /api/research/editor/apply
    {
        batch_id: string,
        phase: string,
        step_id?: string,
        selected_range: { start: number, end: number },
        replacement_text: string
    }
    ↓
Backend: Update phase content in batch storage
    ↓
Frontend: Refresh phase display with updated content
```

---

## Implementation Phases

### Phase 1: Foundation & Configuration (Week 1)

#### 1.1 Backend Configuration
- [ ] Add `qwen-plus` model configuration to `config.yaml`
  ```yaml
  qwen:
    api_key: 'YOUR_QWEN_API_KEY'
    model: 'qwen3-max'  # Keep default
    editor:
      model: 'qwen-plus'  # New: dedicated model for editor
      temperature: 0.7
      max_tokens: 4000
  ```
- [ ] Update `core/config.py` to support `qwen.editor.*` config paths
- [ ] Verify Qwen-Plus API access and test basic chat completion

#### 1.2 Backend API Endpoints
- [ ] Create `backend/app/api/research_editor.py` module
  - `POST /api/research/editor/chat` - Chat with selected content
  - `POST /api/research/editor/apply` - Apply changes to content
  - `GET /api/research/editor/context/{batch_id}/{phase}` - Get phase context
- [ ] Implement `EditorService` class
  - `chat_with_selection()`: Handle chat requests with context
  - `apply_changes()`: Update phase content in batch storage
  - `get_phase_context()`: Retrieve full phase content

#### 1.3 Frontend Types & Interfaces
- [ ] Create `client/src/types/editor.ts`
  ```typescript
  interface TextSelection {
    text: string
    start: number
    end: number
    phase: 'phase1' | 'phase2' | 'phase3' | 'phase4'
    stepId?: string  // For Phase 3
  }
  
  interface EditorChatRequest {
    batch_id: string
    phase: string
    step_id?: string
    selected_text: string
    selected_range: { start: number; end: number }
    full_context: string
    user_message: string
    conversation_history?: Array<{role: string; content: string}>
  }
  
  interface EditorChatResponse {
    response: string
    suggestions?: string[]  // Optional edit suggestions
  }
  ```

### Phase 2: Selection & UI Components (Week 1-2)

#### 2.1 Text Selection Utilities
- [ ] Create `client/src/utils/textSelection.ts`
  - `getTextSelection()`: Get selected text and range from DOM
  - `getSelectionContext()`: Extract surrounding context
  - `highlightSelection()`: Visual highlight of selected text
  - `clearSelection()`: Remove highlights

#### 2.2 ContentEditorPanel Component
- [ ] Create `client/src/components/editor/ContentEditorPanel.tsx`
  - Props:
    - `selection: TextSelection`
    - `onClose: () => void`
    - `onApply: (replacement: string) => void`
  - Features:
    - Floating panel (positioned near selection)
    - Selected text preview (read-only, highlighted)
    - Chat input area
    - AI response display (streaming support)
    - "Apply Changes" button (disabled until AI responds)
    - "Cancel" button

#### 2.3 Selection Integration
- [ ] Update `StreamDisplay.tsx`:
  - Add `onTextSelect` handler
  - Wrap content in selection-aware container
  - Show `ContentEditorPanel` when text is selected
- [ ] Update `Phase3StepContent.tsx`:
  - Add selection support for Phase 3 step content
  - Integrate `ContentEditorPanel`

### Phase 3: Backend Editor Service (Week 2)

#### 3.1 EditorService Implementation
- [ ] Create `backend/app/services/editor_service.py`
  ```python
  class EditorService:
      def __init__(self, config: dict):
          self.config = config
          self.qwen_client = None  # Lazy init
      
      async def chat_with_selection(
          self,
          batch_id: str,
          phase: str,
          selected_text: str,
          full_context: str,
          user_message: str,
          conversation_history: Optional[List] = None,
          step_id: Optional[str] = None
      ) -> AsyncIterator[str]:
          """Stream AI response for selected content editing."""
          # 1. Load phase content from batch storage
          # 2. Construct prompt with context
          # 3. Call Qwen-Plus API
          # 4. Stream response
      
      async def apply_changes(
          self,
          batch_id: str,
          phase: str,
          selected_range: dict,
          replacement_text: str,
          step_id: Optional[str] = None
      ) -> dict:
          """Apply changes to phase content."""
          # 1. Load current content
          # 2. Replace selected range with replacement_text
          # 3. Save updated content
          # 4. Return updated content
  ```

#### 3.2 Prompt Engineering
- [ ] Create `research/prompts/editor/system.md`
  - System prompt for editor assistant
  - Instructions for understanding context and making targeted edits
- [ ] Create `research/prompts/editor/user_template.md`
  - Template for constructing user messages with context
  - Format: Selected text + Full context + User request

#### 3.3 API Route Implementation
- [ ] Implement `/api/research/editor/chat` endpoint
  - Validate request (batch_id, phase, selected_text)
  - Call `EditorService.chat_with_selection()`
  - Stream response using SSE or WebSocket
- [ ] Implement `/api/research/editor/apply` endpoint
  - Validate request
  - Call `EditorService.apply_changes()`
  - Return updated content
- [ ] Add error handling and logging

### Phase 4: Frontend Integration & API Client (Week 2-3)

#### 4.1 API Service
- [ ] Update `client/src/services/api.ts`
  - Add `editorChat()` method
  - Add `applyEditorChanges()` method
  - Support streaming responses

#### 4.2 Editor Chat Hook
- [ ] Create `client/src/hooks/useEditorChat.ts`
  - Manage chat state (messages, loading, error)
  - Handle streaming responses
  - Provide `sendMessage()` and `applyChanges()` functions

#### 4.3 Phase Content Updates
- [ ] Update phase display components to refresh after edits
  - Phase 1: Update research goals display
  - Phase 2: Update finalized questions display
  - Phase 3: Update step content display
  - Phase 4: Update synthesis report display
- [ ] Ensure WebSocket updates reflect editor changes

### Phase 5: Advanced Features (Week 3-4)

#### 5.1 Conversation History
- [ ] Persist editor chat history per selection
- [ ] Show conversation thread in `ContentEditorPanel`
- [ ] Support multi-turn conversations about same selection

#### 5.2 Edit Suggestions
- [ ] AI can provide multiple edit options
- [ ] User can preview changes before applying
- [ ] Diff view showing original vs. proposed changes

#### 5.3 Undo/Redo Support
- [ ] Track edit history per phase
- [ ] Implement undo/redo functionality
- [ ] Store edit history in batch metadata

#### 5.4 Keyboard Shortcuts
- [ ] `Ctrl/Cmd + E`: Open editor for selected text
- [ ] `Esc`: Close editor panel
- [ ] `Ctrl/Cmd + Enter`: Apply changes

### Phase 6: Testing & Refinement (Week 4)

#### 6.1 Unit Tests
- [ ] Test `EditorService` methods
- [ ] Test text selection utilities
- [ ] Test API endpoints

#### 6.2 Integration Tests
- [ ] Test full flow: select → chat → apply → refresh
- [ ] Test with different phases (1, 2, 3, 4)
- [ ] Test with Phase 3 step content

#### 6.3 User Testing
- [ ] Test with real research sessions
- [ ] Gather feedback on UX
- [ ] Refine prompts based on AI responses

---

## Technical Specifications

### Backend API Endpoints

#### POST `/api/research/editor/chat`
**Request:**
```json
{
  "batch_id": "20251119_123456",
  "phase": "phase1",
  "step_id": null,
  "selected_text": "研究目标1：分析AI在咨询顾问领域的应用",
  "selected_range": {
    "start": 150,
    "end": 200
  },
  "full_context": "阶段1输出内容...",
  "user_message": "请将这个目标改得更具体一些",
  "conversation_history": []
}
```

**Response (Streaming):**
```
data: {"type": "token", "content": "根据"}
data: {"type": "token", "content": "您的"}
data: {"type": "token", "content": "要求"}
...
data: {"type": "done"}
```

#### POST `/api/research/editor/apply`
**Request:**
```json
{
  "batch_id": "20251119_123456",
  "phase": "phase1",
  "step_id": null,
  "selected_range": {
    "start": 150,
    "end": 200
  },
  "replacement_text": "研究目标1：深入分析AI技术在管理咨询顾问工作中的具体应用场景、实施路径与效果评估"
}
```

**Response:**
```json
{
  "status": "success",
  "updated_content": "完整更新后的阶段内容...",
  "metadata": {
    "edit_timestamp": "2025-11-19T12:34:56Z",
    "edit_count": 1
  }
}
```

### Frontend Component Props

#### ContentEditorPanel
```typescript
interface ContentEditorPanelProps {
  selection: TextSelection
  batchId: string
  onClose: () => void
  onApply: (replacement: string) => Promise<void>
  position?: { top: number; left: number }  // Optional positioning
}
```

### Prompt Template

#### System Prompt (`research/prompts/editor/system.md`)
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

#### User Prompt Template
```
以下是用户选中的文本：
---
{selected_text}
---

以下是该文本的完整上下文（来自{phase}阶段）：
---
{full_context}
---

用户请求：
{user_message}

请根据上下文和用户请求，提供修改建议或回答问题。
```

---

## Data Model Changes

### Batch Storage Structure
No changes to existing batch structure. Editor changes are applied directly to phase content files:

```
data/research/batches/{batch_id}/
├── phase1_output.json  # Updated when Phase 1 content is edited
├── phase2_output.json  # Updated when Phase 2 content is edited
├── phase3/
│   └── steps/
│       └── {step_id}.json  # Updated when Phase 3 step is edited
└── phase4_output.json  # Updated when Phase 4 content is edited
```

### Editor Metadata (Optional Enhancement)
Add edit history tracking:

```json
{
  "batch_id": "20251119_123456",
  "editor_history": [
    {
      "timestamp": "2025-11-19T12:34:56Z",
      "phase": "phase1",
      "step_id": null,
      "edit_type": "replacement",
      "original_range": { "start": 150, "end": 200 },
      "original_text": "...",
      "replacement_text": "...",
      "user_message": "请将这个目标改得更具体一些"
    }
  ]
}
```

---

## Configuration

### config.yaml Additions
```yaml
qwen:
  api_key: 'YOUR_QWEN_API_KEY'
  model: 'qwen3-max'
  editor:
    model: 'qwen-plus'
    temperature: 0.7
    max_tokens: 4000
    system_prompt_path: 'research/prompts/editor/system.md'
```

### Environment Variables
No new environment variables required. Uses existing `QWEN_API_KEY` or `DASHSCOPE_API_KEY`.

---

## Security Considerations

1. **Batch ID Validation**: Verify user has access to batch before allowing edits
2. **Phase Content Validation**: Ensure edits don't break phase content structure
3. **Rate Limiting**: Limit editor API calls to prevent abuse
4. **Content Sanitization**: Sanitize user input and AI responses
5. **Audit Logging**: Log all editor actions for debugging and audit

---

## Performance Considerations

1. **Lazy Loading**: Load full phase context only when editor is opened
2. **Caching**: Cache phase content in memory during editing session
3. **Streaming**: Use streaming for AI responses to improve perceived performance
4. **Debouncing**: Debounce rapid selection changes
5. **Incremental Updates**: Only update changed portions of UI

---

## Error Handling

### Backend Errors
- **Invalid batch_id**: Return 404 with clear error message
- **Invalid phase**: Return 400 with supported phases list
- **Qwen API failure**: Return 502 with retry suggestion
- **Content update failure**: Return 500 with rollback attempt

### Frontend Errors
- **Selection lost**: Show notification, allow re-selection
- **Network error**: Show retry button
- **Apply failure**: Show error, keep editor open for retry

---

## Testing Strategy

### Unit Tests
- `EditorService.chat_with_selection()`: Mock Qwen client, test prompt construction
- `EditorService.apply_changes()`: Test content replacement logic
- Text selection utilities: Test range calculation, context extraction

### Integration Tests
- Full editor flow: Select → Chat → Apply → Verify
- Phase-specific tests: Test with Phase 1, 2, 3, 4 content
- Error scenarios: Invalid batch, network failure, API errors

### Manual Testing Checklist
- [ ] Select text in Phase 1 research goals → Edit → Verify update
- [ ] Select text in Phase 2 questions → Ask question → Verify response
- [ ] Select text in Phase 3 step → Edit → Verify step content update
- [ ] Select text in Phase 4 report → Edit → Verify report update
- [ ] Test with streaming responses
- [ ] Test conversation history
- [ ] Test undo/redo (if implemented)
- [ ] Test keyboard shortcuts
- [ ] Test error handling (network failure, invalid selection)

---

## Rollout Plan

### Phase 1: Internal Testing (Week 4)
- Deploy to development environment
- Internal team testing
- Fix critical bugs

### Phase 2: Beta Release (Week 5)
- Deploy to staging
- Limited user testing
- Gather feedback

### Phase 3: Production Release (Week 6)
- Deploy to production
- Monitor error rates and performance
- Collect user feedback

---

## Future Enhancements

1. **Multi-selection Editing**: Select multiple non-contiguous text portions
2. **Batch Edits**: Apply same edit to multiple phases
3. **Edit Templates**: Pre-defined edit patterns (e.g., "make more concise", "add examples")
4. **Collaborative Editing**: Multiple users editing same batch (with conflict resolution)
5. **Edit Suggestions**: AI proactively suggests improvements
6. **Version Control**: Full version history with diffs
7. **Export Edits**: Export edit history as markdown/JSON

---

## Dependencies

### Backend
- Existing: `research.client.QwenStreamingClient`
- Existing: Batch storage system
- New: None (reuse existing infrastructure)

### Frontend
- Existing: React, TypeScript, API service
- New: Text selection utilities (vanilla JS)
- Optional: Diff library for change preview (e.g., `react-diff-view`)

---

## Success Metrics

1. **Adoption Rate**: % of research sessions using editor feature
2. **Edit Frequency**: Average edits per session
3. **User Satisfaction**: Feedback scores on editor usefulness
4. **Performance**: Average time from selection to AI response
5. **Error Rate**: % of failed edit operations
6. **Content Quality**: Improvement in edited content quality (subjective)

---

## Appendix

### Reference Code Patterns

#### Text Selection (from 302_document_editor)
```typescript
// Global state for selected text
const [chatSelectText, setChatSelectText] = useState('')

// Selection handler
const handleTextSelect = () => {
  const selection = window.getSelection()
  if (selection && selection.toString().trim()) {
    setChatSelectText(selection.toString())
  }
}
```

#### AI Chat Integration (from AiEditor)
```typescript
// Auto-append selected content
const finalPrompt = prompt.includes("{content}") 
  ? prompt.split('{content}').join(selectedText) 
  : `${selectedText ? selectedText + "\n" : ""}${prompt}`
```

### Related Documentation
- `docs/plans/RIGHT_COLUMN_CHAT_EXECUTION_PLAN.md` - Existing chat system
- `docs/guides/prompts/PROMPT_IMPROVEMENT_IMPLEMENTATION_GUIDE.md` - Prompt engineering
- `research/prompts/phase1_synthesize/instructions.md` - Phase 1 output format

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-19  
**Author**: AI Assistant  
**Status**: Draft - Pending Review

