# 多个Stream处理机制说明

**日期:** 2025-01-27  
**状态:** 技术文档

## 概述

本文档说明当多个stream同时进行时，右侧栏聊天界面如何处理和显示这些stream的内容。

---

## 数据结构

### StreamCollectionState

```typescript
interface StreamCollectionState {
  activeStreamId: string | null  // 当前活动的stream ID（只有一个）
  buffers: Record<string, StreamBufferState>  // 所有stream的buffer字典
  order: string[]  // stream ID的顺序数组（按创建时间）
  pinned: string[]  // 固定的stream ID列表
}
```

**关键点:**
- 每个stream有独立的buffer，通过`stream_id`作为key存储
- `order`数组维护stream的创建顺序
- `activeStreamId`只指向一个当前活动的stream（用于某些UI状态）

### StreamBufferState

```typescript
interface StreamBufferState {
  id: string  // stream ID
  raw: string  // 正常内容
  reasoning: string  // 推理内容
  status: 'active' | 'completed' | 'error'
  isStreaming: boolean
  lastTokenAt?: string | null
  lastReasoningTokenAt?: string | null
  // ... 其他字段
}
```

**关键点:**
- 每个stream独立存储自己的内容和状态
- 正常内容和推理内容分开存储
- 每个stream有独立的时间戳

---

## Timeline Items生成流程

### 1. 遍历所有Streams

在`usePhaseInteraction.ts`中：

```typescript
const orderedIds = [...streams.order]  // 获取所有stream ID，按创建顺序

orderedIds.forEach((id) => {
  const buffer = streams.buffers[id]
  // 为每个stream创建timeline items
})
```

### 2. 为每个Stream创建Items

对于每个stream buffer，会创建**最多2个**timeline items：

1. **正常内容item** (`${id}:content`)
   - 如果`buffer.raw`有内容
   - 类型: `'content'` 或 `'status'`

2. **推理内容item** (`${id}:reasoning`)
   - 如果`buffer.reasoning`有内容
   - 类型: `'reasoning'`
   - **永远不折叠**

### 3. 时间排序

所有items（包括不同stream的items）按时间戳排序：

```typescript
const combined = [...streamItems, ...conversationItems].sort((a, b) => {
  const aTime = a.timestamp ? new Date(a.timestamp).getTime() : 0
  const bTime = b.timestamp ? new Date(b.timestamp).getTime() : 0
  if (aTime === bTime) {
    return a.id.localeCompare(b.id)  // 相同时间按ID排序
  }
  return aTime - bTime  // 按时间升序（旧的在上，新的在下）
})
```

**结果:** 不同stream的内容会**交错显示**，按实际接收时间排序。

---

## 显示方式

### StreamSummaryView（当前使用）

`StreamSummaryView`将items按**描述**分组显示：

```typescript
// 按process description分组
const description = generateProcessDescription(item)  // 例如: "生成研究角色"
const key = description
```

**分组逻辑:**
- 相同描述（如"生成研究角色"）的items归为一组
- 显示每组的：
  - 进行中数量 (`inProgress`)
  - 已完成数量 (`completed`)
  - 错误列表 (`errors`)

**示例显示:**
```
正在生成研究角色 · 2 项
已完成: 处理转录摘要 · 7 项 10:36
已完成: 生成研究角色 · 1 项 10:38
```

**特点:**
- ✅ 简洁，不显示详细内容
- ✅ 按类型分组，易于理解
- ❌ 不显示具体内容
- ❌ 不显示推理内容（因为推理内容被分组到相同描述下）

### StreamContentBubble（详细视图，未使用）

如果使用`StreamContentBubble`，会显示：
- 每个item的完整内容
- 推理内容独立显示（带琥珀色样式）
- 按时间顺序交错显示

---

## 多个Stream同时进行的场景

### 场景1: 并行处理多个任务

**示例:**
- Stream A: 正在生成研究角色
- Stream B: 正在处理转录摘要
- Stream C: 正在执行初始分析

