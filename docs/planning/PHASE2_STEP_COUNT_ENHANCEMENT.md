# Phase 2 Step Count Enhancement Plan

## Problem Statement

Current Phase 2 instructions emphasize "最小充分步骤" (minimal sufficient steps) and "精简步骤列表" (simplified step list), which tends to result in plans with only 3-5 steps. This limits the granularity and creativity of the research planning process.

## Goal

Encourage the AI to generate more granular, creative steps (aiming for 6-12+ steps) while:
- Keeping the prompt simple and concise
- Maintaining creative freedom (not mandating specific number)
- Allowing natural decomposition based on research complexity

## Current Issues

1. **Language emphasizing minimalism**:
   - "最小充分步骤" (minimal sufficient steps) - directly tells AI to minimize
   - "精简步骤列表" (simplified step list) - reinforces simplicity over thoroughness
   - "简化计划" (simplified planning) - in task description

2. **Example shows only 4 steps**:
   - AI models often follow example patterns
   - 4 steps may seem like the "standard"

3. **Design guidelines prioritize efficiency over granularity**:
   - "避免过度分块" (avoid over-chunking) - may be interpreted too broadly

## Proposed Enhancement Strategy

### 1. Reframe Task Language (Subtle but Important)

**Current:**
- "制定一个精炼、可执行的研究计划，聚焦于实现目标所需的最小充分步骤"

**Enhanced:**
- "制定一个详细、可执行的研究计划。将目标分解为清晰的步骤，每个步骤聚焦一个具体任务。"

**Rationale:** 
- Remove "最小充分" (minimal sufficient) language
- Replace with "详细" (detailed) and emphasize decomposition ("将目标分解")
- Encourage granularity through "每个步骤聚焦一个具体任务" (each step focuses on one specific task)

### 2. Enhance Step Guidelines with Creative Decomposition

**Add new guideline:**
- "将复杂任务分解为多个聚焦步骤：例如，'提取论点'可分解为'识别核心论点'、'分析论证结构'、'评估证据强度'等独立步骤。"

**Rationale:**
- Provides concrete example of creative decomposition
- Shows how one broad task can become multiple focused steps
- Encourages thinking about natural breakpoints in research process

### 3. Update Example to Show More Steps

**Current:** Shows 4 generic steps

**Enhanced:** Show 6-8 steps with varied granularity:
- Some steps are single-focused (e.g., "提取核心论点")
- Some are verification steps (e.g., "用评论验证关键论断")
- Some are synthesis steps (e.g., "综合各来源证据")
- Demonstrates that more granular plans are acceptable and desirable

### 4. Add Encouragement for Thoroughness (Optional Section)

**Add subtle note:**
- "对于复杂的研究目标，详细分解有助于确保每个方面都得到充分探索。"

**Rationale:**
- Gives permission for more steps when complexity warrants it
- Frame as benefit rather than requirement
- Keeps it optional and context-dependent

## Specific Changes to Instructions

### Section: 任务 (Task)

**Before:**
```
**任务（简化计划）:**
制定一个精炼、可执行的研究计划，聚焦于实现目标所需的最小充分步骤。强调灵活性与证据驱动，不做过度模板化设计。
```

**After:**
```
**任务（详细计划）:**
制定一个详细、可执行的研究计划。将研究目标分解为清晰的步骤，每个步骤聚焦一个具体任务。强调灵活性与证据驱动，不做过度模板化设计。
```

### Section: 设计指南 (Design Guidelines)

**Add after existing guidelines:**
```
- 将复杂任务分解为多个聚焦步骤：例如，'提取论点'可分解为'识别核心论点'、'分析论证结构'、'评估证据强度'等独立步骤。
```

**Modify existing guideline:**
- Keep "避免过度分块" but add context: "对于长文档，按需使用 sequential；避免在不必要的地方过度分块。"

### Section: 输出示例 (Output Example)

**Expand example to 6-7 steps:**
1. Step showing initial metadata analysis
2. Step showing transcript reading with sequential chunking
3. Step showing specific extraction task (e.g., extract key arguments)
4. Step showing analysis task (e.g., analyze argument structure)
5. Step showing verification with comments
6. Step showing cross-validation
7. Step showing synthesis

## Implementation Notes

### What NOT to Change
- ✅ Keep schema flexible (no max step count)
- ✅ Maintain simplicity - don't add complex rules
- ✅ Keep creative freedom - no mandatory step count
- ✅ Preserve existing data types and chunk strategies

### What to Change
- 🔄 Reframe minimalism language → thoroughness language
- 🔄 Add decomposition example in guidelines
- 🔄 Expand example to show more steps
- 🔄 Add subtle encouragement for complexity-based decomposition

### Testing Considerations
- Monitor average step count after implementation
- Ensure plans remain coherent (more steps ≠ better if steps are trivial)
- Verify that quality is maintained or improved
- Check that AI doesn't generate excessive trivial steps (e.g., 20+ steps)

## Expected Outcomes

1. **Average step count**: Increase from 3-5 to 6-10 steps
2. **Step granularity**: More focused, single-purpose steps
3. **Creative decomposition**: More varied step types (extraction, analysis, verification, synthesis)
4. **Complexity handling**: More steps for complex research goals, appropriate fewer for simple ones
5. **Maintained simplicity**: Prompt remains clean and readable

## Alternative Approaches Considered

### Option A: Explicit Step Count Range
- ❌ Rejected: Too prescriptive, limits creativity
- Would add: "生成6-12个步骤" but this feels forced

### Option B: Add Step Type Categories
- ❌ Rejected: Adds complexity, might feel template-like
- Would require: Mandatory step types (setup, extraction, analysis, etc.)

### Option C: Add Examples of Good vs Bad Decomposition
- ⚠️ Considered: Could be helpful but adds length
- Current approach: Single positive example in guidelines

## Risk Assessment

### Low Risk
- Schema already supports unlimited steps
- No breaking changes to data structure
- Existing Phase 3 execution logic handles variable step counts

### Medium Risk
- AI might over-interpret and generate too many trivial steps
- Need to monitor for quality degradation
- May need fine-tuning based on initial results

### Mitigation
- Keep emphasis on "具体任务" (specific task) - prevents trivial steps
- Maintain focus on "证据驱动" (evidence-driven) - ensures meaningful steps
- Monitor and iterate based on generated plans

## Implementation Priority

**Priority: Medium**
- Enhancement, not bug fix
- Should be tested before full deployment
- Consider A/B testing if possible

## Next Steps

1. Review and approve this plan
2. Implement changes to `instructions.md`
3. Test with several research goals
4. Monitor step count and plan quality
5. Iterate based on results

