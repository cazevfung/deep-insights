# Suggested Questions Feature Plan

## 1. Background & Goals

- **Problem**: Users may struggle to formulate follow-up questions in the right-column chat, especially after receiving AI responses or when exploring session data. This can lead to underutilization of the chat feature and missed opportunities for deeper exploration.
- **Goal**: Add a suggested questions section above the user input text box that dynamically generates 3 contextually relevant questions based on:
  - User's latest input
  - AI's latest answers
  - Current session information (phase, goals, findings, etc.)
- **Value**: Improve user engagement, guide conversation flow, and help users discover relevant questions they might not have thought of.

## 2. Proposed Flow (High-Level)

1. **User interacts with chat** (sends message, receives AI response, or session state changes)
2. **Frontend detects trigger** for refreshing suggestions (new message, new AI response, session update)
3. **Frontend requests suggestions** from backend API endpoint
4. **Backend generates suggestions** using qwen-flash model with context from:
   - Recent conversation history (last N messages)
   - Latest AI response content
   - Session metadata (current phase, research goals, Phase 3 findings, etc.)
5. **Backend returns 3 suggested questions** as JSON array
6. **Frontend displays suggestions** above the textarea input box
7. **User clicks a suggestion** → populates textarea and optionally auto-sends or allows editing

## 3. Model Selection: qwen-flash

**Decision: Yes, use qwen-flash for smart question generation**

**Rationale:**
- qwen-flash is already used in the codebase for summarization tasks (see `config.yaml` line 139)
- Fast and cost-effective for generating short question suggestions
- Good balance between quality and latency for real-time UX
- Can handle context understanding needed for relevant suggestions
- Lower token costs compared to larger models (qwen3-max, qwen-plus)

**Alternative Considered:**
- Rule-based templates: Too rigid, won't adapt to context
- Static question bank: Not contextual enough
- Larger models (qwen-plus, qwen3-max): Overkill for this use case, slower, more expensive

## 4. Feature Scope

### 4.1 Scope In
- Right-column chat suggested questions component
- Backend API endpoint for generating suggestions
- Integration with conversation history
- Integration with session metadata
- Real-time refresh on conversation/session updates
- Click-to-use functionality (populate textarea)

### 4.2 Scope Out
- Question history/persistence
- User feedback on suggestion quality (for now)
- Customization of suggestion count (fixed at 3)
- Multi-language support (Chinese only for now)

**Note**: Auto-send on click is implemented (user decision: AUTO-SEND)

## 5. Detailed Implementation Plan

### 5.1 Frontend: Suggested Questions Component

#### 5.1.1 Component Structure
**Location**: `client/src/components/phaseCommon/SuggestedQuestions.tsx`

**Props:**
```typescript
interface SuggestedQuestionsProps {
  batchId: string | null
  sessionId: string | null
  conversationMessages: ConversationMessage[]
  onQuestionClick: (question: string) => void
  disabled?: boolean
}
```

**Features:**
- Display 3 suggested questions as clickable chips/buttons
- Loading state while fetching suggestions
- Empty state when no suggestions available
- Error state with retry option
- Smooth animations for appearance/disappearance

#### 5.1.2 Integration with PhaseInteractionPanel

**Location**: `client/src/components/phaseCommon/PhaseInteractionPanel.tsx`

**Changes:**
1. Add `SuggestedQuestions` component above the textarea (in footer section, before the input box)
2. Pass required props:
   - `batchId` from `useWorkflowStore`
   - `sessionId` from `useWorkflowStore`
   - `conversationMessages` from `useWorkflowStore`
   - `onQuestionClick` handler that sets draft state
3. Add refresh triggers:
   - When new user message is sent
   - When new AI response is received (via WebSocket or state update)
   - When session state changes (phase transitions, new findings)
   - Debounce rapid updates (e.g., 500ms debounce)

**UI Placement:**
```
<footer>
  {pendingContextRequests...}
  
  <SuggestedQuestions
    batchId={batchId}
    sessionId={sessionId}
    conversationMessages={conversationMessages}
    onQuestionClick={(q) => setDraft(q)}
    disabled={isConversationSending || !batchId}
  />
  
  <div className="textarea-container">
    <textarea ... />
  </div>
</footer>
```

#### 5.1.3 State Management

**Hook**: `client/src/hooks/useSuggestedQuestions.ts`

**Responsibilities:**
- Fetch suggestions from backend API
- Manage loading/error states
- Cache suggestions with TTL (e.g., 30 seconds)
- Debounce refresh requests
- Handle empty/invalid responses

**API Integration:**
```typescript
const fetchSuggestions = async (
  batchId: string,
  sessionId: string | null,
  conversationMessages: ConversationMessage[]
): Promise<string[]> => {
  const response = await apiService.getSuggestedQuestions({
    batch_id: batchId,
    session_id: sessionId ?? undefined,
    conversation_context: conversationMessages.slice(-10), // Last 10 messages
  })
  return response.questions || []
}
```

