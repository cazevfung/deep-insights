# Deep Research Agent - Plan Summary

## What Was Analyzed

1. **Original Plan**: `DEEP_RESEARCH_PLAN.md` - 4-phase workflow for deep research
2. **Scraped Data**: Results from `tests/results/run_251029_150500/` showing actual data structures
3. **Requirements**: Integration with Qwen3-max streaming API (流式输出) for real-time feedback

## Key Enhancements in the Enhanced Plan

### 1. **Streaming API Integration**
- **Original**: Non-streaming API calls, user waits for complete response
- **Enhanced**: Real-time token-by-token streaming output
- **Benefits**: 
  - User sees agent "thinking" in real-time
  - Progress indicators during long operations
  - Better UX for multi-minute operations

### 2. **Multi-Source Data Handling**
- **Original**: Assumed single source (video transcript + comments)
- **Enhanced**: Supports multiple sources with different formats:
  - YouTube: Transcripts + comment arrays
  - Bilibili: Transcripts + structured comments (with likes)
  - Reddit: Article content with embedded comments
  - Articles: Plain text content
- **Benefits**: Can research across platforms, compare viewpoints

### 3. **Data Structure Mapping**
- **Original**: Generic "transcript" and "comments" format
- **Enhanced**: Matches actual scraped file structure:
  - Batch ID tracking (`batch_id`, `link_id`)
  - Source-specific comment formats
  - Metadata preservation (title, author, word_count, etc.)
  - Unified data abstraction layer

### 4. **Chunking Strategies**
- **Original**: Simple sequential chunking
- **Enhanced**: Multiple chunking strategies:
  - `sequential`: Sequential processing
  - `semantic_chunks`: Topic-based splitting
  - `random_sample`: Random sampling for comments
  - `top_by_likes`: Prioritize high-engagement comments (Bilibili)
  - `all`: Send complete data when feasible

### 5. **Progress Tracking**
- **Original**: No explicit progress tracking
- **Enhanced**: Comprehensive progress system:
  - Real-time step completion status
  - Progress bars and percentage completion
  - Streaming output display
  - Scratchpad accumulation visualization

### 6. **Chinese Language Support**
- **Original**: Prompts in English
- **Enhanced**: All prompts and output in Chinese:
  - Matches UI language preference
  - Better for analyzing Chinese content (Bilibili)
  - Consistent user experience

### 7. **Robust Error Handling**
- **Original**: Basic error handling assumed
- **Enhanced**: Specific handling for:
  - Partial JSON runs during streaming
  - Large data token limits
  - Missing data scenarios
  - Multi-source data mismatches

## Architecture Decisions

### Data Flow
```
Scraped Results (JSON files)
    ↓
Data Loader (Phase 0)
    ↓
Unified Data Structure
    ↓
Abstract Generator
    ↓
Streaming API Calls (Phases 1-4)
    ↓
Real-time UI Updates
    ↓
Final Report (Markdown)
```

### Component Structure
```
research_agent/
├── core/
│   ├── qwen_streaming_client.py    # Streaming API integration
│   ├── research_data_loader.py     # Batch data loading
│   └── progress_tracker.py         # Progress tracking
├── phases/
│   ├── phase1_discover.py          # Goal generation
│   ├── phase2_plan.py              # Plan creation
│   ├── phase3_execute.py           # Execution loop
│   └── phase4_synthesize.py        # Report generation
└── ui/
    ├── console_interface.py        # Console UI with streaming
    └── web_interface.py            # Future web UI
```

## Workflow Comparison

### Original Workflow
1. **Phase 1**: Generate goals (1 API call, wait for JSON)
2. **Phase 2**: Create plan (1 API call, wait for JSON)
3. **Phase 3**: Execute steps (multiple calls, wait for each)
4. **Phase 4**: Generate report (1 API call, wait for markdown)

**User Experience**: Mostly waiting with minimal feedback

### Enhanced Workflow
1. **Phase 0**: Load & normalize data (Python, instant feedback)
2. **Phase 1**: Generate goals (streaming, see suggestions appear)
3. **Phase 2**: Create plan (streaming, see plan build step-by-step)
4. **Phase 3**: Execute steps (streaming + progress, real-time findings)
5. **Phase 4**: Generate report (streaming, watch report generate)

**User Experience**: Continuous feedback, feels interactive

## Implementation Phases

### Phase 0: Foundation (Priority 1)
- [ ] Implement `ResearchDataLoader` to handle batch data
- [ ] Create unified data structure
- [ ] Implement data abstraction generation

### Phase 1: Streaming Client (Priority 1)
- [ ] Implement `QwenStreamingClient` using official docs
- [ ] Handle streaming JSON parsing
- [ ] Implement callback system for UI updates

### Phase 2: Core Phases (Priority 2)
- [ ] Phase 1: Goal generation with streaming
- [ ] Phase 2: Plan creation with streaming
- [ ] Phase 3: Execution loop with progress tracking
- [ ] Phase 4: Report generation with streaming

### Phase 3: User Interface (Priority 2)
- [ ] Console interface with streaming display
- [ ] Progress indicators
- [ ] Error handling and retry logic

### Phase 4: Advanced Features (Priority 3)
- [ ] Multi-source research aggregation
- [ ] Web-based UI with WebSocket
- [ ] Export options (PDF, DOCX)
- [ ] Research session history

## Key Technical Challenges

1. **Streaming JSON Parsing**
   - Need to buffer tokens until complete JSON detected
   - Handle malformed JSON gracefully
   - Retry mechanism if JSON invalid

2. **Token Management**
   - Count tokens before sending
   - Split large chunks automatically
   - Cache intermediate results

3. **Multi-Source Data Normalization**
   - Different comment formats
   - Missing data handling
   - Source-specific metadata extraction

4. **Real-time UI Updates**
   - Thread-safe streaming display
   - Progress bar updates
   - Error display during streaming

## Testing Strategy

1. **Unit Tests**: Each component in isolation
2. **Integration Tests**: Full workflow with mock API
3. **Data Tests**: Real scraped data from `run_251029_150500`
4. **Streaming Tests**: Verify JSON parsing from streams
5. **Error Tests**: Missing data, API failures, invalid JSON

## Next Steps

1. Review this enhanced plan for accuracy
2. Confirm Qwen3-max streaming API documentation access
3. Start with Phase 0 (Data Loading) implementation
4. Iteratively build phases 1-4 with streaming support
5. Test with actual scraped data

---

## Resolved Implementation Details

1. **API Authentication**: 
   - API Key: Provided by user (stored securely)
   - Environment variable: `DASHSCOPE_API_KEY` or `QWEN_API_KEY`
   - Can also be passed directly to client constructor

2. **Streaming Format**: 
   - Protocol: Server-Sent Events (SSE)
   - Uses OpenAI-compatible SDK with DashScope endpoints
   - Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1` (Beijing)
   - Alternative: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` (Singapore)
   - Each chunk: `chunk.choices[0].delta.content`
   - Usage info: Last chunk with `stream_options={"include_usage": True}`

3. **Token Limits**: 
   - Maximum: 32,000 tokens per request for qwen-max

4. **Error Recovery**: 
   - Need to implement: Stream interruption handling
   - Best practice: Save progress to scratchpad incrementally
   - Can restart from last completed step if needed

## Remaining Questions

1. **Rate Limiting**: Are there API rate limits? Should we implement throttling or request queuing?
2. **Cost Tracking**: Should we track and display token usage per phase?
3. **Thinking Mode**: Should we enable `enable_thinking` for deeper reasoning in certain phases?

---

*See `DEEP_RESEARCH_PLAN_ENHANCED.md` for full technical details.*



