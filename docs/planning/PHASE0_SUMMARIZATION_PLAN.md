# Phase 0 Summarization Plan: Reducing Truncation Through Intelligent Summarization

## Problem Statement

**Current Issue**: Excessive truncation in Phase 3 is wasting valuable source data:
- Comments are hardcoded to truncate at 15,000 chars (from 271,482 chars = only 5.5% utilization!)
- Even with `max_transcript_chars=0` (no limit), comments are still heavily truncated
- Qwen doesn't know what content it's missing because it only sees truncated samples
- The purpose of collecting extensive comment data is defeated by aggressive truncation

**Root Cause**: 
- Phase 3 sends initial data chunks to Qwen, but these chunks are truncated before Qwen can see what's available
- Qwen can't request specific content items because it doesn't have a summary/index of what's available
- The retrieval system exists but isn't being used effectively because Qwen doesn't know what to request

## Solution Overview

**Core Idea**: Add a summarization step in Phase 0 that extracts **lists of key facts, opinions, and data points** for each content item using qwen-flash (fast, cheap model). These lists serve as **markers** that:
1. **List** all major facts, opinions, and datapoints from each content item (not narrative summaries)
2. Act as **markers** for the AI to quickly understand what's available in that item
3. Be saved in each respective JSON file for easy retrieval
4. Be sent to Qwen initially instead of truncated raw content
5. Allow Qwen to request full content items based on marker relevance when more context is needed

**Benefits**:
- **Less truncation**: Initial batch uses marker lists (small, complete) instead of truncated raw content
- **Better context awareness**: Qwen can quickly scan lists to understand what's available in each content item
- **Targeted retrieval**: Qwen can request specific content items based on marker relevance
- **Full utilization**: All content items can be accessed when needed, not lost to truncation
- **Quick scanning**: Lists are scannable without reading full content, enabling faster decision-making

---

## Architecture Changes

### 1. New Phase 0 Step: Content Summarization

**Location**: `research/phases/phase0_prepare.py` or new `research/phases/phase0_summarize.py`

**When**: After loading batch data, before creating abstracts

**What**: For each content item, use qwen-flash to extract a **list** of key facts, opinions, and data points that serve as **markers** for the AI to quickly understand what's available in that item. This list helps the AI make informed retrieval decisions.

**Output**: Add `summary` field to each content item's JSON structure containing lists of facts, opinions, and data points (not narrative summaries)

### 2. Updated JSON Structure

**Current Structure** (in batch_data):
```python
{
    "link_id": {
        "transcript": "...",  # Full transcript text
        "comments": [...],    # List of comments
        "metadata": {...},
        "source": "youtube|bilibili|reddit|article"
    }
}
```

**New Structure** (after Phase 0 summarization):
```python
{
    "link_id": {
        "transcript": "...",  # Full transcript text (unchanged)
        "comments": [...],    # Full comments list (unchanged)
        "metadata": {...},    # Unchanged
        "source": "...",     # Unchanged
        "summary": {          # NEW: List of markers for retrieval
            "transcript_summary": {
                "key_facts": [           # List of factual statements
                    "Fact 1: ...",
                    "Fact 2: ...",
                    ...
                ],
                "key_opinions": [        # List of opinions/arguments
                    "Opinion 1: ...",
                    "Opinion 2: ...",
                    ...
                ],
                "key_datapoints": [     # List of data points/statistics
                    "Data point 1: ...",
                    "Data point 2: ...",
                    ...
                ],
                "topic_areas": ["topic1", "topic2", ...],  # List of topics
                "word_count": 12345,
                "total_markers": 15  # Total number of facts+opinions+datapoints
            },
            "comments_summary": {
                "total_comments": 1000,
                "key_facts_from_comments": [  # List of facts mentioned in comments
                    "Fact 1: ...",
                    "Fact 2: ...",
                    ...
                ],
                "key_opinions_from_comments": [  # List of opinions from comments
                    "Opinion 1: ...",
                    "Opinion 2: ...",
                    ...
                ],
                "key_datapoints_from_comments": [  # List of data points from comments
                    "Data point 1: ...",
                    "Data point 2: ...",
                    ...
                ],
                "major_themes": [        # List of discussion themes
                    "Theme 1: ...",
                    "Theme 2: ...",
                    ...
                ],
                "sentiment_overview": "mostly_positive|mixed|mostly_negative",
                "top_engagement_markers": [  # High-engagement comments as markers
                    "High-engagement comment about X: ...",
                    ...
                ],
                "total_markers": 25  # Total number of markers from comments
            },
            "created_at": "2025-11-04T11:00:00",
            "model_used": "qwen-flash"
        }
    }
}
```

