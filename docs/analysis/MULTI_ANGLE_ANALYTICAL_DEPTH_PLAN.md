# Multi-Angle Analytical Depth Plan

## Problem Analysis

Current research process extracts information but may not:
- **Think from multiple perspectives** - may take single viewpoint
- **Actively seek contradictions** - may accept claims without challenging
- **Dig deeper based on findings** - may stop at surface level
- **Compare arguments vs counterarguments** - may not seek opposing views
- **Follow up with deeper questions** - may not probe further based on discoveries

### Current Analytical Approach

**Phase 2 (Planning)**: Creates analysis steps but may not explicitly seek:
- Different stakeholder perspectives
- Contradictory evidence
- Alternative interpretations
- Missing angles

**Phase 3 (Execution)**: Analyzes data but:
- Focuses on extracting what's present
- May not actively seek what's missing
- May not challenge claims
- May not compare arguments systematically

**Phase 4 (Synthesis)**: Synthesizes but may not:
- Present multiple perspectives equally
- Show argument/counterargument structure
- Highlight contradictions as insights
- Weave complexity into narrative

### User's Request

Force the AI to:
1. **Think from more angles** - multiple perspectives on each topic
2. **Dig deeper based on research steps** - follow-up questions and deeper analysis
3. **Seek examples more actively** - not just extract, but actively find examples
4. **Find arguments AND counterarguments** - systematic opposition-seeking
5. **Be more detailed throughout** - not just at extraction, but at every analytical step

---

## Proposed Solutions

### Solution 1: Multi-Perspective Analysis Framework for Phase 3 (HIGH IMPACT)

**Concept**: Force Phase 3 to analyze every topic from multiple predefined angles, not just extract what's present.

#### 1.1. Add Multi-Perspective Analysis Instructions

**File**: `research/prompts/phase3_execute/instructions.md`

**Add Section** (before "兴趣点提取要求"):
```
**多角度分析要求：**

在完成步骤目标时，必须从以下角度进行分析（即使某些角度信息有限，也要尝试）：

1. **支持者视角 (Proponent View)**：
   - 谁支持这个观点？为什么？
   - 他们的论据是什么？有什么证据？
   - 他们的动机/利益是什么？

2. **反对者视角 (Opponent View)**：
   - 谁反对这个观点？为什么？
   - 他们的论据和反驳是什么？
   - 他们的担忧/利益是什么？

3. **中立者视角 (Neutral/Observer View)**：
   - 是否有中立的观察者或分析者？
   - 他们的客观分析是什么？
   - 他们指出了什么平衡点或复杂性？

4. **不同来源视角 (Cross-Source Perspective)**：
   - 不同来源（视频作者 vs 评论者 vs 其他）对这个话题的看法是否一致？
   - 如果不一致，差异在哪里？
   - 哪些观点在某个来源中出现但在其他来源中缺失？

5. **深层次原因 (Root Cause Analysis)**：
   - 表面的现象/观点背后的根本原因是什么？
   - 为什么会有这样的观点分歧？
   - 是否有更深层的动机、恐惧、利益冲突？

**必须识别**：
- ✅ 如果内容中明确表达了某个观点，记录支持该观点的人/来源
- ✅ 如果内容中暗示了反对意见（即使未明确表达），也要识别
- ✅ 如果评论与转录本观点不同，这本身就是重要的发现
- ✅ 如果某个角度在内容中缺失，在"open_questions"中记录（例如："未找到明确的反对者观点"）

**不要只记录统一观点**：
- ❌ 避免："大多数人都认为X"
- ✅ 改为："视频作者认为X，理由是...；而评论区中有玩家持相反观点，认为..."
```

#### 1.2. Enhance Output Schema for Multi-Perspective

**File**: `research/prompts/phase3_execute/instructions.md`

**Update JSON Output Format**:
```json
{
  "points_of_interest": {
    "key_claims": [
      {
        "claim": "具体论点",
        "supporting_evidence": "支持证据",
        "relevance": "high|medium|low",
        "proponents": ["谁支持，如：视频作者、某些玩家"],  // NEW
        "opponents": ["谁反对，如：其他玩家、评论者"],      // NEW
        "counterarguments": ["反对论据（如有）"],          // NEW
        "root_cause": "深层原因分析（如有）"             // NEW
      }
    ],
    "controversial_topics": [
      {
        "topic": "争议话题",
        "opposing_views": [
          {
            "view": "观点1",
            "proponents": ["谁持有这个观点"],
            "evidence": "支持证据",
            "motivation": "可能的动机/利益（如有）"
          },
          {
            "view": "观点2",
            "proponents": ["谁持有这个观点"],
            "evidence": "支持证据",
            "motivation": "可能的动机/利益（如有）"
          }
        ],
        "intensity": "high|medium|low",
        "missing_perspectives": ["哪个角度缺失（如有）"],  // NEW
        "complexity_note": "关于这个争议的复杂性的观察（如有）"  // NEW
      }
    ]
  }
}
```

