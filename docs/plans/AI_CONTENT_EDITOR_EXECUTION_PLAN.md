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
- **Automatic Step Rerun**: For Phase 3, if a step goal is edited, the system automatically detects the change and triggers a rerun of that step (with optional report regeneration)

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

## Critical Design Decision: Immediate Persistence & Phase Propagation

### Question: Will changes immediately apply to session files and be used by future phases?

**Answer: YES - Changes are immediately persisted and automatically used by subsequent phases.**

#### How It Works

1. **Immediate Persistence**: When a user applies an edit (e.g., edits a Phase 1 research goal), the `EditorService.apply_changes()` method:
   - Loads the `ResearchSession` for the batch
   - Updates the phase artifact with the edited content
   - Calls `session.save_phase_artifact(phase_key, updated_artifact, autosave=True)`
   - This **immediately writes** to `data/research/batches/{batch_id}/session.json`

2. **Automatic Phase Propagation**: When subsequent phases run, they load artifacts using:
   ```python
   phase1_artifact = session.get_phase_artifact("phase1")
   ```
   - This reads from the **same session.json file** that was just updated
   - Phase 2, 3, and 4 will automatically use the **edited** Phase 1 content
   - No manual re-run needed - edits are live immediately

3. **Example Flow**:
   ```
   User edits Phase 1 goal: "分析AI应用" → "深入分析AI技术在咨询顾问工作中的具体应用场景"
      ↓
   EditorService saves via session.save_phase_artifact("phase1", updated_artifact)
      ↓
   session.json updated immediately
      ↓
   Phase 2 runs (now or later) → loads session.get_phase_artifact("phase1")
      ↓
   Phase 2 uses the EDITED goal automatically
   ```

#### Edge Cases & Considerations

- **Phase Already Running**: If Phase 2 is currently running when Phase 1 is edited, Phase 2 will continue with the old content. The edited content will be used the next time Phase 2 runs (e.g., on rerun or in a new batch).
- **Phase Already Complete**: If Phase 2 has already completed, editing Phase 1 won't retroactively change Phase 2's output. User would need to rerun Phase 2 to use the edited Phase 1 content.
- **Validation**: The editor should warn users if editing a phase that has already been consumed by later phases, suggesting a rerun of dependent phases.

#### Special Case: Phase 3 Step Goal Changes

**Automatic Step Rerun Detection**: When editing Phase 3 content, the system automatically detects if a step goal was changed:

1. **Detection Logic**: The `EditorService._detect_phase3_goal_change()` method:
   - Parses the edited text to find patterns like "步骤 X: goal"
   - Matches the step_id and goal against the Phase 3 plan
   - Compares old goal vs. new goal
   - Returns step info if goal actually changed

2. **Automatic Rerun**: When a goal change is detected:
   - The plan in `phase3` artifact is updated with the new goal
   - `workflow_service.rerun_phase3_step()` is automatically called
   - The step is re-executed with the new goal
   - If Phase 4 is complete, the report is automatically regenerated (`regenerate_report=True`)

3. **User Experience**:
   - User edits a step goal → System detects change → Step automatically reruns
   - User sees notification: "步骤 X 的目标已更改，正在自动重新执行..."
   - No manual rerun needed - fully automatic

4. **Example Flow**:
   ```
   User edits: "步骤 3: 分析AI应用" → "步骤 3: 深入分析AI技术在咨询顾问工作中的具体应用场景"
      ↓
   EditorService detects goal change (step_id=3, old≠new)
      ↓
   Plan updated in phase3 artifact
      ↓
   workflow_service.rerun_phase3_step(step_id=3, regenerate_report=True) triggered
      ↓
   Step 3 re-executes with new goal
      ↓
   Phase 4 report regenerated (if Phase 4 was complete)
   ```

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

## Detailed Implementation Guide

This section provides step-by-step implementation details for both backend and frontend changes.

### Quick Implementation Reference

**Backend Changes:**
1. **Config**: Add `qwen.editor.*` to `config.yaml`, add `get_editor_config()` to `core/config.py`
2. **Service**: Create `backend/app/services/editor_service.py` with `EditorService` class
3. **Routes**: Add `/editor/chat` and `/editor/apply` endpoints to `backend/app/routes/research.py`
4. **Prompts**: Create `research/prompts/editor/system.md`

