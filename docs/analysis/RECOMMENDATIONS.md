# Research System: Understanding Enhancement Recommendations

## Priority Recommendations

### 🔴 High Priority

#### 1. Enhance Sequential Chunking with Context Preservation
**Problem**: When processing large transcripts sequentially, AI may lose context from earlier chunks.

**Current Behavior**:
- Sequential chunks processed independently
- Only insights (not details) preserved in scratchpad

**Recommended Solution**:
```python
# In phase3_execute.py, _execute_step method:
def _execute_step(self, step_id, goal, data_chunk, scratchpad_summary, required_data):
    # If processing sequential chunk, include previous chunk summary
    if self._is_sequential_chunk(data_chunk):
        chunk_summary = self._get_previous_chunks_summary(step_id)
        context = {
            "step_id": step_id,
            "goal": goal,
            "previous_chunks_context": chunk_summary,  # NEW
            "current_chunk": safe_data_chunk,
            "scratchpad_summary": safe_summary,
        }
    ...
```

**Implementation**:
- Track which chunks have been processed for each step
- Include brief summary (50-100 words) of previous chunks in prompt
- Maintain chunk-level insights separately from step-level findings

**Impact**: Significant improvement in understanding for large content analysis.

---

#### 2. Add Source Attribution to Findings
**Problem**: Findings may lose traceability to original sources, making report citations difficult.

**Current Behavior**:
- Scratchpad stores findings but not source links
- Report may cite findings without source attribution

**Recommended Solution**:
```python
# In phase3_execute.py, when storing findings:
findings_with_sources = {
    **findings,
    "sources": self._identify_sources(data_chunk),  # NEW
    "link_ids": self._get_source_ids(data_chunk)     # NEW
}

self.session.update_scratchpad(
    step_id, 
    findings_with_sources,  # Includes sources
    insights, 
    confidence
)
```

**Implementation**:
- Track link_id in data chunks during preparation
- Include source IDs in findings structure
- Update scratchpad format to include source references
- Update Phase 4 prompt to encourage source citation

**Impact**: Improves report credibility and traceability.

---

### 🟡 Medium Priority

#### 3. Implement Intelligent Sampling for Abstracts
**Problem**: First 500 words may miss important content; random comment sampling may miss high-engagement content.

**Current Behavior**:
- Fixed: first 500 words
- Random: 30 comments

**Recommended Solution**:
```python
# In data_loader.py, create_abstract method:
def create_abstract(self, data, ...):
    transcript = data.get("transcript", "")
    if transcript:
        # Option 1: TF-IDF based sampling
        important_sections = self._extract_important_sections(transcript)
        
        # Option 2: Multi-point sampling
        words = transcript.split()
        samples = []
        if len(words) > 1500:
            # Beginning, middle, end
            samples.extend([
                " ".join(words[:500]),  # Beginning
                " ".join(words[len(words)//2-250:len(words)//2+250]),  # Middle
                " ".join(words[-500:])  # End
            ])
        else:
            samples.append(" ".join(words[:500]))
        
        abstract_parts.append(f"**转录本摘要**:\n" + "\n\n---\n\n".join(samples))
    
    # For comments: prefer high-engagement
    comments = data.get("comments", [])
    if comments:
        if isinstance(comments[0], dict):
            # Sort by engagement (likes, replies, etc.)
            sorted_comments = sorted(
                comments, 
                key=lambda x: x.get("likes", 0) + x.get("replies", 0),
                reverse=True
            )[:comment_sample_size]
        ...
```

**Implementation**:
- Multi-point sampling for transcripts (beginning, middle, end)
- Engagement-based sorting for comments (likes, replies)
- Add flag for "intelligent_sampling" in config

**Impact**: Better representation of content, especially for long-form content.

---

#### 4. Add Content Quality Indicators
**Problem**: System doesn't warn about low-quality, sparse, or imbalanced data.

**Current Behavior**:
- Provides statistics but no interpretation
- No warnings for data quality issues

**Recommended Solution**:
```python
# In phase0_prepare.py or data_loader.py:
def assess_data_quality(self, batch_data) -> Dict[str, Any]:
    """Assess and flag data quality issues."""
    quality_flags = []
    
    # Check for imbalance
    word_counts = [d.get("metadata", {}).get("word_count", 0) for d in batch_data.values()]
    if len(word_counts) > 1:
        max_words = max(word_counts)
        total_words = sum(word_counts)
        if max_words / total_words > 0.8:  # 80% from one source
            quality_flags.append({
                "type": "imbalance",
                "message": f"80% of content from single source",
                "severity": "warning"
            })
    
    # Check for sparse data
    avg_words = sum(word_counts) / len(word_counts)
    if avg_words < 500:
        quality_flags.append({
            "type": "sparse",
            "message": f"Average content length: {avg_words} words",
            "severity": "info"
        })
    
    # Check comment coverage
    items_with_comments = sum(1 for d in batch_data.values() if d.get("comments"))
    if items_with_comments < len(batch_data) * 0.5:
        quality_flags.append({
            "type": "comment_coverage",
            "message": f"Only {items_with_comments}/{len(batch_data)} items have comments",
            "severity": "warning"
        })
    
    return {
        "quality_flags": quality_flags,
        "quality_score": self._calculate_quality_score(batch_data)
    }
```