### 5.2 Backend: Suggested Questions API

#### 5.2.1 API Endpoint

**Route**: `POST /research/conversation/suggest-questions`

**Request Body:**
```typescript
{
  batch_id: string
  session_id?: string
  conversation_context: Array<{
    role: 'user' | 'assistant'
    content: string
    timestamp: string
  }>
}
```

**Response:**
```typescript
{
  questions: string[]  // Array of exactly 3 questions
  generated_at: string
  model_used: string  // "qwen-flash"
}
```

**Error Handling:**
- 400: Invalid batch_id or missing required fields
- 404: Batch not found
- 500: Model generation error (return empty array or fallback questions)

#### 5.2.2 Implementation Location

**File**: `backend/app/routes/conversation.py` (or create new file if needed)

**Function**: `suggest_questions_endpoint()`

**Dependencies:**
- Access to conversation history from batch storage
- Access to session metadata (via session_id)
- Qwen client for calling qwen-flash model
- Prompt template for question generation

#### 5.2.3 Prompt Engineering

**Prompt Template**: `research/prompts/right_column_chat/suggest_questions.md`

**Context to Include:**
1. **Recent Conversation** (last 5-10 messages)
   - User questions
   - AI responses
   - Format: "User: ...\nAssistant: ..."

2. **Session Context**
   - Current phase
   - Research goals (synthesized_goal)
   - Phase 3 summary (if available)
   - Phase 3 points of interest (if available)
   - Current action/status

3. **Instructions**
   - Generate exactly 3 follow-up questions
   - Questions should be:
     - Relevant to the conversation context
     - Helpful for exploring the research topic
     - Diverse (not repetitive)
     - Concise (one sentence each)
     - In Chinese
   - Avoid questions already asked in recent conversation
   - Focus on deepening understanding or exploring new angles

**Example Prompt Structure:**
```
你是一个智能研究助手。基于以下对话历史和会话信息，生成3个相关的后续问题。

## 对话历史
${conversation_history}

## 会话信息
- 当前阶段: ${current_phase}
- 研究目标: ${synthesized_goal}
- Phase 3 摘要: ${phase3_summary}
- Phase 3 兴趣点: ${phase3_points}

## 要求
1. 生成恰好3个问题
2. 问题应该与对话上下文相关
3. 问题应该有助于探索研究主题
4. 问题应该多样化，不重复
5. 每个问题应该简洁（一句话）
6. 避免重复最近对话中已经问过的问题
7. 专注于深化理解或探索新角度

请直接返回3个问题，每行一个问题，不要编号，不要额外说明。
```

#### 5.2.4 Model Configuration

**Model**: `qwen-flash` (from config)

**Parameters:**
- `temperature`: 0.7 (balanced creativity)
- `max_tokens`: 200 (questions are short)
- `top_p`: 0.9

**Cost Considerations:**
- qwen-flash is cost-effective for this use case
- Cache suggestions to avoid redundant calls
- Debounce on frontend to limit request frequency
- Consider rate limiting if needed

#### 5.2.5 Session Data Access

**Data Sources:**
1. **Conversation History**
   - From batch conversation log: `data/research/conversations/{batch_id}.json`
   - Or from in-memory state if available

2. **Session Metadata**
   - From session file: `data/research/sessions/session_{session_id}.json`
   - Extract:
     - `current_phase`
     - `synthesized_goal`
     - `phase_artifacts.phase3.summary`
     - `phase_artifacts.phase3.points_of_interest`
     - `current_action` (if available)

3. **Fallback Behavior**
   - If session_id not provided: use batch-level data only
   - If session file not found: skip session-specific context
   - If conversation history empty: generate generic starter questions

### 5.3 Refresh Triggers

#### 5.3.1 Frontend Triggers

**When to Refresh:**
1. **New User Message Sent**
   - After `handleConversationSend` completes
   - Wait for AI response before refreshing (to include AI answer in context)

2. **New AI Response Received**
   - On WebSocket event: `conversation:message` or `conversation:delta`
   - When `conversationMessages` state updates with new assistant message
   - Debounce: 500ms after last update

3. **Session State Changes**
   - Phase transitions (detected via `phase` from `usePhaseInteraction`)
   - New Phase 3 findings (if available via WebSocket or state)
   - Research goal updates

4. **Manual Refresh**
   - Optional: "Refresh" button in component (low priority)

**Debouncing Strategy:**
- Use `useDebounce` hook or `lodash.debounce`
- Debounce time: 500ms
- Cancel pending requests if new trigger arrives

#### 5.3.2 Backend Caching

**Cache Strategy:**
- Cache suggestions per `(batch_id, session_id, conversation_hash)`
- TTL: 30 seconds
- Conversation hash: hash of last 5 messages (to detect changes)
- Invalidate on new messages

**Implementation:**
- Use in-memory cache (dict) for simplicity
- Key: `f"suggestions:{batch_id}:{session_id}:{conversation_hash}"`
- Store: `{questions: [], generated_at: timestamp, expires_at: timestamp}`