**Frontend Changes:**
1. **Types**: Create `client/src/types/editor.ts` with all TypeScript interfaces
2. **Utils**: Create `client/src/utils/textSelection.ts` for text selection handling
3. **Hook**: Create `client/src/hooks/useEditorChat.ts` for chat state management
4. **Component**: Create `client/src/components/editor/ContentEditorPanel.tsx` for UI
5. **API**: Add `editorChat()` and `applyEditorChanges()` to `client/src/services/api.ts`
6. **Integration**: Add selection support to `StreamDisplay.tsx` and `Phase3StepContent.tsx`

**Key Implementation Points:**
- Editor service uses `ResearchSession.save_phase_artifact()` to persist changes immediately
- Changes are automatically used by future phases via `session.get_phase_artifact()`
- Frontend uses streaming API for real-time AI responses
- Selection is captured via DOM `mouseup` events and text range calculation

---

## Implementation Phases

### Phase 1: Foundation & Configuration (Week 1)

#### 1.1 Backend Configuration

**File: `config.yaml`**
- [ ] Add editor configuration section:
  ```yaml
  qwen:
    api_key: 'YOUR_QWEN_API_KEY'
    model: 'qwen3-max'  # Keep default
    editor:
      model: 'qwen-plus'  # New: dedicated model for editor
      temperature: 0.7
      max_tokens: 4000
      system_prompt_path: 'research/prompts/editor/system.md'
  ```

**File: `core/config.py`**
- [ ] Add method to get editor config:
  ```python
  def get_editor_config(self) -> dict:
      """Get editor-specific Qwen configuration."""
      return {
          'model': self.get('qwen.editor.model', 'qwen-plus'),
          'temperature': self.get('qwen.editor.temperature', 0.7),
          'max_tokens': self.get_int('qwen.editor.max_tokens', 4000),
          'system_prompt_path': self.get('qwen.editor.system_prompt_path', 'research/prompts/editor/system.md'),
      }
  ```

**File: `research/prompts/editor/system.md`** (NEW)
- [ ] Create system prompt file:
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

**Testing:**
- [ ] Verify Qwen-Plus API access: Test basic chat completion with qwen-plus model
- [ ] Verify config loading: Test `config.get_editor_config()` returns correct values

#### 1.2 Backend Service Implementation