#### 1.3. Add "Critical Analysis" Step Type Instructions

**File**: `research/prompts/phase3_execute/instructions.md`

**Add Section**:
```
**批判性分析模式：**

如果步骤目标包含"批判性分析"、"寻找矛盾"、"多角度分析"等关键词，请采用批判性思维：

1. **质疑假设**：
   - 内容中的陈述基于什么假设？
   - 这些假设是否合理？是否有替代假设？

2. **寻找矛盾**：
   - 内容内部是否有自相矛盾之处？
   - 不同来源之间是否有矛盾？
   - 声明与证据是否一致？

3. **寻找缺失信息**：
   - 什么是没有说但应该说的？
   - 哪些关键信息或观点可能被遗漏了？
   - 是否存在"房间里的大象"（明显但被忽略的问题）？

4. **评估证据质量**：
   - 提供的证据是否充分？
   - 证据来源是否可靠？
   - 是否有选择性使用证据的迹象？

5. **识别偏见**：
   - 是否有明显的立场偏向？
   - 是否存在未声明的利益冲突？
   - 某些观点是否被过度强调或低估？
```

---

### Solution 2: Enhanced Phase 2 Planning for Multi-Angle Research (HIGH IMPACT)

**Concept**: Make Phase 2 explicitly plan for multi-perspective analysis and contradiction-seeking steps.

#### 2.1. Add Multi-Perspective Planning Guidance

**File**: `research/prompts/phase2_plan/instructions.md`

**Add Section** (after "详细内容提取策略"):
```
**多角度分析计划要求：**

为确保研究深度和全面性，研究计划应该包含多角度分析的步骤：

1. **必须包含的角度分析步骤**：
   - 如果研究主题涉及争议或分歧，必须添加专门步骤来：
     * 识别不同观点（支持者 vs 反对者 vs 中立者）
     * 收集每个观点的论据和证据
     * 分析观点分歧的根源
   - 如果研究主题涉及利益相关者，必须添加步骤来：
     * 分析不同利益相关者的立场
     * 识别他们可能的动机和利益
     * 比较不同群体的观点

2. **批判性分析步骤**：
   - 对于复杂主题，添加专门的"批判性分析"步骤：
     * goal: "批判性分析[主题]，寻找矛盾、缺失信息和替代解释"
     * 专门质疑假设、寻找矛盾、识别偏见

3. **对比分析步骤**：
   - 如果涉及不同来源/案例，添加对比步骤：
     * goal: "对比分析[不同来源]在[主题]上的观点和论据"
     * 识别一致性和差异性
     * 分析差异的原因

4. **深挖步骤**：
   - 对于重要的发现，添加"深挖"步骤：
     * goal: "深入分析[发现]，探索根本原因、影响和复杂性"
     * 使用5 Whys方法或根因分析

**示例计划结构：**
对于研究主题"游戏设计的公平性问题"：
1. 步骤1-2: 基本分析（识别核心话题）
2. 步骤3: 多角度分析（玩家vs开发者vs评论者观点）
3. 步骤4: 批判性分析（质疑假设、寻找矛盾）
4. 步骤5: 对比分析（不同游戏的公平性机制对比）
5. 步骤6: 深挖分析（公平性问题的根本原因）
6. 步骤7: 详细素材收集
7. 步骤8: 综合步骤
```

#### 2.2. Add Step Goal Templates for Multi-Angle Analysis

**File**: `research/prompts/phase2_plan/instructions.md`

