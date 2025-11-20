# Reasoning Content 显示研究文档

**日期:** 2025-01-27  
**状态:** 研究文档（不实施）  
**优先级:** 中

## 概述

本文档研究如何在右侧栏聊天界面中显示AI token stream中的`reasoning_content`，并将其作为有时间顺序的文本显示。

---

## 当前系统架构分析

### 1. 数据流架构

```
WebSocket消息 → workflowStore → usePhaseInteraction → PhaseInteractionPanel → StreamTimeline → StreamContentBubble
```

**关键组件:**

1. **workflowStore** (`client/src/stores/workflowStore.ts`):
   - 管理所有stream状态
   - `StreamBufferState` 存储stream数据:
     ```typescript
     interface StreamBufferState {
       id: string
       raw: string  // 当前存储完整文本内容
       status: 'active' | 'completed' | 'error'
       tokenCount: number
       lastTokenAt?: string | null
       metadata?: Record<string, any> | null
     }
     ```
   - `appendStreamToken(streamId, token)` 方法追加token到`raw`字段

2. **usePhaseInteraction** (`client/src/hooks/usePhaseInteraction.ts`):
   - 将stream buffers转换为`PhaseTimelineItem[]`
   - `PhaseTimelineItem`包含:
     ```typescript
     interface PhaseTimelineItem {
       id: string
       message: string  // 来自buffer.raw
       isStreaming: boolean
       status: 'active' | 'completed' | 'error'
       metadata?: Record<string, any> | null
       timestamp: string | null
     }
     ```

3. **PhaseInteractionPanel** (`client/src/components/phaseCommon/PhaseInteractionPanel.tsx`):
   - 显示timeline items
   - 处理滚动和用户交互

4. **StreamTimeline** (`client/src/components/phaseCommon/StreamTimeline.tsx`):
   - 渲染timeline items列表

5. **StreamContentBubble** (`client/src/components/phaseCommon/StreamContentBubble.tsx`):
   - 显示单个timeline item的内容
   - 支持折叠/展开、复制等功能

### 2. 当前Token处理方式

**WebSocket消息处理流程:**

1. WebSocket接收消息（假设格式）:
   ```json
   {
     "type": "research:stream",
     "stream_id": "stream_123",
     "delta": {
       "content": "新的token文本",
       "reasoning_content": "推理内容token"  // 需要提取
     },
     "metadata": {...}
   }
   ```

2. 当前实现只处理`delta.content`，追加到`buffer.raw`

3. `reasoning_content`可能被忽略或包含在`delta.content`中

---

## 阿里云Stream API分析