**File: `backend/app/services/editor_service.py`** (NEW)
- [ ] Create new service file with complete implementation:
  ```python
  """
  Editor service for AI-powered content editing.
  """
  from typing import Optional, Dict, Any, List, AsyncIterator
  from pathlib import Path
  from loguru import logger
  from research.session import ResearchSession
  from research.client import QwenStreamingClient
  from core.config import Config

  class EditorService:
      def __init__(self, config: Config):
          self.config = config
          self.editor_config = config.get_editor_config()
          self._qwen_client: Optional[QwenStreamingClient] = None
      
      def _get_qwen_client(self) -> QwenStreamingClient:
          """Lazy initialization of Qwen client."""
          if self._qwen_client is None:
              api_key = self.config.get('qwen.api_key') or os.getenv('DASHSCOPE_API_KEY')
              if not api_key:
                  raise ValueError("Qwen API key not configured")
              model = self.editor_config['model']
              self._qwen_client = QwenStreamingClient(api_key=api_key, model=model)
          return self._qwen_client
      
      def _load_session(self, batch_id: str) -> ResearchSession:
          """Load ResearchSession for batch_id."""
          from research.session import ResearchSession
          batches_dir = self.config.get_batches_dir()
          batch_path = batches_dir / batch_id
          if not batch_path.exists():
              raise ValueError(f"Batch {batch_id} not found")
          return ResearchSession.load_from_path(batch_path)
      
      def _get_phase_key(self, phase: str, step_id: Optional[str] = None) -> str:
          """Get phase artifact key."""
          if phase == 'phase3' and step_id:
              return f"phase3_step_{step_id}"
          return phase
      
      def _extract_content_from_artifact(self, artifact: Dict[str, Any], phase: str) -> str:
          """Extract content string from phase artifact."""
          # Phase 1: artifact['data']['goals'] or artifact['data']['content']
          # Phase 2: artifact['data']['plan'] or artifact['data']['questions']
          # Phase 3: artifact['data']['content'] or artifact['data']['step_content']
          # Phase 4: artifact['data']['content'] or artifact['data']['report']
          
          data = artifact.get('data', {})
          
          if phase == 'phase1':
              # Try different possible keys
              return data.get('goals', data.get('content', data.get('output', '')))
          elif phase == 'phase2':
              return data.get('plan', data.get('questions', data.get('content', '')))
          elif phase == 'phase3':
              return data.get('content', data.get('step_content', data.get('output', '')))
          elif phase == 'phase4':
              return data.get('content', data.get('report', data.get('output', '')))
          
          # Fallback: try to find any string content
          if isinstance(data, str):
              return data
          if isinstance(data, dict):
              # Try common keys
              for key in ['content', 'output', 'text', 'result']:
                  if key in data and isinstance(data[key], str):
                      return data[key]
          
          return str(data) if data else ''
      
      def _update_content_in_artifact(
          self, 
          artifact: Dict[str, Any], 
          phase: str, 
          selected_range: Dict[str, int],
          replacement_text: str
      ) -> Dict[str, Any]:
          """Update artifact content with replacement text."""
          current_content = self._extract_content_from_artifact(artifact, phase)
          
          # Replace selected range
          start = selected_range['start']
          end = selected_range['end']
          updated_content = current_content[:start] + replacement_text + current_content[end:]
          
          # Update artifact structure based on phase
          data = artifact.get('data', {})
          
          if phase == 'phase1':
              if 'goals' in data:
                  data['goals'] = updated_content
              else:
                  data['content'] = updated_content
          elif phase == 'phase2':
              if 'plan' in data:
                  data['plan'] = updated_content
              else:
                  data['content'] = updated_content
          elif phase == 'phase3':
              data['content'] = updated_content
          elif phase == 'phase4':
              data['content'] = updated_content
          
          artifact['data'] = data
          return artifact
      
      async def chat_with_selection(
          self,
          batch_id: str,
          phase: str,
          selected_text: str,
          full_context: str,
          user_message: str,
          conversation_history: Optional[List[Dict[str, str]]] = None,
          step_id: Optional[str] = None
      ) -> AsyncIterator[str]:
          """Stream AI response for selected content editing."""
          try:
              # Load session and artifact for context
              session = self._load_session(batch_id)
              phase_key = self._get_phase_key(phase, step_id)
              artifact = session.get_phase_artifact(phase_key, {})
              
              # Load system prompt
              system_prompt_path = Path(self.editor_config['system_prompt_path'])
              if system_prompt_path.exists():
                  with open(system_prompt_path, 'r', encoding='utf-8') as f:
                      system_prompt = f.read()
              else:
                  system_prompt = "你是一个专业的研究内容编辑助手。"
              
              # Construct user prompt
              user_prompt = f"""以下是用户选中的文本：
---
{selected_text}
---

以下是该文本的完整上下文（来自{phase}阶段）：
---
{full_context}
---

用户请求：
{user_message}

请根据上下文和用户请求，提供修改建议或回答问题。"""
              
              # Prepare messages
              messages = [
                  {"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_prompt}
              ]
              
              # Add conversation history if provided
              if conversation_history:
                  messages = [messages[0]] + conversation_history + [messages[1]]
              
              # Stream response from Qwen
              client = self._get_qwen_client()
              async for chunk in client.stream_chat(messages):
                  if chunk.get('content'):
                      yield chunk['content']
              
          except Exception as e:
              logger.error(f"Error in chat_with_selection: {e}", exc_info=True)
              raise
      
      async def apply_changes(
          self,
          batch_id: str,
          phase: str,
          selected_range: Dict[str, int],
          replacement_text: str,
          step_id: Optional[str] = None
      ) -> Dict[str, Any]:
          """Apply changes to phase content and immediately persist."""
          try:
              # Load session
              session = self._load_session(batch_id)
              phase_key = self._get_phase_key(phase, step_id)
              
              # Load current artifact
              artifact = session.get_phase_artifact(phase_key, {})
              if not artifact:
                  raise ValueError(f"Phase artifact {phase_key} not found for batch {batch_id}")
              
              # Update artifact with new content
              updated_artifact = self._update_content_in_artifact(
                  artifact, phase, selected_range, replacement_text
              )
              
              # Save immediately (this persists to session.json)
              session.save_phase_artifact(phase_key, updated_artifact['data'], autosave=True)
              
              # Extract updated content for response
              updated_content = self._extract_content_from_artifact(updated_artifact, phase)
              
              return {
                  "status": "success",
                  "updated_content": updated_content,
                  "metadata": {
                      "edit_timestamp": datetime.now().isoformat(),
                      "persisted": True,
                      "will_affect_future_phases": True,
                      "phase": phase,
                      "step_id": step_id
                  }
              }
              
          except Exception as e:
              logger.error(f"Error in apply_changes: {e}", exc_info=True)
              raise
  ```

#### 1.3 Backend API Routes