**Add Templates**:
```
**步骤目标模板示例：**

**多角度分析：**
- "从玩家、开发者、评论者三个角度分析[主题]的观点和论据"
- "识别并对比[主题]的支持者和反对者的观点和证据"
- "分析不同利益相关者对[主题]的不同立场和动机"

**批判性分析：**
- "批判性分析[主题]，质疑假设、寻找矛盾、识别缺失信息"
- "寻找[主题]相关的自相矛盾之处和未解决的问题"
- "评估[主题]相关证据的质量和可信度"

**对比分析：**
- "对比分析[来源A]和[来源B]在[主题]上的观点差异"
- "比较不同游戏/案例在处理[主题]时的不同方法"
- "识别跨来源的一致观点和分歧观点"

**深挖分析：**
- "深入探索[发现]的根本原因、深层动机和复杂性"
- "分析[现象]背后的系统性问题（经济、心理、社会等）"
- "追踪[观点]的因果链条和潜在影响"

**详细素材收集（结合角度）：**
- "收集支持[观点A]和支持[观点B]的具体引述和例子"
- "从不同角度收集关于[主题]的详细证据和例子"
```

---

### Solution 3: "Follow-Up Questioning" After Initial Findings (MEDIUM-HIGH IMPACT)

**Concept**: After Phase 3 completes a step, analyze findings and automatically generate follow-up questions for deeper digging.

#### 3.1. Add Follow-Up Question Generation in Phase 3

**File**: `research/phases/phase3_execute.py`

**Enhancement**: After executing a step, analyze findings and generate follow-up questions:

```python
def _generate_follow_up_questions(
    self,
    step_findings: Dict[str, Any],
    scratchpad_summary: str
) -> List[str]:
    """
    Generate follow-up questions based on what was found (or not found).
    
    Returns list of questions that should be explored in subsequent steps.
    """
    questions = []
    
    findings_data = step_findings.get("findings", {})
    points_of_interest = findings_data.get("points_of_interest", {})
    
    # If controversy found but only one side, ask about the other side
    controversies = points_of_interest.get("controversial_topics", [])
    for cont in controversies:
        opposing_views = cont.get("opposing_views", [])
        if len(opposing_views) < 2:
            questions.append(f"找到关于'{cont['topic']}'的争议，但只看到一方观点。另一方的观点是什么？")
    
    # If claims found but weak evidence, ask for stronger evidence
    key_claims = points_of_interest.get("key_claims", [])
    for claim in key_claims:
        if claim.get("relevance") == "high" and not claim.get("supporting_evidence"):
            questions.append(f"关键论点'{claim['claim']}'缺少支撑证据。证据在哪里？")
    
    # If surprising insight found, ask to dig deeper
    insights = points_of_interest.get("surprising_insights", [])
    for insight in insights:
        questions.append(f"意外洞察'{insight}'需要进一步探索。其根本原因是什么？")
    
    return questions[:3]  # Top 3 questions
```

**Integration**: Append follow-up questions to scratchpad as "open_questions", which Phase 2 (if re-planned) or subsequent steps can address.

#### 3.2. Add Follow-Up Question Instructions to Phase 2

**File**: `research/prompts/phase2_plan/instructions.md`

**Add Guidance**:
```
**后续深挖步骤（Follow-Up Steps）：**

在创建研究计划时，考虑：

1. **基于预期发现的后续步骤**：
   - 如果在步骤1-3中发现了争议，添加步骤4专门分析对立方
   - 如果在步骤1-3中发现了关键观点，添加步骤4-5收集更多支撑证据
   - 如果在步骤1-3中发现了意外洞察，添加步骤4深挖其根源

2. **条件步骤（可选）**：
   - 可以在plan中标记"如果步骤X发现Y，则执行步骤Z"
   - 或者在主要分析步骤后，添加灵活的"深挖"步骤

3. **迭代分析**：
   - 对于复杂主题，允许多个阶段的分析
   - 第一阶段：基本识别
   - 第二阶段：基于第一阶段发现的深挖
   - 第三阶段：综合和验证
```

**Note**: Since Phase 2 runs once before Phase 3, the AI can't reactively plan. But we can:
- Guide Phase 2 to proactively plan follow-up steps
- Have Phase 3 identify gaps and add to scratchpad for future reference
- Or implement Phase 2.5 (re-planning based on Phase 3 findings - optional)

---

### Solution 4: Active Contradiction and Gap Seeking (MEDIUM-HIGH IMPACT)

**Concept**: Force Phase 3 to actively seek contradictions and gaps, not just extract what's present.

#### 4.1. Add Active Seeking Instructions

**File**: `research/prompts/phase3_execute/instructions.md`