**Key Characteristics**:
- **Lists, not narratives**: Each field is a list of discrete items (facts, opinions, datapoints)
- **Markers for retrieval**: Each item in the list is a "marker" that signals what information is available
- **Quick scanning**: AI can quickly scan lists to understand what's available without reading full content
- **Retrieval decision support**: Lists help AI decide which content items to retrieve in full

### 3. Summary Storage

**Option A: In-memory only** (simpler, faster)
- Summaries stored in `batch_data` dict during research session
- Lost when session ends
- Pros: Simple, no file I/O
- Cons: Need to regenerate each time

**Option B: Save to JSON files** (recommended)
- Save summaries back to original JSON files in `tests/results/run_{batch_id}/`
- Add `summary` field to each content item's JSON file
- Pros: Persistent, can reuse across sessions
- Cons: Need to modify existing JSON files (or create new ones)

**Recommendation**: Option B - Save summaries to JSON files for persistence and reuse.

**File Structure**:
```
tests/results/run_{batch_id}/
├── {batch_id}_{SOURCE}_{link_id}_tsct.json  # Transcript file
│   └── Add "summary" field here
├── {batch_id}_{SOURCE}_{link_id}_cmts.json  # Comments file
│   └── Add "summary" field here
└── ...
```

**Note**: Since transcripts and comments are in separate files, we need to either:
1. Add summary to both files (with partial summaries)
2. Create a combined summary file
3. Add summary to the transcript file (primary) and reference it from comments file

**Recommendation**: Add summary to transcript file (primary content), and if comments file exists separately, add a `summary` field there too with just comments summary.

### 4. Phase 3 Changes: Use Summaries Instead of Truncated Content

**Current Flow**:
1. Phase 3 loads batch_data
2. Creates data chunk from transcript/comments
3. **Truncates** data chunk (15K for comments, configurable for transcripts)
4. Sends truncated chunk to Qwen
5. Qwen may request more via retrieval handler

**New Flow**:
1. Phase 3 loads batch_data (with summaries)
2. Creates **initial batch** using summaries instead of raw content
   - Send summaries of all content items to Qwen
   - Much smaller than raw content, but complete overview
3. Qwen can see all available content items and their key points
4. Qwen requests full content items based on summary relevance
5. Phase 3 uses retrieval handler to fetch full content when requested

**Key Changes in `phase3_execute.py`**:
- Add method: `_prepare_summary_batch()` - creates initial batch from summaries
- Modify `_prepare_data_chunk()` - check if summary exists, use it for initial batch
- Keep `_safe_truncate_data_chunk()` for fallback when summaries not available
- Update retrieval logic to handle summary-based requests

---

## Implementation Details

### Step 1: Create Summarization Module

**New File**: `research/summarization/content_summarizer.py`

```python
"""Content summarization using qwen-flash for Phase 0."""

from typing import Dict, Any, List, Optional
from core.qwen_client import QwenStreamingClient  # Or create separate flash client
from research.phases.base_phase import BasePhase
from loguru import logger


class ContentSummarizer:
    """Summarize content items using qwen-flash."""
    
    def __init__(self, client: QwenStreamingClient):
        self.client = client
        self.model = "qwen-flash"  # Fast, cheap model for summarization
    
    def summarize_content_item(
        self,
        link_id: str,
        transcript: Optional[str] = None,
        comments: Optional[List] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create structured summary for a content item.
        
        Returns:
            {
                "transcript_summary": {...},
                "comments_summary": {...}
            }
        """
        # Implementation details below
        pass
    
    def _summarize_transcript(self, transcript: str) -> Dict[str, Any]:
        """
        Extract lists of key facts, opinions, and data points from transcript.
        
        Returns lists that serve as markers for retrieval, not narrative summaries.
        """
        # Use qwen-flash to extract lists of:
        # - Key facts (factual statements)
        # - Key opinions (arguments/viewpoints)
        # - Key datapoints (statistics/numbers)
        # - Topic areas (list of topics covered)
        pass
    
    def _summarize_comments(self, comments: List) -> Dict[str, Any]:
        """
        Extract lists of key facts, opinions, and data points from comments.
        
        Returns lists that serve as markers for retrieval, not narrative summaries.
        """
        # Use qwen-flash to extract lists of:
        # - Key facts mentioned in comments
        # - Key opinions expressed in comments
        # - Key datapoints mentioned in comments
        # - Major themes (discussion topics)
        # - Top engagement markers (high-engagement comments as retrieval signals)
        pass
```

### Step 2: Create Summarization Prompts