**File: `backend/app/routes/research.py`**
- [ ] Add editor routes at the end of the file:
  ```python
  from app.services.editor_service import EditorService
  from fastapi.responses import StreamingResponse
  import json
  
  # Initialize editor service (singleton)
  _editor_service: Optional[EditorService] = None
  
  def get_editor_service() -> EditorService:
      """Get or create editor service instance."""
      global _editor_service
      if _editor_service is None:
          from core.config import Config
          config = Config()
          _editor_service = EditorService(config)
      return _editor_service
  
  
  class EditorChatRequest(BaseModel):
      batch_id: str
      phase: str
      step_id: Optional[str] = None
      selected_text: str
      selected_range: Dict[str, int]
      full_context: str
      user_message: str
      conversation_history: Optional[List[Dict[str, str]]] = None
  
  
  class EditorApplyRequest(BaseModel):
      batch_id: str
      phase: str
      step_id: Optional[str] = None
      selected_range: Dict[str, int]
      replacement_text: str
  
  
  @router.post("/editor/chat")
  async def editor_chat(request: EditorChatRequest):
      """Chat with AI about selected content."""
      try:
          editor_service = get_editor_service()
          
          async def generate():
              async for chunk in editor_service.chat_with_selection(
                  batch_id=request.batch_id,
                  phase=request.phase,
                  selected_text=request.selected_text,
                  full_context=request.full_context,
                  user_message=request.user_message,
                  conversation_history=request.conversation_history,
                  step_id=request.step_id
              ):
                  yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
              yield "data: {}\n\n"  # End marker
          
          return StreamingResponse(
              generate(),
              media_type="text/event-stream",
              headers={
                  "Cache-Control": "no-cache",
                  "Connection": "keep-alive",
              }
          )
          
      except Exception as e:
          logger.error(f"Editor chat error: {e}", exc_info=True)
          raise HTTPException(status_code=500, detail=str(e))
  
  
  @router.post("/editor/apply")
  async def editor_apply(request: EditorApplyRequest):
      """Apply changes to phase content."""
      try:
          editor_service = get_editor_service()
          result = await editor_service.apply_changes(
              batch_id=request.batch_id,
              phase=request.phase,
              selected_range=request.selected_range,
              replacement_text=request.replacement_text,
              step_id=request.step_id
          )
          return result
          
      except ValueError as e:
          raise HTTPException(status_code=404, detail=str(e))
      except Exception as e:
          logger.error(f"Editor apply error: {e}", exc_info=True)
          raise HTTPException(status_code=500, detail=str(e))
  ```

**File: `backend/app/main.py`**
- [ ] No changes needed - routes are automatically included via `app.include_router(research.router, prefix="/api/research")`

**Testing:**
- [ ] Test `/api/research/editor/chat` endpoint with Postman/curl
- [ ] Test `/api/research/editor/apply` endpoint
- [ ] Verify session.json is updated after apply

#### 1.4 Frontend Types & Interfaces

**File: `client/src/types/editor.ts`** (NEW)
- [ ] Create new types file:
  ```typescript
  export interface TextSelection {
    text: string
    start: number
    end: number
    phase: 'phase1' | 'phase2' | 'phase3' | 'phase4'
    stepId?: string  // For Phase 3
    element?: HTMLElement  // DOM element containing the selection
  }
  
  export interface EditorChatRequest {
    batch_id: string
    phase: string
    step_id?: string | null
    selected_text: string
    selected_range: { start: number; end: number }
    full_context: string
    user_message: string
    conversation_history?: Array<{role: string; content: string}>
  }
  
  export interface EditorChatResponse {
    response: string
    suggestions?: string[]  // Optional edit suggestions
  }
  
  export interface EditorApplyRequest {
    batch_id: string
    phase: string
    step_id?: string | null
    selected_range: { start: number; end: number }
    replacement_text: string
  }
  
  export interface EditorApplyResponse {
    status: 'success' | 'error'
    updated_content: string
    metadata: {
      edit_timestamp: string
      persisted: boolean
      will_affect_future_phases: boolean
      phase?: string
      step_id?: string | null
    }
    error?: string
  }
  
  export interface EditorMessage {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: string
  }
  ```

### Phase 2: Selection & UI Components (Week 1-2)

#### 2.1 Text Selection Utilities