**处理方式:**
1. 每个stream独立接收token
2. 每个stream的内容独立存储
3. Timeline items按时间戳交错显示
4. Summary view按描述分组显示

**显示效果:**
```
正在生成研究角色 · 1 项
正在处理转录摘要 · 3 项
正在执行初始分析 · 1 项
```

### 场景2: 同一类型多个实例

**示例:**
- Stream A: 处理转录摘要 (link_id: link1)
- Stream B: 处理转录摘要 (link_id: link2)
- Stream C: 处理转录摘要 (link_id: link3)

**处理方式:**
- `StreamSummaryView`会合并显示为：
  ```
  正在处理转录摘要 · 3 项
  ```
- 使用`completedLinkIds`和`inProgressLinkIds`避免重复计数

### 场景3: 推理内容和正常内容交错

**示例:**
- Stream A的推理内容在10:00:01
- Stream A的正常内容在10:00:02
- Stream B的推理内容在10:00:01.5

**显示顺序:**
1. Stream A的推理内容 (10:00:01)
2. Stream B的推理内容 (10:00:01.5)
3. Stream A的正常内容 (10:00:02)

**关键点:**
- 推理内容和正常内容**完全按时间戳排序**
- 不同stream的内容会**交错显示**
- 推理内容永远不折叠，始终显示

---

## 潜在问题和限制

### 1. 内容交错可能造成混乱

**问题:**
- 当多个stream同时进行时，不同stream的内容会交错显示
- 用户可能难以区分哪些内容属于哪个stream

**当前缓解:**
- Summary view按描述分组，隐藏了交错问题
- 每个item有subtitle显示阶段和步骤信息

### 2. 推理内容可能被分组隐藏

**问题:**
- `StreamSummaryView`按描述分组
- 推理内容和正常内容可能被分到同一组
- 推理内容不会单独显示在summary中

**当前状态:**
- 推理内容在summary view中**不会单独显示**
- 只有在详细视图（如果启用）中才会显示推理内容

### 3. activeStreamId的限制

**问题:**
- `activeStreamId`只指向一个stream
- 当多个stream同时进行时，只有一个被认为是"active"
- 可能影响某些UI状态（如streaming indicator）

**当前实现:**
- 每个stream的`isStreaming`状态独立管理
- `activeStreamId`主要用于某些特定的UI逻辑

---

## 改进建议

### 选项1: 按Stream分组显示

在详细视图中，可以按stream ID分组：

```
┌─ Stream A: 生成研究角色 ─┐
│ 💭 推理过程: ...          │
│ 正常内容: ...             │
└──────────────────────────┘

┌─ Stream B: 处理转录摘要 ─┐
│ 💭 推理过程: ...          │
│ 正常内容: ...             │
└──────────────────────────┘
```

### 选项2: 显示Stream标识

在每个item上显示stream ID或标识：

```
[Stream-A] 💭 推理过程: ...
[Stream-B] 💭 推理过程: ...
[Stream-A] 正常内容: ...
```

### 选项3: 在Summary中显示推理内容

修改`StreamSummaryView`，为推理内容创建独立的分组：

```
正在推理: 生成研究角色 · 2 项
正在生成研究角色 · 1 项
已完成: 处理转录摘要 · 7 项
```

---

## 总结

**当前机制:**
1. ✅ 支持多个stream同时进行
2. ✅ 每个stream独立存储和管理
3. ✅ 所有items按时间戳排序显示
4. ✅ Summary view按描述分组，简洁明了
5. ⚠️ 推理内容在summary中不单独显示
6. ⚠️ 多个stream的内容会交错显示

**适用场景:**
- ✅ 适合并行处理多个独立任务
- ✅ 适合需要按时间顺序查看所有活动
- ⚠️ 不适合需要按stream分组查看的场景

---

**文档状态:** 技术说明文档  
**最后更新:** 2025-01-27