**New Directory**: `research/prompts/content_summarization/`

**Files**:
- `system.md` - System prompt for summarization task
- `transcript_instructions.md` - Instructions for transcript summarization
- `comments_instructions.md` - Instructions for comments summarization
- `output_schema.json` - JSON schema for structured summary output

**Example Prompt Structure**:
```
System: You are a content indexing assistant. Extract lists of key facts, opinions, and data points that serve as markers for retrieval.

Task: Extract from this transcript/comments:
1. List of key FACTS (factual statements, concrete information)
2. List of key OPINIONS (arguments, viewpoints, perspectives)
3. List of key DATA POINTS (statistics, numbers, metrics)
4. List of topic areas covered

Important: Output as LISTS, not narrative summaries. Each item in the list is a "marker" that signals what information is available. The AI will use these markers to decide which content items to retrieve in full.

Output format: JSON with specific structure (see schema)
```

**Prompt Philosophy**:
- **Lists, not summaries**: Emphasize extracting discrete items, not writing paragraphs
- **Markers for retrieval**: Each item signals what's available
- **Quick scanning**: Lists should be scannable without reading full content
- **Facts vs Opinions vs Data**: Clear distinction helps AI understand content type

### Step 3: Integrate into Phase 0

**Modify**: `research/phases/phase0_prepare.py`

**Add Method**:
```python
def _summarize_content_items(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize all content items using qwen-flash."""
    from research.summarization.content_summarizer import ContentSummarizer
    
    summarizer = ContentSummarizer(self.client)
    summaries = {}
    
    for link_id, data in batch_data.items():
        logger.info(f"Summarizing content item: {link_id}")
        summary = summarizer.summarize_content_item(
            link_id=link_id,
            transcript=data.get("transcript"),
            comments=data.get("comments"),
            metadata=data.get("metadata")
        )
        # Add summary to data
        data["summary"] = summary
        summaries[link_id] = summary
    
    return batch_data  # Now with summaries added
```

**Update `execute()` method**:
```python
def execute(self, batch_id: str) -> Dict[str, Any]:
    # ... existing code ...
    
    # Load batch data
    batch_data = self.data_loader.load_batch(batch_id)
    
    # NEW: Summarize content items
    batch_data = self._summarize_content_items(batch_data)
    
    # Save summaries to JSON files (optional but recommended)
    self._save_summaries_to_files(batch_id, batch_data)
    
    # ... rest of existing code ...
```

### Step 4: Save Summaries to JSON Files

**New Method in Phase0Prepare**:
```python
def _save_summaries_to_files(self, batch_id: str, batch_data: Dict[str, Any]):
    """Save summaries back to JSON files for persistence."""
    # For each content item, update its JSON file with summary
    # This allows summaries to be reused in future sessions
    pass
```

**Implementation Considerations**:
- Need to find the original JSON file for each link_id
- Update JSON file with `summary` field
- Handle both transcript and comments files separately
- Use atomic writes (write to temp file, then rename)

### Step 5: Update Phase 3 to Use Summaries

**Modify**: `research/phases/phase3_execute.py`