**File: `client/src/utils/textSelection.ts`** (NEW)
- [ ] Create utility file with complete implementation:
  ```typescript
  import { TextSelection } from '../types/editor'

  /**
   * Get current text selection from DOM
   */
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

    // Find the container element (nearest content container)
    let container = range.commonAncestorContainer
    if (container.nodeType === Node.TEXT_NODE) {
      container = container.parentElement!
    }

    // Get full text content of container
    const containerText = container.textContent || ''
    
    // Calculate start/end positions relative to container
    const preRange = range.cloneRange()
    preRange.selectNodeContents(container)
    preRange.setEnd(range.startContainer, range.startOffset)
    const start = preRange.toString().length
    
    const end = start + selectedText.length

    return {
      text: selectedText,
      start,
      end,
      phase: 'phase1', // Will be set by caller
      element: container as HTMLElement
    }
  }

  /**
   * Get context around selection (surrounding text)
   */
  export function getSelectionContext(
    selection: TextSelection,
    contextChars: number = 500
  ): string {
    const element = selection.element
    if (!element) return ''

    const fullText = element.textContent || ''
    const contextStart = Math.max(0, selection.start - contextChars)
    const contextEnd = Math.min(fullText.length, selection.end + contextChars)
    
    return fullText.substring(contextStart, contextEnd)
  }

  /**
   * Highlight selected text in DOM
   */
  export function highlightSelection(
    selection: TextSelection,
    highlightId: string = 'editor-selection-highlight'
  ): () => void {
    // Remove existing highlights
    clearSelection(highlightId)

    const element = selection.element
    if (!element) return () => {}

    // Create highlight span
    const highlight = document.createElement('span')
    highlight.id = highlightId
    highlight.className = 'editor-selection-highlight'
    highlight.style.backgroundColor = '#FEC74A'
    highlight.style.padding = '2px 4px'
    highlight.style.borderRadius = '3px'
    highlight.style.fontWeight = '500'

    // This is a simplified version - in production, you'd need to
    // properly handle text node splitting and range insertion
    // For now, we'll use a simpler approach with data attributes
    
    return () => clearSelection(highlightId)
  }

  /**
   * Clear selection highlights
   */
  export function clearSelection(highlightId: string = 'editor-selection-highlight'): void {
    const existing = document.getElementById(highlightId)
    if (existing) {
      // Remove highlight but preserve text
      const parent = existing.parentNode
      if (parent) {
        parent.replaceChild(document.createTextNode(existing.textContent || ''), existing)
        parent.normalize()
      }
    }
  }

  /**
   * Get full context text from element
   */
  export function getFullContext(element: HTMLElement): string {
    return element.textContent || ''
  }
  ```

#### 2.2 API Service Integration

**File: `client/src/services/api.ts`**
- [ ] Add editor methods to `apiService` object:
  ```typescript
  import { 
    EditorChatRequest, 
    EditorApplyRequest, 
    EditorApplyResponse 
  } from '../types/editor'

  // Add to apiService object:
  
  /**
   * Chat with AI about selected content (streaming)
   */
  editorChat: async function* (
    request: EditorChatRequest
  ): AsyncGenerator<string, void, unknown> {
    const response = await fetch('/api/research/editor/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(`Editor chat failed: ${response.statusText}`)
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) {
      throw new Error('Response body is not readable')
    }

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data.trim() === '{}') continue // End marker
            
            try {
              const parsed = JSON.parse(data)
              if (parsed.type === 'token' && parsed.content) {
                yield parsed.content
              }
            } catch (e) {
              // Skip invalid JSON
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  },

  /**
   * Apply changes to phase content
   */
  applyEditorChanges: async function (
    request: EditorApplyRequest
  ): Promise<EditorApplyResponse> {
    const response = await api.post('/research/editor/apply', request)
    return response.data
  },
  ```

#### 2.3 Editor Chat Hook

