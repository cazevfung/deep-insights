# Comments Summarization Instructions

Extract key information from these comments as **lists of markers** for retrieval purposes.

## Task

Analyze the comments and extract:

1. **key_facts_from_comments** (List): Factual statements mentioned in comments
   - Format: "FACT: [statement]" (10-50 words each)
   - Target: 5-15 facts

2. **key_opinions_from_comments** (List): Opinions, viewpoints, arguments from comments
   - Format: "OPINION: [statement]" (10-50 words each)
   - Target: 5-15 opinions

3. **key_datapoints_from_comments** (List): Statistics, numbers, metrics mentioned in comments
   - Format: "DATA: [statistic]" (10-50 words each)
   - Target: 5-15 datapoints

4. **major_themes** (List): Main discussion themes/topics in comments
   - Format: "Theme: [description]" (10-50 words each)
   - Target: 3-10 themes

5. **sentiment_overview** (String): Overall sentiment
   - Options: "mostly_positive", "mixed", "mostly_negative"
   
6. **top_engagement_markers** (List): High-engagement comments as retrieval signals
   - Format: "High-engagement comment about [topic]: [summary]" (10-50 words each)
   - Include comments with high likes/replies
   - Target: 3-8 markers

## Output Requirements

- Output as JSON only
- Focus on comments with high engagement (likes, replies)
- Extract unique insights, not duplicates
- Each marker: 10-50 words
- Be specific and informative

## JSON Schema

```json
{
  "total_comments": 1000,
  "key_facts_from_comments": ["FACT: ...", ...],
  "key_opinions_from_comments": ["OPINION: ...", ...],
  "key_datapoints_from_comments": ["DATA: ...", ...],
  "major_themes": ["Theme: ...", ...],
  "sentiment_overview": "mostly_positive|mixed|mostly_negative",
  "top_engagement_markers": ["High-engagement comment about X: ...", ...],
  "total_markers": 25
}
```