**New Method**:
```python
def _prepare_summary_batch(
    self,
    batch_data: Dict[str, Any],
    required_data: str
) -> str:
    """
    Prepare initial batch using summaries instead of raw content.
    
    This creates a compact overview of all content items that Qwen can use
    to decide which items need full content retrieval.
    """
    summary_parts = []
    
    for link_id, data in batch_data.items():
        summary = data.get("summary")
        if not summary:
            # Fallback: use existing abstract method
            continue
        
        # Build summary text using lists of markers
        item_summary = f"**内容项: {link_id}**\n"
        item_summary += f"来源: {data.get('source', 'unknown')}\n"
        
        if required_data in ["transcript", "transcript_with_comments"]:
            ts_summary = summary.get("transcript_summary", {})
            if ts_summary:
                # List of key facts
                key_facts = ts_summary.get("key_facts", [])
                if key_facts:
                    item_summary += f"\n**关键事实** ({len(key_facts)} 条):\n"
                    for fact in key_facts[:8]:  # Show top 8 markers
                        item_summary += f"- {fact}\n"
                
                # List of key opinions
                key_opinions = ts_summary.get("key_opinions", [])
                if key_opinions:
                    item_summary += f"\n**关键观点** ({len(key_opinions)} 条):\n"
                    for opinion in key_opinions[:8]:
                        item_summary += f"- {opinion}\n"
                
                # List of key datapoints
                key_datapoints = ts_summary.get("key_datapoints", [])
                if key_datapoints:
                    item_summary += f"\n**关键数据点** ({len(key_datapoints)} 条):\n"
                    for dp in key_datapoints[:8]:
                        item_summary += f"- {dp}\n"
        
        if required_data in ["comments", "transcript_with_comments"]:
            cmt_summary = summary.get("comments_summary", {})
            if cmt_summary:
                # List of facts from comments
                facts_from_comments = cmt_summary.get("key_facts_from_comments", [])
                if facts_from_comments:
                    item_summary += f"\n**评论中的关键事实** ({len(facts_from_comments)} 条):\n"
                    for fact in facts_from_comments[:8]:
                        item_summary += f"- {fact}\n"
                
                # List of opinions from comments
                opinions_from_comments = cmt_summary.get("key_opinions_from_comments", [])
                if opinions_from_comments:
                    item_summary += f"\n**评论中的关键观点** ({len(opinions_from_comments)} 条):\n"
                    for opinion in opinions_from_comments[:8]:
                        item_summary += f"- {opinion}\n"
                
                # List of datapoints from comments
                datapoints_from_comments = cmt_summary.get("key_datapoints_from_comments", [])
                if datapoints_from_comments:
                    item_summary += f"\n**评论中的关键数据点** ({len(datapoints_from_comments)} 条):\n"
                    for dp in datapoints_from_comments[:8]:
                        item_summary += f"- {dp}\n"
                
                # Major themes
                major_themes = cmt_summary.get("major_themes", [])
                if major_themes:
                    item_summary += f"\n**讨论主题** ({len(major_themes)} 个):\n"
                    for theme in major_themes[:8]:
                        item_summary += f"- {theme}\n"
        
        summary_parts.append(item_summary)
    
    return "\n\n---\n\n".join(summary_parts)
```

**Update `_prepare_data_chunk()` method**:
```python
def _prepare_data_chunk(
    self,
    batch_data: Dict[str, Any],
    required_data: str,
    chunk_strategy: str = "all"
) -> str:
    """Prepare data chunk, preferring summaries for initial batch."""
    
    # Check if summaries are available
    has_summaries = any(
        data.get("summary") for data in batch_data.values()
    )
    
    if has_summaries and chunk_strategy == "all":
        # Use summary batch for initial overview
        self.logger.info("Using summaries for initial batch (full content available on request)")
        return self._prepare_summary_batch(batch_data, required_data)
    else:
        # Fallback to existing method (truncated raw content)
        return self._prepare_data_chunk_legacy(batch_data, required_data, chunk_strategy)
```

**Update Retrieval Flow**:
- When Qwen requests specific content items, use full content (not summaries)
- Update retrieval handler to support "get full content item by link_id"
- Remove hardcoded 15K truncation for comments when full content is requested

### Step 6: Update Retrieval Handler

**Modify**: `research/retrieval_handler.py`

**Add Method**:
```python
def retrieve_full_content_item(
    self,
    link_id: str,
    batch_data: Dict[str, Any],
    include_transcript: bool = True,
    include_comments: bool = True
) -> str:
    """
    Retrieve full (untruncated) content for a specific link_id.
    Used when Qwen requests detailed content based on summary.
    """
    data = batch_data.get(link_id)
    if not data:
        return f"Error: link_id {link_id} not found"
    
    parts = []
    
    if include_transcript:
        transcript = data.get("transcript", "")
        if transcript:
            parts.append(f"**完整转录本** ({len(transcript)} chars):\n{transcript}")
    
    if include_comments:
        comments = data.get("comments", [])
        if comments:
            # Format all comments (no truncation!)
            comments_text = self._format_comments(comments)
            parts.append(f"**完整评论** ({len(comments)} 条):\n{comments_text}")
    
    return "\n\n".join(parts) if parts else f"Error: No content available for {link_id}"
```

---

## Configuration Changes

**Add to `config.yaml`**:
```yaml
research:
  summarization:
    enabled: true  # Enable Phase 0 summarization
    model: "qwen-flash"  # Fast model for summarization
    max_transcript_length_for_summary: 50000  # Chunk very long transcripts for summarization
    max_comments_for_summary: 1000  # Sample large comment sets for summarization
    save_to_files: true  # Save summaries to JSON files for persistence
    reuse_existing_summaries: true  # Use existing summaries if found in JSON files
  retrieval:
    # ... existing config ...
    use_summaries_for_initial_batch: true  # Use summaries instead of truncated content
    enable_full_content_retrieval: true  # Allow Qwen to request full content items
```

---

## Migration & Backwards Compatibility

### Handling Existing Data

**Lazy Summarization**
- Check if summary exists in JSON file
- If exists, load it
- If not, generate on-the-fly during Phase 0
- Save after generation