**Add Section** (before "多角度分析要求"):
```
**主动寻找矛盾、缺失和深度的要求：**

不要只是被动提取信息，要主动寻找：

1. **主动寻找矛盾**：
   - 转录本说X，但评论说Y？ → 这是重要发现，记录为controversial_topic
   - 同一个来源在不同地方说了矛盾的话？ → 这也是发现，可能揭示复杂性
   - 不存在矛盾但应该有？ → 在open_questions中记录（"为什么没有反对声音？"）

2. **主动寻找缺失**：
   - 某个重要话题应该被讨论但没出现？ → 记录为open_question
   - 某个观点应该有证据但证据不足？ → 记录缺失的证据类型
   - 某个角度应该被覆盖但被忽略？ → 记录缺失的角度

3. **主动寻找深度**：
   - 看到一个观点后，不要只记录观点本身
   - 要问："为什么会有这个观点？"
   - 要问："这个观点支持/反对谁的利益？"
   - 要问："这个观点的潜在影响是什么？"
   - 将这些深层分析记录在"root_cause"或"complexity_note"字段

4. **主动寻找例子**：
   - 看到一个概括性陈述，立即寻找具体例子来支撑或反驳
   - "游戏很受欢迎" → 找到具体的受欢迎的证据（数据、评论）
   - "玩家很挫败" → 找到具体的挫败表达和例子
   - 如果只有概括没有例子，记录为缺失信息

**思考框架：**
在处理每个主要话题时，问自己：
- ✅ 这个观点有具体例子吗？（没有 → 寻找或标记缺失）
- ✅ 这个观点有反对声音吗？（没有 → 这是发现，记录"缺少反对意见"）
- ✅ 这个观点的深层原因是什么？（不清楚 → 记录为需深挖）
- ✅ 不同来源对这个话题的看法一致吗？（不一致 → 这是controversy，需详细对比）
```

#### 4.2. Enhance Controversial Topics Extraction

**File**: `research/prompts/phase3_execute/instructions.md`

**Enhance "争议话题" Section**:
```
3. **争议话题 (Controversial Topics)** - ENHANCED:
   必须主动识别：
   - **明确的争议**：内容中明确表达了不同观点
   - **潜在的争议**：某个观点很强但没有反对声音（这本身就是发现）
   - **跨来源争议**：转录本和评论区的观点不一致
   - **内部矛盾**：同一个来源在不同时候说了矛盾的话
   
   对于每个争议，必须记录：
   - 话题：争议的核心是什么
   - 各方观点：每个观点的具体表述（完整的引述）
   - 各方支持者：谁持有这个观点（来源、身份）
   - 各方证据：支撑每个观点的证据、例子、数据
   - 强度：争议的激烈程度（high/medium/low）
   - 深层原因：为什么会有这个分歧？（利益冲突、价值差异、信息不对称等）
   - 缺失信息：是否缺少某个重要角度的观点？
```

---

### Solution 5: "Devil's Advocate" Analysis Step (MEDIUM IMPACT)

**Concept**: Add a specialized step type that forces the AI to argue against findings, seeking weaknesses and alternative explanations.

#### 5.1. Add Devil's Advocate Step Type

**File**: `research/prompts/phase2_plan/instructions.md`

**Add to Step Types**:
```
- `'devil_advocate'`：扮演"魔鬼的代言人"，质疑已有发现，寻找弱点、替代解释和反对论据
  * 不是要推翻发现，而是要检验其强度和全面性
  * 专门寻找：假设是否合理、证据是否充分、是否有其他解释
  * 建议在主要发现后、综合步骤前添加
```

#### 5.2. Add Devil's Advocate Instructions

**File**: `research/prompts/phase3_execute/instructions.md`

**Add Section** (when goal contains "devil's advocate" or "质疑" keywords):
```
**魔鬼的代言人模式：**

如果你的目标是"质疑"、"魔鬼的代言人"、"寻找弱点"，请：

1. **质疑假设**：
   - 已有发现基于什么假设？
   - 这些假设是否必然成立？
   - 是否有替代假设？

2. **寻找反例**：
   - 已有的例子是否有例外？
   - 是否有相反的证据被忽略了？
   - 是否有选择性的证据使用？

3. **寻找替代解释**：
   - 观察到的现象是否有其他解释？
   - 是否过于简化了复杂的情况？
   - 是否遗漏了重要的变量？

4. **评估证据质量**：
   - 证据来源是否可靠？
   - 证据是否充分？
   - 是否存在偏见？

5. **识别逻辑漏洞**：
   - 论证是否有逻辑漏洞？
   - 因果关系是否合理？
   - 是否犯了相关性≠因果性的错误？

**输出格式**：
将这些质疑和替代解释记录在：
- `key_claims`：如果有替代解释，记录为额外的claim with "alternative_explanation": true
- `open_questions`：记录通过质疑发现的问题
- `surprising_insights`：如果质疑发现了意外复杂性，记录为insight
```