根据阿里云文档 (https://help.aliyun.com/zh/model-studio/stream)，流式输出可能包含以下字段:

### 可能的Stream响应结构

```json
{
  "output": {
    "choices": [{
      "message": {
        "content": "正常输出内容",
        "role": "assistant"
      },
      "finish_reason": null
    }],
    "usage": {...}
  },
  "reasoning_content": "推理过程内容",  // 推理内容字段
  "request_id": "..."
}
```

或者可能是嵌套结构:

```json
{
  "delta": {
    "content": "正常内容token",
    "reasoning_content": "推理内容token"  // 推理内容增量
  },
  "stream_id": "..."
}
```

### 关键观察

1. **reasoning_content可能是独立字段**: 与`content`分离，需要单独处理
2. **reasoning_content可能是增量更新**: 每个token都包含新的推理片段
3. **时间顺序**: reasoning_content应该按照接收顺序显示
4. **显示位置**: 应该在聊天界面中作为独立的文本消息显示

---

## 实现方案研究

### 方案1: 扩展StreamBufferState存储reasoning_content

**数据结构变更:**

```typescript
interface StreamBufferState extends StreamState {
  id: string
  raw: string  // 正常内容
  reasoning: string  // 新增: 推理内容
  status: 'active' | 'completed' | 'error'
  tokenCount: number
  reasoningTokenCount: number  // 新增: 推理token计数
  lastTokenAt?: string | null
  lastReasoningTokenAt?: string | null  // 新增: 最后推理token时间
  metadata?: Record<string, any> | null
}
```

**workflowStore变更:**

```typescript
// 新增方法
appendReasoningToken: (streamId: string, token: string) => void

// 实现
appendReasoningToken: (streamId, token) => {
  set((state) => {
    const buffer = state.researchAgentStatus.streams.buffers[streamId]
    if (!buffer) return state
    
    const lastReasoningTokenAt = new Date().toISOString()
    return {
      researchAgentStatus: {
        ...state.researchAgentStatus,
        streams: {
          ...state.researchAgentStatus.streams,
          buffers: {
            ...state.researchAgentStatus.streams.buffers,
            [streamId]: {
              ...buffer,
              reasoning: (buffer.reasoning || '') + token,
              reasoningTokenCount: (buffer.reasoningTokenCount || 0) + 1,
              lastReasoningTokenAt,
            }
          }
        }
      }
    }
  })
}
```

**WebSocket消息处理变更:**

```typescript
// 在WebSocket消息处理中
if (message.type === 'research:stream') {
  const { stream_id, delta } = message
  
  if (delta.content) {
    store.getState().appendStreamToken(stream_id, delta.content)
  }
  
  // 新增: 处理reasoning_content
  if (delta.reasoning_content) {
    store.getState().appendReasoningToken(stream_id, delta.reasoning_content)
  }
}
```

### 方案2: 创建独立的ReasoningTimelineItem

**数据结构:**

```typescript
interface ReasoningTimelineItem {
  id: string
  streamId: string  // 关联的stream ID
  content: string
  isStreaming: boolean
  timestamp: string | null
  type: 'reasoning'  // 标识为推理内容
}
```

**usePhaseInteraction变更:**

```typescript
const reasoningItems = useMemo<ReasoningTimelineItem[]>(() => {
  return Object.entries(streams.buffers)
    .filter(([_, buffer]) => buffer.reasoning && buffer.reasoning.length > 0)
    .map(([streamId, buffer]) => ({
      id: `reasoning:${streamId}`,
      streamId,
      content: buffer.reasoning,
      isStreaming: buffer.isStreaming,
      timestamp: buffer.lastReasoningTokenAt || buffer.lastTokenAt || null,
      type: 'reasoning' as const,
    }))
}, [streams.buffers])
```

**显示逻辑:**

在`PhaseInteractionPanel`中，将reasoning items与普通timeline items合并，按时间顺序显示:

```typescript
const allItems = useMemo(() => {
  const combined = [...timelineItems, ...reasoningItems]
  return combined.sort((a, b) => {
    const aTime = a.timestamp ? new Date(a.timestamp).getTime() : 0
    const bTime = b.timestamp ? new Date(b.timestamp).getTime() : 0
    return aTime - bTime
  })
}, [timelineItems, reasoningItems])
```

### 方案3: 在StreamContentBubble中显示reasoning_content

**组件变更:**

在`StreamContentBubble`中，如果item有reasoning内容，显示在单独的区域:

```typescript
const StreamContentBubble: React.FC<StreamContentBubbleProps> = ({ item }) => {
  const reasoningContent = item.metadata?.reasoning_content || null
  
  return (
    <div>
      {/* 正常内容 */}
      <div>{item.message}</div>
      
      {/* 推理内容区域 */}
      {reasoningContent && (
        <div className="mt-2 pt-2 border-t border-neutral-200">
          <div className="text-[9px] text-neutral-400 mb-1">推理过程:</div>
          <div className="text-[10px] text-neutral-600 italic">
            {reasoningContent}
          </div>
        </div>
      )}
    </div>
  )
}
```

**优点:**
- 推理内容与正常内容关联显示
- 不需要创建新的timeline item

**缺点:**
- 推理内容不是独立的时间序列消息
- 如果推理内容很长，可能影响正常内容显示

---

## 推荐方案: 混合方案

结合方案1和方案2的优点:

### 1. 数据结构扩展

```typescript
interface StreamBufferState extends StreamState {
  id: string
  raw: string
  reasoning: string  // 新增
  status: 'active' | 'completed' | 'error'
  tokenCount: number
  reasoningTokenCount: number  // 新增
  lastTokenAt?: string | null
  lastReasoningTokenAt?: string | null  // 新增
  metadata?: Record<string, any> | null
}
```

### 2. Timeline Item扩展

```typescript
interface PhaseTimelineItem {
  id: string
  type: TimelineItemType | 'reasoning'  // 新增'reasoning'类型
  title: string
  message: string
  reasoning?: string  // 新增: 推理内容
  isStreaming: boolean
  // ... 其他字段
}
```

### 3. 显示策略

**选项A: 独立显示推理内容**

在`usePhaseInteraction`中，为每个有reasoning内容的stream创建两个items:
1. 正常内容item (type: 'content')
2. 推理内容item (type: 'reasoning')

```typescript
const timelineItems = useMemo<PhaseTimelineItem[]>(() => {
  const items: PhaseTimelineItem[] = []
  
  orderedIds.forEach((id) => {
    const buffer = streams.buffers[id]
    if (!buffer) return
    
    // 正常内容item
    items.push({
      id: `${id}:content`,
      type: 'content',
      message: buffer.raw,
      // ...
    })
    
    // 推理内容item (如果有)
    if (buffer.reasoning && buffer.reasoning.length > 0) {
      items.push({
        id: `${id}:reasoning`,
        type: 'reasoning',
        title: '推理过程',
        message: buffer.reasoning,
        isStreaming: buffer.isStreaming,
        timestamp: buffer.lastReasoningTokenAt || buffer.lastTokenAt,
        // ...
      })
    }
  })
  
  return items.sort((a, b) => {
    // 按时间排序
    const aTime = a.timestamp ? new Date(a.timestamp).getTime() : 0
    const bTime = b.timestamp ? new Date(b.timestamp).getTime() : 0
    return aTime - bTime
  })
}, [streams])
```

**选项B: 在同一个bubble中显示**

在`StreamContentBubble`中，如果item有reasoning内容，显示在折叠区域:

```typescript
const StreamContentBubble: React.FC<StreamContentBubbleProps> = ({ item }) => {
  const hasReasoning = item.type === 'reasoning' || item.reasoning
  
  return (
    <div>
      {item.type === 'reasoning' ? (
        // 推理内容专用显示
        <div className="bg-amber-50 border-l-2 border-amber-300 pl-3 py-2">
          <div className="text-[9px] text-amber-600 mb-1 font-medium">
            💭 推理过程
          </div>
          <div className="text-[10px] text-neutral-700 leading-relaxed">
            <ReactMarkdown>{item.message}</ReactMarkdown>
          </div>
        </div>
      ) : (
        // 正常内容显示
        <div>{item.message}</div>
      )}
    </div>
  )
}
```

### 4. 视觉设计建议

**推理内容样式:**

- **背景色**: 浅黄色/浅蓝色 (`bg-amber-50` 或 `bg-blue-50`)
- **边框**: 左侧彩色边框 (`border-l-2 border-amber-300`)
- **图标**: 💭 或 🧠 表示推理
- **字体**: 稍小字体 (`text-[10px]`)，斜体或正常
- **动画**: 如果正在streaming，使用shiny动画

**时间顺序显示:**

- 推理内容和正常内容按`timestamp`排序
- 如果推理内容和正常内容时间相同，推理内容显示在正常内容之前（因为推理通常先于输出）

---

## WebSocket消息处理实现

### 消息格式假设

```typescript
interface StreamDelta {
  content?: string
  reasoning_content?: string  // 推理内容增量
}

interface StreamMessage {
  type: 'research:stream'
  stream_id: string
  delta: StreamDelta
  metadata?: Record<string, any>
}
```

### 处理逻辑

```typescript
// 在WebSocket消息处理中
function handleStreamMessage(message: StreamMessage) {
  const { stream_id, delta, metadata } = message
  const store = useWorkflowStore.getState()
  
  // 确保stream存在
  if (!store.researchAgentStatus.streams.buffers[stream_id]) {
    store.startStream(stream_id, {
      phase: metadata?.phase,
      metadata: metadata,
      startedAt: new Date().toISOString(),
    })
  }
  
  // 处理正常内容
  if (delta.content) {
    store.appendStreamToken(stream_id, delta.content)
  }
  
  // 处理推理内容
  if (delta.reasoning_content) {
    store.appendReasoningToken(stream_id, delta.reasoning_content)
  }
  
  // 更新streaming状态
  store.updateResearchAgentStatus({
    streamingState: {
      isStreaming: true,
      lastTokenAt: new Date().toISOString(),
    }
  })
}
```

---

## 技术考虑

### 1. 性能优化

- **防抖处理**: reasoning_content更新可能很频繁，需要防抖
- **虚拟滚动**: 如果推理内容很多，考虑虚拟滚动
- **增量更新**: 只更新变化的DOM部分

### 2. 状态管理

- **分离存储**: reasoning和content分开存储，便于独立更新
- **时间戳**: 记录每个token的时间戳，确保时间顺序正确
- **完成状态**: 推理内容完成后，标记为completed

### 3. 用户体验

- **视觉区分**: 推理内容和正常内容有明显视觉区分
- **折叠选项**: 推理内容可以折叠，避免占用太多空间
- **搜索功能**: 如果实现搜索，需要包含推理内容

### 4. 数据持久化

- **会话保存**: reasoning_content应该保存在会话数据中
- **导出功能**: 导出时包含推理内容

---

## 实施步骤（如果决定实施）

### Phase 1: 数据结构扩展

1. 扩展`StreamBufferState`接口，添加`reasoning`字段
2. 在`workflowStore`中添加`appendReasoningToken`方法
3. 更新WebSocket消息处理，提取`reasoning_content`

### Phase 2: Timeline Item扩展

1. 扩展`PhaseTimelineItem`，支持`reasoning`类型
2. 在`usePhaseInteraction`中生成reasoning items
3. 按时间顺序合并reasoning items和content items

### Phase 3: UI组件更新

1. 更新`StreamContentBubble`，支持显示reasoning内容
2. 或创建新的`ReasoningContentBubble`组件
3. 添加推理内容的样式和动画

### Phase 4: 测试和优化

1. 测试reasoning_content的流式显示
2. 测试时间顺序是否正确
3. 优化性能和用户体验

---

## 开放问题

1. **reasoning_content的实际格式**: 
   - 需要确认阿里云API返回的reasoning_content的确切格式
   - 是增量更新还是完整内容？
   - 是否包含markdown格式？

2. **显示策略**:
   - 独立显示还是与正常内容一起显示？
   - 是否需要折叠功能？
   - 是否需要搜索功能？

3. **性能考虑**:
   - reasoning_content可能很长，如何优化渲染？
   - 是否需要分页或虚拟滚动？

4. **用户体验**:
   - 推理内容对用户的价值是什么？
   - 是否需要可配置的显示/隐藏选项？

---

## 参考资料

- 阿里云Model Studio流式输出文档: https://help.aliyun.com/zh/model-studio/stream
- 当前实现:
  - `client/src/stores/workflowStore.ts`
  - `client/src/hooks/usePhaseInteraction.ts`
  - `client/src/components/phaseCommon/PhaseInteractionPanel.tsx`
  - `client/src/components/phaseCommon/StreamContentBubble.tsx`
- 相关设计文档:
  - `docs/frontend/RIGHT_COLUMN_TEXT_ONLY_STREAMING_PLAN.md`

---

**文档状态:** 研究完成 - 等待实施决策  
**最后更新:** 2025-01-27