### Backwards Compatibility

- If summaries not available, fall back to existing truncation behavior
- Existing code continues to work
- Summarization is opt-in via config

---

## Performance Considerations

### Summarization Costs (qwen-flash)

**Estimates**:
- qwen-flash is much cheaper than qwen-max
- Per content item: ~500-2000 tokens input, ~300-800 tokens output
- Cost: ~$0.001-0.005 per content item
- For 10 content items: ~$0.01-0.05 (negligible)

### Time Impact

- Summarization adds ~1-3 seconds per content item
- Can be parallelized (multiple qwen-flash calls simultaneously)
- For 10 items: ~10-30 seconds total (acceptable for Phase 0)

### Token Savings in Phase 3

**Before**: 
- Sending 271K chars of comments (truncated to 15K) = ~4000 tokens
- Many content items = high token usage

**After**:
- Initial batch: summaries only = ~200-500 tokens per item
- Only request full content when needed = much lower token usage overall
- Better utilization = less wasted tokens

---

## Testing Strategy

### Unit Tests

1. **ContentSummarizer**
   - Test transcript summarization
   - Test comments summarization
   - Test handling of missing data
   - Test large content handling

2. **Phase0Prepare**
   - Test summarization integration
   - Test summary saving to files
   - Test loading existing summaries

3. **Phase3Execute**
   - Test summary batch preparation
   - Test fallback to legacy method
   - Test full content retrieval

### Integration Tests

1. **End-to-end flow**:
   - Phase 0: Load batch → Summarize → Save summaries
   - Phase 3: Load batch with summaries → Use summaries for initial batch → Request full content → Verify no truncation

2. **Backwards compatibility**:
   - Test with batches that don't have summaries (should fall back to truncation)

### Validation

- Verify summaries capture key information
- Verify full content retrieval works correctly
- Verify no data loss (all content accessible when needed)
- Verify performance is acceptable

---

## Implementation Order

### Phase 1: Core Summarization (Foundation)
1. ✅ Create `ContentSummarizer` class
2. ✅ Create summarization prompts
3. ✅ Implement transcript summarization
4. ✅ Implement comments summarization
5. ✅ Test summarization quality

### Phase 2: Phase 0 Integration
6. ✅ Integrate summarization into Phase0Prepare
7. ✅ Add summary saving to JSON files
8. ✅ Add summary loading from JSON files
9. ✅ Test Phase 0 with summarization

### Phase 3: Phase 3 Integration
10. ✅ Add summary batch preparation in Phase3Execute
11. ✅ Update data chunk preparation to use summaries
12. ✅ Update retrieval handler for full content retrieval
13. ✅ Test Phase 3 with summaries

### Phase 4: Polish & Optimization
14. ✅ Add configuration options
15. ✅ Add logging and monitoring
16. ✅ Performance optimization (parallelization)
17. ✅ Documentation updates

---

## Success Metrics

### Quantitative
- **Truncation reduction**: Comments utilization increases from 5.5% to 80%+ (when needed)
- **Token efficiency**: Initial batch tokens reduced by 60-80%
- **Content coverage**: All content items accessible when requested (0% data loss)

### Qualitative
- Qwen can see overview of all content items before requesting details
- Research quality improves due to better context awareness
- No user-visible truncation warnings (or minimal)

---

## ANSWERS TO QUESTIONS

1. **List granularity**: How many markers per list?
   - 5-15 markers per list (facts + opinions + datapoints)
   - Each marker should be 10-50 words (concise but informative)

2. **Marker format**: How should each marker be structured?
   - Structured with type prefix ("FACT: Player retention dropped 30% after season reset")

3. **List format**: Structured JSON vs. plain text?
   - Structured JSON (easier to parse, allows filtering by type)

4. **When to regenerate summaries**: 
   - Regenerate if content file timestamp changes

5. **Batch summarization**: Process all items in parallel or sequentially?
   - Parallel with rate limiting (don't overwhelm API)

6. **Summary caching**: Cache summaries across sessions?
   - Yes, save to JSON files

---

## Next Steps

1. **Review this plan** - Get feedback on approach
2. **Refine details** - Address open questions
3. **Implement Phase 1** - Core summarization
4. **Test and iterate** - Validate approach
5. **Deploy** - Integrate into main workflow

---

## References

- Current truncation logic: `research/phases/phase3_execute.py::_safe_truncate_data_chunk()`
- Current Phase 0: `research/phases/phase0_prepare.py`
- Current retrieval: `research/retrieval_handler.py`
- Data loading: `research/data_loader.py`