**File: `client/src/hooks/useEditorChat.ts`** (NEW)
- [ ] Create hook for managing editor chat state:
  ```typescript
  import { useState, useCallback, useRef } from 'react'
  import { apiService } from '../services/api'
  import { EditorChatRequest, EditorApplyRequest, EditorMessage } from '../types/editor'

  interface UseEditorChatOptions {
    batchId: string
    phase: string
    stepId?: string | null
    onApplySuccess?: (updatedContent: string) => void
    onError?: (error: Error) => void
  }

  export function useEditorChat(options: UseEditorChatOptions) {
    const { batchId, phase, stepId, onApplySuccess, onError } = options
    
    const [messages, setMessages] = useState<EditorMessage[]>([])
    const [isLoading, setIsLoading] = useState(false)
    const [currentResponse, setCurrentResponse] = useState('')
    const [isStreaming, setIsStreaming] = useState(false)
    const abortControllerRef = useRef<AbortController | null>(null)

    const sendMessage = useCallback(async (
      selectedText: string,
      selectedRange: { start: number; end: number },
      fullContext: string,
      userMessage: string
    ) => {
      if (isLoading) return

      setIsLoading(true)
      setIsStreaming(true)
      setCurrentResponse('')

      // Add user message
      const userMsg: EditorMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: userMessage,
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, userMsg])

      try {
        const request: EditorChatRequest = {
          batch_id: batchId,
          phase,
          step_id: stepId || null,
          selected_text: selectedText,
          selected_range: selectedRange,
          full_context: fullContext,
          user_message: userMessage,
          conversation_history: messages.map(m => ({
            role: m.role,
            content: m.content
          }))
        }

        // Stream response
        let fullResponse = ''
        for await (const chunk of apiService.editorChat(request)) {
          fullResponse += chunk
          setCurrentResponse(fullResponse)
        }

        // Add assistant message
        const assistantMsg: EditorMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: fullResponse,
          timestamp: new Date().toISOString()
        }
        setMessages(prev => [...prev, assistantMsg])
        setCurrentResponse('')

      } catch (error) {
        console.error('Editor chat error:', error)
        if (onError) {
          onError(error as Error)
        }
      } finally {
        setIsLoading(false)
        setIsStreaming(false)
      }
    }, [batchId, phase, stepId, messages, isLoading, onError])

    const applyChanges = useCallback(async (
      selectedRange: { start: number; end: number },
      replacementText: string
    ) => {
      try {
        const request: EditorApplyRequest = {
          batch_id: batchId,
          phase,
          step_id: stepId || null,
          selected_range: selectedRange,
          replacement_text: replacementText
        }

        const response = await apiService.applyEditorChanges(request)
        
        if (response.status === 'success' && onApplySuccess) {
          onApplySuccess(response.updated_content)
        }

        return response
      } catch (error) {
        console.error('Apply changes error:', error)
        if (onError) {
          onError(error as Error)
        }
        throw error
      }
    }, [batchId, phase, stepId, onApplySuccess, onError])

    const clearMessages = useCallback(() => {
      setMessages([])
      setCurrentResponse('')
    }, [])

    return {
      messages,
      currentResponse,
      isLoading,
      isStreaming,
      sendMessage,
      applyChanges,
      clearMessages
    }
  }
  ```

#### 2.4 ContentEditorPanel Component

