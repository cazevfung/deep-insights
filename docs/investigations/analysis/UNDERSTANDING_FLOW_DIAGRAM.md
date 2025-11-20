# Research System: Content Understanding Flow Diagram

## Visual Flow of How AI Gains Understanding

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PHASE 0: DATA PREPARATION                            │
│                      (Initial Context Setup)                            │
├─────────────────────────────────────────────────────────────────────────┤
│ Input: Raw Scraped Data                                                 │
│   - Transcripts (YouTube, Bilibili, Reddit, Articles)                   │
│   - Comments (various formats)                                         │
│   - Metadata (title, author, dates, URLs)                              │
│                                                                          │
│ Processing:                                                              │
│   ├─ Normalize formats (unified structure)                              │
│   ├─ Create abstracts per item:                                         │
│   │   • First 500 words of transcript                                   │
│   │   • Random 30 comments                                              │
│   │   • Metadata summary                                                │
│   └─ Combine with source labels                                         │
│                                                                          │
│ Output: Combined Abstract                                               │
│   Format: "**来源: {link_id}**\n{abstract}" (per item)                  │
│   Size: ~5,000-10,000 words total (manageable)                         │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   PHASE 1: DISCOVER GOALS                                │
│                   (Strategic Understanding)                              │
├─────────────────────────────────────────────────────────────────────────┤
│ Input: Combined Abstract + Optional User Topic                          │
│                                                                          │
│ AI Context:                                                              │
│   • Sees ALL source abstracts together                                  │
│   • Understands available content types                                 │
│   • Recognizes data diversity/patterns                                  │
│   • Can align with user intent (if provided)                            │
│                                                                          │
│ Processing:                                                              │
│   ├─ Analyze content themes                                             │
│   ├─ Identify research opportunities                                    │
│   └─ Generate 3 actionable goals                                        │
│                                                                          │
│ Output: 3 Research Goal Suggestions (JSON)                              │
│   User selects one → becomes "selected_goal"                             │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   PHASE 2: CREATE PLAN                                   │
│                   (Tactical Understanding)                              │
├─────────────────────────────────────────────────────────────────────────┤
│ Input: Selected Goal + Data Summary                                     │
│   • Data Summary: word counts, comment counts, sources list            │
│                                                                          │
│ AI Context:                                                              │
│   • Knows available data volume (quantitative)                          │
│   • Understands research objective (goal-focused)                      │
│   • Can plan appropriate chunking strategies                            │
│                                                                          │
│ Processing:                                                              │
│   ├─ Break goal into steps                                              │
│   ├─ Assign data requirements per step                                   │
│   ├─ Select chunking strategies (sequential/all/sample)                 │
│   └─ Estimate token requirements                                        │
│                                                                          │
│ Output: Research Plan (JSON)                                            │
│   Structure: [{step_id, goal, required_data, chunk_strategy, ...}]     │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   PHASE 3: EXECUTE PLAN                                  │
│                   (Deep Analytical Understanding)                       │
├─────────────────────────────────────────────────────────────────────────┤
│ For Each Step:                                                           │
│                                                                          │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ Step Context:                                                      │  │
│ │   • Step goal (specific objective)                                 │  │
│ │   • Data chunk (prepared per strategy)                             │  │
│ │   • Scratchpad summary (all previous findings)                     │  │
│ │                                                                     │  │
│ │ Data Preparation:                                                   │  │
│ │   if required_data == "transcript":                                 │  │
│ │     → Combine ALL transcripts                                       │  │
│ │     → Apply chunking (sequential: 2000 words OR all)               │  │
│ │     → Limit to 8000 chars                                           │  │
│ │                                                                     │  │
│ │   if required_data == "comments":                                   │  │
│ │     → Combine ALL comments                                          │  │
│ │     → Apply sampling (random_sample OR all)                         │  │
│ │                                                                     │  │
│ │   if required_data == "previous_findings":                          │  │
│ │     → Return scratchpad summary                                     │  │
│ │                                                                     │  │
│ │ AI Analysis:                                                        │  │
│ │   • Analyzes data chunk with context of prior findings              │  │
│ │   • Generates structured findings (JSON)                             │  │
│ │   • Includes confidence score                                       │  │
│ │                                                                     │  │
│ │ Output: Findings JSON                                               │  │
│ │   {step_id, findings: {...}, insights: "...", confidence: 0.0}    │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│ Scratchpad Update:                                                      │
│   • Store findings per step                                             │  │
│   • Format: "步骤 {step_id}: {insights}\n发现: {findings}"            │  │
│   • Maintain running summary for next steps                            │  │
│                                                                          │
│ Result: Accumulated findings across all steps                            │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   PHASE 4: SYNTHESIZE REPORT                            │
│                   (Holistic Understanding)                              │
├─────────────────────────────────────────────────────────────────────────┤
│ Input: Selected Goal + Complete Scratchpad                              │
│                                                                          │
│ AI Context:                                                              │
│   • Sees ALL findings from ALL steps                                    │
│   • Understands complete research journey                                │
│   • Knows original research objective                                   │
│                                                                          │
│ Processing:                                                              │
│   ├─ Synthesize all findings                                            │
│   ├─ Align with original goal                                           │
│   ├─ Structure as Markdown report                                       │
│   └─ Provide evidence and insights                                      │
│                                                                          │
│ Output: Final Research Report (Markdown)                                  │
│   Structure:                                                             │
│     # Research Report: {goal}                                           │
│     ## Executive Summary                                                │
│     ## Main Findings                                                    │
│     ## Detailed Analysis                                                │
│     ## Conclusions                                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Understanding Mechanisms

### 1. Progressive Context Enrichment
```
Abstracts (Phase 0) 
    → Goals (Phase 1) 
    → Plan (Phase 2) 
    → Findings (Phase 3) 
    → Report (Phase 4)
```
Each phase adds depth while maintaining previous understanding.

### 2. Memory Persistence
```
Phase 3 Step 1 → Findings → Scratchpad
Phase 3 Step 2 → Uses Scratchpad → Adds Findings → Updates Scratchpad
Phase 3 Step 3 → Uses Updated Scratchpad → ...
Phase 4 → Uses Complete Scratchpad → Report
```

### 3. Context Size Management
```
Phase 0: ~500 words/item (sampling)
Phase 1: All abstracts combined (~5K-10K words)
Phase 2: Statistical summary only
Phase 3: 8,000 char chunks per step
Phase 4: All scratchpad findings
```

### 4. Data Flow Examples

**Example: Sequential Transcript Processing**
```
Step 1: Chunk 1 (words 0-2000) + Empty scratchpad → Findings 1
Step 2: Chunk 2 (words 2000-4000) + Scratchpad (Findings 1) → Findings 2
Step 3: Previous findings (Findings 1 + 2) → Synthesis findings
```

**Example: Comment Analysis**
```
Step 1: Transcript analysis → Key themes
Step 2: Comments (random sample) + Scratchpad (Step 1) → Reaction analysis
Step 3: Previous findings → Pattern identification
```

## Understanding Quality Factors

✅ **Completeness**: All data available through phases
✅ **Relevance**: Each step focuses on specific goal
✅ **Context**: Scratchpad maintains memory
✅ **Structure**: JSON schemas ensure consistency
✅ **Size Management**: Chunking prevents overflow

⚠️ **Limitations**:
- Sequential chunking may lose detail
- Sampling may miss important content
- Source attribution could be stronger

