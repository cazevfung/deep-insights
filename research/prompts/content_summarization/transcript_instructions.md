# Transcript Summarization Instructions

Extract key information from this transcript as **lists of markers** for retrieval purposes.

## Task

Analyze the transcript and extract:

1. **key_facts** (List): Factual statements, concrete information, verifiable claims
   - Format: "FACT: [statement]" (10-50 words each)
   - Example: "FACT: Player retention dropped 30% after season reset"
   - Target: 5-15 facts

2. **key_opinions** (List): Arguments, viewpoints, perspectives, interpretations
   - Format: "OPINION: [statement]" (10-50 words each)
   - Example: "OPINION: The new ranking system is unfair to casual players"
   - Target: 5-15 opinions

3. **key_datapoints** (List): Statistics, numbers, metrics, quantitative information
   - Format: "DATA: [statistic]" (10-50 words each)
   - Example: "DATA: Average playtime increased from 2.5 to 3.2 hours per day"
   - Target: 5-15 datapoints

4. **topic_areas** (List): Main topics/themes covered in the transcript
   - Format: Simple topic names (3-10 words each)
   - Example: "Game balance updates", "Player feedback analysis"
   - Target: 3-10 topics

## Output Requirements

- Output as JSON only
- Each list should contain 5-15 items (except topic_areas: 3-10)
- Each marker: 10-50 words
- Be specific and informative
- Avoid vague or generic statements

## JSON Schema

```json
{
  "key_facts": ["FACT: ...", ...],
  "key_opinions": ["OPINION: ...", ...],
  "key_datapoints": ["DATA: ...", ...],
  "topic_areas": ["topic1", "topic2", ...],
  "word_count": 12345,
  "total_markers": 15
}
```