**File: `client/src/components/editor/ContentEditorPanel.tsx`** (NEW)
- [ ] Create component directory: `client/src/components/editor/`
- [ ] Create component file:
  ```typescript
  import React, { useState, useRef, useEffect } from 'react'
  import { TextSelection } from '../../types/editor'
  import { useEditorChat } from '../../hooks/useEditorChat'
  import Button from '../common/Button'

  interface ContentEditorPanelProps {
    selection: TextSelection
    batchId: string
    onClose: () => void
    onApply: (replacement: string) => Promise<void>
    position?: { top: number; left: number }
  }

  export const ContentEditorPanel: React.FC<ContentEditorPanelProps> = ({
    selection,
    batchId,
    onClose,
    onApply,
    position
  }) => {
    const [userMessage, setUserMessage] = useState('')
    const [replacementText, setReplacementText] = useState('')
    const panelRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLTextAreaElement>(null)

    const {
      messages,
      currentResponse,
      isLoading,
      isStreaming,
      sendMessage,
      applyChanges,
      clearMessages
    } = useEditorChat({
      batchId,
      phase: selection.phase,
      stepId: selection.stepId,
      onApplySuccess: async (updatedContent) => {
        // Refresh phase display (handled by parent)
        await onApply(replacementText || currentResponse)
        onClose()
      },
      onError: (error) => {
        console.error('Editor error:', error)
        // Show error notification
      }
    })

    // Update replacement text when AI responds
    useEffect(() => {
      if (currentResponse && !isStreaming) {
        setReplacementText(currentResponse)
      }
    }, [currentResponse, isStreaming])

    // Position panel near selection
    useEffect(() => {
      if (panelRef.current && selection.element && !position) {
        const rect = selection.element.getBoundingClientRect()
        const panel = panelRef.current
        panel.style.top = `${rect.bottom + 10}px`
        panel.style.left = `${rect.left}px`
      }
    }, [selection, position])

    const handleSend = async () => {
      if (!userMessage.trim() || isLoading) return

      const fullContext = selection.element?.textContent || ''
      await sendMessage(
        selection.text,
        { start: selection.start, end: selection.end },
        fullContext,
        userMessage
      )
      setUserMessage('')
    }

    const handleApply = async () => {
      if (!replacementText.trim()) return
      
      await applyChanges(
        { start: selection.start, end: selection.end },
        replacementText
      )
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
      if (e.key === 'Escape') {
        onClose()
      }
    }

    return (
      <div
        ref={panelRef}
        className="fixed z-50 w-96 bg-white rounded-lg shadow-xl border border-gray-200"
        style={position ? { top: position.top, left: position.left } : {}}
      >
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">编辑内容</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>

        {/* Selected Text Preview */}
        <div className="px-4 py-3 bg-yellow-50 border-b border-gray-200">
          <div className="text-xs font-medium text-gray-700 mb-1">选中的文本：</div>
          <div className="text-sm text-gray-900 bg-yellow-100 p-2 rounded">
            {selection.text}
          </div>
        </div>

        {/* Messages */}
        <div className="px-4 py-3 max-h-64 overflow-y-auto">
          {messages.length === 0 && !currentResponse && (
            <div className="text-sm text-gray-500 text-center py-4">
              输入问题或修改请求...
            </div>
          )}
          
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`mb-3 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}
            >
              <div
                className={`inline-block px-3 py-2 rounded-lg text-sm ${
                  msg.role === 'user'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}

          {currentResponse && (
            <div className="mb-3 text-left">
              <div className="inline-block px-3 py-2 rounded-lg text-sm bg-gray-100 text-gray-900">
                {currentResponse}
                {isStreaming && <span className="animate-pulse">▋</span>}
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="px-4 py-3 border-t border-gray-200">
          <textarea
            ref={inputRef}
            value={userMessage}
            onChange={(e) => setUserMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入问题或修改请求..."
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            rows={2}
            disabled={isLoading}
          />
          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-gray-500">Shift+Enter 换行，Enter 发送</span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={onClose}
                disabled={isLoading}
              >
                取消
              </Button>
              <Button
                size="sm"
                variant="primary"
                onClick={handleSend}
                disabled={isLoading || !userMessage.trim()}
              >
                {isLoading ? '发送中...' : '发送'}
              </Button>
            </div>
          </div>
        </div>

        {/* Apply Changes Section */}
        {replacementText && (
          <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
            <div className="text-xs font-medium text-gray-700 mb-2">修改后的文本：</div>
            <div className="text-sm text-gray-900 bg-white p-2 rounded border border-gray-200 mb-2">
              {replacementText}
            </div>
            <Button
              size="sm"
              variant="primary"
              onClick={handleApply}
              disabled={isLoading}
              className="w-full"
            >
              应用修改
            </Button>
          </div>
        )}
      </div>
    )
  }
  ```

#### 2.5 Selection Integration

**File: `client/src/components/streaming/StreamDisplay.tsx`**
- [ ] Add selection support:
  ```typescript
  // Add imports
  import { useState, useCallback } from 'react'
  import { getTextSelection, TextSelection } from '../../utils/textSelection'
  import { ContentEditorPanel } from '../editor/ContentEditorPanel'
  import { useWorkflowStore } from '../../stores/workflowStore'

  // Add state inside component
  const [selection, setSelection] = useState<TextSelection | null>(null)
  const batchId = useWorkflowStore((state) => state.batchId)

  // Add selection handler
  const handleTextSelect = useCallback(() => {
    const sel = getTextSelection()
    if (sel && sel.text.trim().length > 0) {
      // Determine phase from props or context
      sel.phase = phase || 'phase1'
      setSelection(sel)
    }
  }, [phase])

  // Add mouseup listener to content area
  useEffect(() => {
    const contentArea = streamRef.current
    if (!contentArea) return

    contentArea.addEventListener('mouseup', handleTextSelect)
    return () => {
      contentArea.removeEventListener('mouseup', handleTextSelect)
    }
  }, [handleTextSelect])

  // Add editor panel render
  {selection && batchId && (
    <ContentEditorPanel
      selection={selection}
      batchId={batchId}
      onClose={() => setSelection(null)}
      onApply={async (replacement) => {
        // Trigger content refresh
        // This will be handled by parent component or store update
        setSelection(null)
      }}
    />
  )}
  ```

**File: `client/src/components/phase3/Phase3StepContent.tsx`**
- [ ] Add similar selection support (check file structure first)
- [ ] Import and integrate `ContentEditorPanel`
- [ ] Add `stepId` to selection when creating it

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
          # 1. Load ResearchSession for batch_id
          # 2. Load phase artifact: session.get_phase_artifact(phase_key)
          # 3. Extract content from artifact for context
          # 4. Construct prompt with context
          # 5. Call Qwen-Plus API
          # 6. Stream response
      
      async def apply_changes(
          self,
          batch_id: str,
          phase: str,
          selected_range: dict,
          replacement_text: str,
          step_id: Optional[str] = None
      ) -> dict:
          """Apply changes to phase content and immediately persist.
          
          CRITICAL: This method saves changes via session.save_phase_artifact(),
          which means:
          - Changes are immediately persisted to session.json
          - Future phases (when they run) will automatically use the edited content
          - No need to manually trigger phase re-runs - edits are live
          """
          # 1. Load ResearchSession for batch_id
          # 2. Load current phase artifact: session.get_phase_artifact(phase_key)
          # 3. Extract content string from artifact (handle different artifact structures)
          # 4. Replace selected range with replacement_text
          # 5. Update artifact with new content (preserve other artifact fields)
          # 6. Save via session.save_phase_artifact(phase_key, updated_artifact, autosave=True)
          #    → This immediately persists to session.json
          #    → Future phases will use edited content when they load artifacts
          # 7. Return updated content + metadata confirming persistence
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
    "edit_count": 1,
    "persisted": true,  // Confirms changes saved to session.json
    "will_affect_future_phases": true  // Confirms future phases will use edited content
  }
}
```

**Important:** This endpoint immediately persists changes to the session file via `session.save_phase_artifact()`. Any subsequent phase execution (Phase 2, 3, or 4) will automatically use the edited content when loading artifacts.

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
No changes to existing batch structure. Editor changes are applied directly to phase artifacts in the session file, which are immediately persisted and will be used by subsequent phases.

**Critical: Immediate Persistence & Phase Propagation**

When a user edits content (e.g., edits a research goal in Phase 1), the changes are:
1. **Immediately saved** to the session JSON file via `session.save_phase_artifact(phase_key, updated_data, autosave=True)`
2. **Automatically used** by future phases when they load artifacts using `session.get_phase_artifact(phase_key)`

**Example Flow:**
- User edits Phase 1 research goal → `EditorService.apply_changes()` updates Phase 1 artifact
- Changes saved via `session.save_phase_artifact("phase1", updated_artifact)`
- When Phase 2 runs, it loads: `phase1_artifact = session.get_phase_artifact("phase1")`
- Phase 2 will use the **edited** Phase 1 content automatically

**Session File Structure:**
```
data/research/batches/{batch_id}/session.json
{
  "phase_artifacts": {
    "phase1": {
      "data": { /* Updated content after edit */ },
      "updated_at": "2025-11-19T12:34:56Z"
    },
    "phase2": { ... },
    "phase3": { ... },
    "phase4": { ... }
  }
}
```

**Note:** The session file is the single source of truth. All phases load from `session.get_phase_artifact()`, so edits are immediately effective for future phases.

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

---

## Implementation Checklist Summary

### Files to Create (NEW)

**Backend:**
1. `backend/app/services/editor_service.py` - Editor service implementation
2. `research/prompts/editor/system.md` - System prompt for editor

**Frontend:**
3. `client/src/types/editor.ts` - TypeScript type definitions
4. `client/src/utils/textSelection.ts` - Text selection utilities
5. `client/src/hooks/useEditorChat.ts` - Editor chat hook
6. `client/src/components/editor/ContentEditorPanel.tsx` - Main editor panel component

### Files to Modify

**Backend:**
1. `config.yaml` - Add `qwen.editor.*` configuration
2. `core/config.py` - Add `get_editor_config()` method
3. `backend/app/routes/research.py` - Add `/editor/chat` and `/editor/apply` endpoints

**Frontend:**
4. `client/src/services/api.ts` - Add `editorChat()` and `applyEditorChanges()` methods
5. `client/src/components/streaming/StreamDisplay.tsx` - Add text selection support
6. `client/src/components/phase3/Phase3StepContent.tsx` - Add text selection support (if exists)

### Configuration Changes

1. **config.yaml**: Add editor model configuration
2. **No database changes required** - Uses existing session.json structure
3. **No new dependencies** - Reuses existing Qwen client and session management

### Testing Requirements

**Backend Tests:**
- [ ] Test `EditorService.chat_with_selection()` with mock Qwen client
- [ ] Test `EditorService.apply_changes()` with sample artifacts
- [ ] Test API endpoints with Postman/curl
- [ ] Verify session.json updates after apply

**Frontend Tests:**
- [ ] Test text selection utilities
- [ ] Test `useEditorChat` hook
- [ ] Test `ContentEditorPanel` component rendering
- [ ] Test integration with `StreamDisplay` and `Phase3StepContent`

**Integration Tests:**
- [ ] Full flow: Select → Chat → Apply → Verify session.json update
- [ ] Test with Phase 1, 2, 3, 4 content
- [ ] Test with Phase 3 step content
- [ ] Verify future phases use edited content

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-19  
**Author**: AI Assistant  
**Status**: Draft - Pending Review