---

### Solution 6: Depth-Based Follow-Up Analysis (MEDIUM IMPACT)

**Concept**: Based on what's found at each step, automatically generate deeper analysis prompts for subsequent steps.

#### 6.1. Add Depth Indicators to Findings

**File**: `research/phases/phase3_execute.py`

**Enhancement**: Tag findings with "depth_level" to indicate if deeper analysis is needed:

```python
def _assess_finding_depth(self, findings: Dict[str, Any]) -> str:
    """
    Assess if finding needs deeper analysis.
    
    Returns: "surface", "moderate", "deep", or "needs_deeper"
    """
    points_of_interest = findings.get("findings", {}).get("points_of_interest", {})
    
    # If high-relevance claim but no root_cause analysis, needs deeper
    key_claims = points_of_interest.get("key_claims", [])
    for claim in key_claims:
        if claim.get("relevance") == "high" and not claim.get("root_cause"):
            return "needs_deeper"
    
    # If controversy but no deeper analysis, needs deeper
    controversies = points_of_interest.get("controversial_topics", [])
    for cont in controversies:
        if cont.get("intensity") == "high" and not cont.get("complexity_note"):
            return "needs_deeper"
    
    return "moderate"
```

**Usage**: If finding is tagged "needs_deeper", create follow-up step suggestion in scratchpad.

#### 6.2. Add "5 Whys" Analysis Framework

**File**: `research/prompts/phase3_execute/instructions.md`

**Add Section**:
```
**深度分析方法：**

对于重要发现，使用以下框架深入分析：

1. **5 Whys 方法**：
   - 看到一个现象/观点，问"为什么？"
   - 得到答案后，再问"为什么？"
   - 重复5次，找到根本原因
   - 记录整个"Why链条"在root_cause字段

2. **系统思维**：
   - 这个发现涉及哪些系统？（经济、社会、心理、技术等）
   - 不同系统之间如何相互作用？
   - 是否有系统性的根源？

3. **利益相关者分析**：
   - 这个发现影响谁的利益？
   - 不同利益相关者可能如何反应？
   - 利益冲突如何影响观察到的现象？

4. **时间维度**：
   - 这个发现是暂时的还是长期的？
   - 可能如何演变？
   - 历史上是否有类似情况？
```

---

### Solution 7: Enhanced Phase 4 Multi-Perspective Synthesis (MEDIUM IMPACT)

**Concept**: Make Phase 4 explicitly present multiple perspectives and weave complexity into narrative.

#### 7.1. Add Detail Density Requirements and Multi-Perspective Synthesis Instructions

**File**: `research/prompts/phase4_synthesize/instructions.md`

**Add Section** (before "如何将兴趣点融入文章"):

**7.0. Detail Density Standards (from Advanced Detail Preservation Plan)**

```
**详细度标准：**

为了生成专业、详细的文章，请遵循以下密度标准：

1. **引述密度**：
   - 目标：每100-150字至少包含1条引述或直接引用
   - 文章总长度目标：2000-3500字（对于详细报告）
   - 直接引述应该：具体、生动、支撑论点
   - 间接引用或转述也需要具体细节，不只是概括

2. **例子和数据密度**：
   - 每个主要论点应该包含至少1-2个具体例子或数据点
   - 使用具体数字、时间、地点、名称
   - 优先使用生动的、可感知的描述

3. **证据支撑**：
   - 避免"很多玩家认为"这样的概括
   - 使用"一位Reddit用户指出"、"B站评论区中"等具体引用
   - 每个分析性陈述应该至少有一个支撑细节

4. **专业文章的长度**：
   - 目标长度：2000-3500字（中等长度深度报道）
   - 不要为了简洁而牺牲细节
   - 如果素材丰富，文章应该长一些而不是短一些

**示例对比**：
❌ 概括性："玩家对挫败感的反应各有不同"
✅ 详细性："一位玩家描述他在游戏中'最快一把37秒就被打死'，这种完全不可控的挫败感让他'红温一整周'。而另一位Reddit用户则写道：'虽然死了，但我知道是我站位失误，这让我想再试一次。'"
```