### 5.4 UI/UX Design

#### 5.4.1 Visual Design

**Layout:**
- Horizontal row of 3 question chips/buttons
- Above textarea, below context requests (if any)
- Compact design to not take too much vertical space

**Styling:**
- Question chips: rounded, subtle background (e.g., `bg-neutral-50` or `bg-primary-50`)
- Hover effect: slight elevation or background change
- Click effect: brief animation
- Loading state: skeleton placeholders or spinner
- Empty state: hide component (no suggestions available)

**Responsive:**
- On narrow screens: stack vertically or show fewer questions
- Maintain readability and clickability

#### 5.4.2 Interaction Design

**Click Behavior:**
1. User clicks a suggested question
2. Question is automatically sent immediately (AUTO-SEND)
3. Message appears in conversation timeline
4. No editing step - question is sent as-is for faster interaction

**Accessibility:**
- Keyboard navigation support
- ARIA labels for screen readers
- Clear visual feedback on hover/focus

### 5.5 API Service Integration

#### 5.5.1 Frontend API Service

**File**: `client/src/services/api.ts`

**New Method:**
```typescript
getSuggestedQuestions: async (payload: {
  batch_id: string
  session_id?: string
  conversation_context: Array<{
    role: 'user' | 'assistant'
    content: string
    timestamp: string
  }>
}): Promise<{
  questions: string[]
  generated_at: string
  model_used: string
}>
```

**Implementation:**
- POST to `/research/conversation/suggest-questions`
- Handle errors gracefully
- Return empty array on error (fallback)

## 6. Implementation Phases

### Phase 1: Backend Foundation
1. Create API endpoint skeleton
2. Implement prompt template
3. Integrate qwen-flash model call
4. Add session data access helpers
5. Implement basic caching
6. Test with mock data

### Phase 2: Frontend Component
1. Create `SuggestedQuestions` component
2. Create `useSuggestedQuestions` hook
3. Add API service method
4. Implement loading/error states
5. Add basic styling

### Phase 3: Integration
1. Integrate component into `PhaseInteractionPanel`
2. Add refresh triggers
3. Implement debouncing
4. Test end-to-end flow

### Phase 4: Polish
1. Refine prompt engineering
2. Optimize caching strategy
3. Improve UI/UX
4. Add error handling and fallbacks
5. Performance testing

## 7. Technical Considerations

### 7.1 Performance
- **Debouncing**: Prevent excessive API calls
- **Caching**: Reduce redundant model calls
- **Lazy Loading**: Only fetch when component is visible
- **Request Cancellation**: Cancel pending requests on new triggers

### 7.2 Error Handling
- **Network Errors**: Show retry option or hide component
- **Model Errors**: Return empty array, log error
- **Invalid Responses**: Validate response format, fallback to empty array
- **Missing Data**: Gracefully degrade (use available context only)

### 7.3 Cost Management
- **Rate Limiting**: Consider backend rate limits if needed
- **Caching**: Aggressive caching to reduce API calls
- **Debouncing**: Limit request frequency
- **Model Selection**: qwen-flash is already cost-effective

### 7.4 Security
- **Input Validation**: Validate batch_id, session_id
- **Authorization**: Ensure user has access to batch/session
- **Sanitization**: Sanitize conversation context before sending to model

## 8. Testing Strategy

### 8.1 Unit Tests
- Component rendering
- Hook logic (fetching, caching, debouncing)
- API service method
- Prompt generation

### 8.2 Integration Tests
- End-to-end flow: user sends message → suggestions refresh
- Session state changes → suggestions update
- Error scenarios (network errors, invalid responses)

### 8.3 Manual Testing
- Test with various conversation contexts
- Test with different session states
- Test refresh triggers
- Test UI responsiveness

## 9. Future Enhancements (Out of Scope)

1. **User Feedback**: Allow users to rate suggestions (thumbs up/down)
2. **Learning**: Use feedback to improve suggestions over time
3. **Customization**: Allow users to adjust suggestion count or style
4. **History**: Show previously used suggestions
5. **Multi-language**: Support English and other languages
6. **Smart Timing**: Only show suggestions when user is idle (not typing)

## 10. Open Questions

1. **Auto-send on click**: Should clicking a suggestion auto-send, or just populate textarea? (Decision: AUTO-SEND - implemented)
2. **Suggestion count**: Fixed at 3, or configurable? (Decision: Fixed at 3 for MVP)
3. **Refresh frequency**: How often should suggestions refresh? (Decision: On conversation/session changes, with debouncing)
4. **Fallback questions**: Should we have static fallback questions when model fails? (Decision: Yes, generic starter questions, starter questions should also be produced based on session data)
5. **Visibility**: Should suggestions be hidden when user is actively typing? (Decision: Keep visible, but don't refresh while typing)

---

**Next Action**: Review plan with stakeholders, then proceed with Phase 1 implementation.