**Implementation**:
- Add quality assessment to Phase 0
- Include quality flags in Phase 1 and Phase 2 prompts
- Display warnings in UI

**Impact**: Helps users understand data limitations before research begins.

---

#### 5. Enhance Phase 2 Prompt with Content Preview
**Problem**: Plan created without seeing actual content, leading to suboptimal chunking strategy selection.

**Current Behavior**:
- Only receives statistics (word count, comment count)
- No content samples

**Recommended Solution**:
```python
# In phase2_plan.py, execute method:
def execute(self, selected_goal, data_summary):
    # Add content previews
    content_preview = self._generate_content_preview(batch_data)
    
    context = {
        "selected_goal": selected_goal,
        "total_words": total_words,
        "total_comments": total_comments,
        "sources_list": sources_list,
        "content_preview": content_preview,  # NEW
    }
    ...
```

```python
def _generate_content_preview(self, batch_data) -> str:
    """Generate representative content samples for planning."""
    previews = []
    
    # Sample 2-3 items per source type
    for source_type in set(d.get("source") for d in batch_data.values()):
        items = [d for d in batch_data.values() if d.get("source") == source_type]
        samples = items[:2]  # First 2 items per source
        
        for item in samples:
            transcript = item.get("transcript", "")[:500]  # First 500 chars
            previews.append(f"**{source_type}示例**:\n{transcript}...")
    
    return "\n\n".join(previews)
```

**Implementation**:
- Extract 2-3 content samples per source type
- Include in Phase 2 prompt (within token limits)
- Update prompt instructions to use previews for chunking strategy selection

**Impact**: More informed plan generation.

---

### 🟢 Low Priority (Nice to Have)

#### 6. Adaptive Chunk Size Selection
**Current**: Fixed 2000 words for sequential chunking.

**Recommendation**: Analyze content complexity and adjust chunk size:
```python
def calculate_optimal_chunk_size(self, transcript: str) -> int:
    """Calculate optimal chunk size based on content."""
    words = transcript.split()
    avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
    
    # Adjust based on content characteristics
    if avg_word_length > 10:  # Technical content
        return 1500  # Smaller chunks
    else:
        return 2000  # Standard chunks
```

---

#### 7. Semantic Chunking Strategy
**Current**: Only sequential and random sampling.

**Recommendation**: Add semantic chunking:
```python
def semantic_chunk(self, transcript: str, max_chunk_size: int = 2000) -> List[str]:
    """Chunk by semantic boundaries (sentences, paragraphs)."""
    # Split by paragraphs first
    paragraphs = transcript.split('\n\n')
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        para_words = len(para.split())
        if current_size + para_words > max_chunk_size:
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_size = para_words
        else:
            current_chunk.append(para)
            current_size += para_words
    
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks
```

---

#### 8. Confidence-Based Findings Filtering
**Problem**: Low-confidence findings may pollute scratchpad.

**Recommendation**: 
- Only store findings above confidence threshold (e.g., 0.3)
- Flag low-confidence findings for review
- Include confidence statistics in scratchpad summary

---

## Implementation Priority Matrix

| Enhancement | Priority | Effort | Impact | Recommendation |
|------------|----------|--------|--------|----------------|
| Sequential chunking context | 🔴 High | Medium | High | Implement next |
| Source attribution | 🔴 High | Low | Medium | Quick win |
| Intelligent sampling | 🟡 Medium | Medium | Medium | Implement after high priority |
| Quality indicators | 🟡 Medium | Medium | Medium | Important for UX |
| Content preview in Phase 2 | 🟡 Medium | Low | Low | Nice improvement |
| Adaptive chunking | 🟢 Low | High | Low | Future enhancement |
| Semantic chunking | 🟢 Low | High | Medium | Future enhancement |

---

## Quick Wins (Easy, High Impact)

1. **Add source IDs to findings** (30 min)
   - Modify `_execute_step` to track link_ids
   - Update scratchpad structure

2. **Multi-point transcript sampling** (1 hour)
   - Modify `create_abstract` to sample beginning, middle, end

3. **Engagement-based comment sampling** (30 min)
   - Sort by likes before sampling

4. **Quality flag in Phase 2 prompt** (30 min)
   - Add simple imbalance detection
   - Include in data_summary context

---

## Testing Recommendations

After implementing enhancements, test with:

1. **Large transcript** (>10,000 words)
   - Verify sequential chunking maintains context
   - Check scratchpad completeness

2. **Imbalanced dataset** (one source has 80% of content)
   - Verify quality flags appear
   - Check plan accounts for imbalance

3. **Multiple sources** (YouTube + Bilibili + Articles)
   - Verify source attribution works
   - Check report citations

4. **Sparse data** (low word counts, few comments)
   - Verify quality warnings
   - Check system handles gracefully