#### 7.1. Add Multi-Perspective Synthesis Instructions
```
**多角度和复杂性的呈现：**

当你的发现中包含不同观点、争议或复杂性时，必须：

1. **平等呈现不同视角**：
   - ❌ 避免：只强调主导观点，忽略少数观点
   - ✅ 使用：明确呈现各方观点，让读者看到复杂性
   - 例如："视频作者认为X，理由是...。然而，评论区的玩家提出了相反观点..."

2. **展示争议的张力**：
   - ❌ 避免：回避争议，只呈现统一观点
   - ✅ 使用：将争议作为文章的核心张力点
   - 通过对比不同观点创造叙事张力
   - 展示为什么会有这样的分歧

3. **揭示复杂性而非简化**：
   - ❌ 避免："答案是简单的X"
   - ✅ 使用："答案取决于你问谁..."、"情况比表面更复杂..."
   - 承认不确定性："目前尚不清楚..."、"需要更多研究..."

4. **展示论证和反论证**：
   - 对于每个主要论点，展示支持论据和反对论据
   - 不要让文章成为单一观点的宣传
   - 让读者看到全貌，自己判断

5. **使用对比结构**：
   - 使用"一方面...另一方面..."的结构
   - 使用"支持者认为...反对者则认为..."的对比
   - 这种结构本身就能展示复杂性

**示例：**
❌ 单一视角："游戏设计很成功，玩家很满意"
✅ 多视角："游戏设计师认为设计很成功，玩家整体反应积极。但评论区中也出现了不同声音：一些玩家指出..."

**示例：**
❌ 回避复杂性："这个问题的原因很明确"
✅ 展示复杂性："关于这个问题的原因，不同人有不同解释：开发者认为..., 而玩家社区则指出... 这种分歧本身就揭示了问题的复杂性"
```

#### 7.2. Add Complexity Checklist

**File**: `research/prompts/phase4_synthesize/instructions.md`

**Add to Article Audit Checklist**:
```
**多角度和复杂性检查：**

在完成文章前，检查：
- [ ] 如果发现中有争议，是否在文章中呈现了各方观点？
- [ ] 是否只呈现了主导观点而忽略了少数/反对观点？
- [ ] 对于复杂主题，是否承认了复杂性而非过度简化？
- [ ] 文章是否展示了论证和反论证？
- [ ] 是否存在应该呈现但未呈现的角度？

**详细度检查（from Advanced Detail Preservation Plan）：**
- [ ] 每个主要段落至少包含1条具体引述或例子
- [ ] 每个分析性陈述都有至少1个支撑细节
- [ ] 文章总长度至少2000字（除非数据确实有限）
- [ ] 没有过度概括的地方（如"很多玩家"应改为具体引用）
- [ ] 所有关键数据点、统计数字、时间、地点都已包含
- [ ] 引述密度达到每100-150字至少1条引述
```

---

### Solution 8: Example-Seeking Mode (MEDIUM IMPACT)

**Concept**: When a general claim is found, force AI to immediately seek specific examples rather than accepting the claim as-is.

#### 8.1. Add Example-Seeking Instructions

**File**: `research/prompts/phase3_execute/instructions.md`

**Add Section**:
```
**例子主动寻找模式：**

每当遇到概括性陈述时，必须立即寻找具体例子：

1. **识别概括性陈述**：
   - "玩家很挫败" → 需要具体例子
   - "游戏很受欢迎" → 需要具体例子
   - "设计有问题" → 需要具体例子

2. **主动搜索**：
   - 在同一个数据块中搜索支撑这个概括的例子
   - 在之前的发现中搜索相关例子
   - 如果找不到，标记为"缺少具体例子"

3. **例子质量要求**：
   - 不要接受模糊的例子（"有些玩家说..."）
   - 需要具体的、可引用的例子（"一位Reddit用户写道：'我最快一把37秒就被打死...'"）
   - 需要多个例子来支撑一个概括（至少2-3个）

4. **记录规则**：
   - 如果找到一个概括性陈述，必须至少找到1个具体例子
   - 如果在数据块中找不到例子，记录为open_question："需要更多关于[概括]的具体例子"
   - 如果在数据块中找到例子，立即记录在specific_examples中，并标注它支撑哪个key_claim
```

**Integration**: This should be part of the analysis process, not separate. When processing data chunk, AI should continuously ask "这个说法有具体例子吗？"

---

### Solution 9: Enhanced Scratchpad Detail Preservation (MEDIUM IMPACT)

**Concept**: Ensure detailed quotes and examples are prominently featured in scratchpad summary, not buried in JSON structure.

**Problem**: Scratchpad stores structured findings (JSON), but when Phase 4 accesses it via `get_scratchpad_summary()`, the summary format might condense detailed quotes and examples.

#### 9.1. Enhance Scratchpad Summary Format

**File**: `research/session.py`

**Enhancement**: Modify `get_scratchpad_summary()` to explicitly extract and format quotes/examples prominently:

```python
def get_scratchpad_summary(self) -> str:
    """Enhanced to preserve detailed quotes and examples."""
    # ... existing code ...
    
    # For each step, explicitly extract and format quotes/examples
    for step_data in scratchpad:
        points_of_interest = step_data.get("findings", {}).get("points_of_interest", {})
        
        # Extract and format quotes prominently
        if points_of_interest:
            quotes_section = "\n**重要引述和例子**:\n"
            
            # Key claims with quotes
            for claim in points_of_interest.get("key_claims", [])[:5]:
                if isinstance(claim, dict) and claim.get("claim"):
                    quotes_section += f"- \"{claim['claim']}\""
                    if claim.get("supporting_evidence"):
                        quotes_section += f" (证据: {claim['supporting_evidence'][:100]})"
                    quotes_section += "\n"
            
            # Notable evidence quotes
            for evidence in points_of_interest.get("notable_evidence", [])[:5]:
                if isinstance(evidence, dict) and evidence.get("quote"):
                    quotes_section += f"- \"{evidence['quote']}\""
                    if evidence.get("description"):
                        quotes_section += f" ({evidence['description'][:80]})"
                    quotes_section += "\n"
            
            # Specific examples
            for example in points_of_interest.get("specific_examples", [])[:5]:
                if isinstance(example, dict) and example.get("example"):
                    quotes_section += f"- 例子: {example['example']}"
                    if example.get("context"):
                        quotes_section += f" (上下文: {example['context'][:80]})"
                    quotes_section += "\n"
            
            step_summary += quotes_section + "\n"
```

**Rationale**: Make quotes and examples highly visible in scratchpad summary, not buried in JSON structure. This ensures Phase 4 receives detailed quotes, not just summaries.

#### 9.2. Dynamic Limits for Very Large Transcripts (Optional)

**File**: `research/phases/phase3_execute.py`

**Enhancement**: For very large transcripts using "all" strategy, allow higher limits to avoid unnecessary splitting:

```python
def _calculate_dynamic_limit(
    self,
    data_chunk: str,
    required_data: str,
    full_transcript_size: Optional[int] = None
) -> int:
    """
    Calculate dynamic limit based on transcript size and API capacity.
    
    For very large transcripts, use higher limits if we're not splitting too many ways.
    """
    if required_data in ["transcript", "transcript_with_comments"]:
        base_limit = 50000
        
        # If transcript is very large but we're processing a single chunk,
        # allow more to avoid splitting
        if full_transcript_size:
            if full_transcript_size > 100000 and len(data_chunk) > 80000:
                # Very large transcript, allow up to 100K for single "all" strategy
                return 100000
            elif full_transcript_size > 80000:
                # Large transcript, allow 75000
                return 75000
        
        return base_limit
    # ... rest
```

**Note**: This is optional - 50K limit is already quite generous. Only implement if very large transcripts (>100K chars) are common.

---

## Implementation Priority

### Phase 1: High-Impact Core Enhancements (3-4 hours)

1. ✅ **Solution 1**: Multi-perspective analysis framework for Phase 3
   - Add multi-angle analysis instructions
   - Enhance output schema for perspectives
   - Add critical analysis mode

2. ✅ **Solution 2**: Enhanced Phase 2 planning for multi-angle research
   - Add multi-perspective planning guidance
   - Add step goal templates

**Impact**: Forces AI to think from multiple angles at planning and execution stages

### Phase 2: Active Seeking Enhancements (2-3 hours)

3. ✅ **Solution 4**: Active contradiction and gap seeking
   - Add active seeking instructions
   - Enhance controversial topics extraction

4. ✅ **Solution 8**: Example-seeking mode
   - Force AI to seek examples for every general claim

**Impact**: AI actively seeks what's missing, not just extracts what's present

### Phase 3: Depth and Synthesis (2-3 hours)

5. ✅ **Solution 6**: Depth-based follow-up analysis
   - Add depth indicators
   - Add 5 Whys and systematic thinking frameworks

6. ✅ **Solution 7**: Enhanced Phase 4 multi-perspective synthesis
   - Add detail density standards (merged from Advanced Detail Plan)
   - Add multi-perspective synthesis instructions
   - Add complexity and detail checklists

7. ✅ **Solution 9**: Enhanced scratchpad detail preservation
   - Make quotes/examples prominent in scratchpad summary
   - Extract from JSON structure explicitly

**Impact**: Deeper analysis, better presentation of complexity, and better detail visibility

### Phase 4: Advanced Techniques (Optional, 2-3 hours)

8. ✅ **Solution 3**: Follow-up questioning (may require Phase 2.5 re-planning)
9. ✅ **Solution 5**: Devil's Advocate analysis step

**Impact**: Advanced critical thinking techniques

---

## Expected Outcomes

### Quantitative Improvements

- **Multi-perspective coverage**: Each topic analyzed from 2-4 perspectives (vs current 1-2)
- **Contradiction identification**: 3-5 identified contradictions per article (vs current 0-2)
- **Example-to-claim ratio**: 2-3 examples per general claim (vs current 0.5-1)
- **Arguments vs counterarguments**: Both sides presented for each major controversy

### Qualitative Improvements

- **More nuanced articles**: Articles show complexity, don't oversimplify
- **Stronger evidence**: Every claim backed by specific examples
- **Better balance**: Multiple perspectives presented equally
- **Deeper insights**: Root causes and systemic factors explored
- **Critical thinking**: Assumptions challenged, alternatives considered

### Success Metrics

**Before**:
- Single perspective on most topics
- Few contradictions identified
- General claims without examples
- Oversimplified narratives

**After**:
- Multi-perspective on every major topic
- Active contradiction-seeking
- Every general claim backed by 2+ examples
- Complex narratives that acknowledge nuance

---

## Risks & Mitigation

### Risk 1: Analysis Becomes Too Academic
**Concern**: Multi-perspective analysis might make articles too formal/academic.

**Mitigation**:
- Phase 4 instructions maintain journalistic style
- Complexity can be presented narratively
- Balance depth with readability

### Risk 2: Information Overload
**Concern**: Too many perspectives might confuse readers.

**Mitigation**:
- Phase 4 instructions guide narrative integration
- AI can prioritize most relevant perspectives
- Use clear structure (e.g., "支持者认为...反对者认为...")

### Risk 3: Analysis Paralysis
**Concern**: AI might get stuck seeking too many angles.

**Mitigation**:
- Instructions guide priority (most relevant perspectives first)
- Set limits (e.g., "至少2-3个视角" not "所有可能的视角")
- Focus on content-relevant perspectives

### Risk 4: Contradiction Overemphasis
**Concern**: Too much focus on contradictions might make everything seem contentious.

**Mitigation**:
- Instructions emphasize identifying when there IS consensus (also a finding)
- Present contradictions where they exist, consensus where it exists
- Balance is the goal

---

## Testing Strategy

### Test Case 1: Multi-Perspective Coverage
- Verify each major topic analyzed from at least 2 perspectives
- Check that proponents/opponents are identified
- Verify counterarguments are collected

### Test Case 2: Contradiction Seeking
- Verify contradictions between sources are identified
- Check that missing perspectives are noted
- Confirm controversies are analyzed deeply

### Test Case 3: Example Seeking
- Count examples per general claim (target: 2+)
- Verify examples are specific and quotable
- Check that missing examples are noted as gaps

### Test Case 4: Depth Analysis
- Verify root cause analysis for key claims
- Check that 5 Whys or systematic thinking is applied
- Confirm complexity is explored, not simplified

### Test Case 5: Article Balance
- Verify articles present multiple perspectives
- Check that arguments and counterarguments are shown
- Confirm complexity is acknowledged

---

## Conclusion

### Key Strategy

Force analytical depth and multi-perspective thinking at every stage:

1. **Plan for angles**: Phase 2 explicitly plans multi-perspective steps
2. **Analyze from angles**: Phase 3 analyzes from multiple predefined perspectives
3. **Seek actively**: Phase 3 actively seeks contradictions, gaps, and examples
4. **Dig deeper**: Phase 3 follows up with deeper questions based on findings
5. **Synthesize complexity**: Phase 4 presents multiple perspectives and acknowledges nuance

### Expected Result

Articles that:
- **Show multiple perspectives** on every major topic
- **Present arguments AND counterarguments** systematically
- **Back every general claim** with 2+ specific examples
- **Seek contradictions** and explore why they exist
- **Acknowledge complexity** rather than oversimplify
- **Dig deeper** into root causes and systemic factors
- **Challenge assumptions** and consider alternatives

### Next Steps (After Approval)

1. Implement Phase 1 (multi-perspective framework)
2. Test with sample batch
3. Verify multi-angle analysis improvements
4. Implement Phase 2 (active seeking)
5. Iterate based on results

