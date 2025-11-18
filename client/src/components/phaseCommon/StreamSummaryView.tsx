import React, { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import { PhaseTimelineItem } from '../../hooks/usePhaseInteraction'
import { Icon } from '../common/Icon'

interface StreamSummaryViewProps {
  items: PhaseTimelineItem[]
  onDismiss?: (item: PhaseTimelineItem) => void
}

// Generate process description from metadata (same as ProcessTextItem)
const generateProcessDescription = (item: PhaseTimelineItem): string => {
  const { metadata, stepLabel } = item

  if (!metadata) {
    return '处理中'
  }

  const stageLabel = metadata.stage_label || metadata.component
  if (stageLabel) {
    const stageMap: Record<string, string> = {
      'phase4-outline': '生成报告大纲',
      'phase4-coverage': '生成覆盖检查',
      'phase4-article': '生成最终报告',
      'Phase4-Outline': '生成报告大纲',
      'Phase4-Coverage': '生成覆盖检查',
      'Phase4-Article': '生成最终报告',
    }
    if (stageMap[stageLabel]) {
      return stageMap[stageLabel]
    }
  }

  if (metadata.component) {
    const componentMap: Record<string, string> = {
      role_generation: '生成研究角色',
      goal_generation: '生成研究目标',
      synthesis: '综合研究结果',
      step_initial: '执行初始分析',
      step_followup: '执行补充分析',
      json_repair: '修复JSON格式',
      transcript: '处理转录摘要',
      comments: '处理评论摘要',
      summarization: '生成内容摘要',
    }
    const description = componentMap[metadata.component]
    if (description) {
      return description
    }
  }

  if (stepLabel) {
    return `处理 ${stepLabel}`
  }

  return '处理中'
}

interface GroupedItem {
  description: string
  completed: number
  inProgress: number
  errors: PhaseTimelineItem[]
  lastUpdate?: string
  // Track unique link_ids for transcript/comments summaries to avoid double counting
  completedLinkIds?: Set<string>
  inProgressLinkIds?: Set<string>
}

const normalizeListChildren = (children: React.ReactNode) =>
  React.Children.map(children, (child) => {
    if (!React.isValidElement(child)) {
      if (typeof child === 'string') {
        return child.replace(/\n+/g, ' ').trim()
      }
      return child
    }
    if (child.type === 'p') {
      const existing = child.props.className || ''
      return (
        <span className={`text-[10px] leading-tight ${existing}`.trim()}>
          {child.props.children}
        </span>
      )
    }
    return child
  })

const reasoningMarkdownComponents = {
  h1: (props: any) => (
    <p className="font-semibold text-[14px] text-neutral-1000 whitespace-pre-wrap mb-2 mt-3 tracking-tight" {...props} />
  ),
  h2: (props: any) => (
    <p className="font-semibold text-[12px] text-neutral-900 whitespace-pre-wrap mb-2 mt-3 tracking-tight" {...props} />
  ),
  h3: (props: any) => (
    <p className="font-semibold text-[11px] text-neutral-800 whitespace-pre-wrap mb-2 mt-3 tracking-tight" {...props} />
  ),
  h4: (props: any) => (
    <p className="font-semibold text-[10.5px] text-neutral-800 whitespace-pre-wrap mb-2 mt-3 tracking-tight" {...props} />
  ),
  h5: (props: any) => (
    <p className="font-semibold text-[10px] text-neutral-800 whitespace-pre-wrap mb-2 mt-3 tracking-tight" {...props} />
  ),
  h6: (props: any) => (
    <p className="font-semibold text-[10px] text-neutral-700 whitespace-pre-wrap mb-2 mt-3 tracking-tight uppercase" {...props} />
  ),
  p: (props: any) => (
    <p className="text-[10px] text-neutral-600 leading-relaxed mb-2 mt-3 whitespace-pre-wrap" {...props} />
  ),
  ul: (props: any) => <ul className="list-disc pl-4 text-[10px] text-neutral-600 space-y-0 my-0 py-0" {...props} />,
  ol: (props: any) => <ol className="list-decimal pl-4 text-[10px] text-neutral-600 space-y-0 my-0 py-0" {...props} />,
  li: (props: any) => (
    <li className="text-[10px] leading-tight my-0 py-0 marker:text-neutral-400">
      {normalizeListChildren(props.children)}
    </li>
  ),
  strong: (props: any) => <strong className="font-semibold text-neutral-700" {...props} />,
  em: (props: any) => <em className="not-italic text-neutral-600" {...props} />,
}

const StreamSummaryView: React.FC<StreamSummaryViewProps> = ({ items, onDismiss }) => {

  // Reasoning items to show individually
  const reasoningItems = useMemo(() => {
    const filtered = items
      .filter((item) => {
        if (item.type !== 'reasoning') return false
        // Show if has content OR is streaming (don't use trim - we want to show text as it streams)
        const hasContent = item.message && item.message.length > 0
        const isStreaming = item.isStreaming && item.status === 'active'
        
        // Debug logging
        if (item.type === 'reasoning') {
          console.log('🔍 Reasoning item check:', {
            id: item.id,
            hasMessage: !!item.message,
            messageLength: item.message?.length || 0,
            messagePreview: item.message?.substring(0, 50) || '(empty)',
            isStreaming,
            willShow: hasContent || isStreaming,
          })
        }
        
        return hasContent || isStreaming
      })
    
    console.log('🔍 Total reasoning items to show:', filtered.length)
    return filtered
  }, [items])

  // Group items by description/type (excluding reasoning and status items)
  const grouped = useMemo(() => {
    const groups = new Map<string, GroupedItem>()

    items.forEach((item) => {
      // Skip reasoning and status items - they are displayed individually
      if (item.type === 'reasoning' || item.type === 'status') {
        return
      }

      const isStreaming = item.isStreaming && item.status === 'active'
      const isCompleted = item.status === 'completed' || (!item.isStreaming && item.status === 'active')
      const isError = item.status === 'error' || item.statusVariant === 'error'

      const description = generateProcessDescription(item)
      const key = description

      // Check if this is a transcript or comments summary (which should be counted by unique link_id)
      const isTranscriptOrCommentsSummary = item.metadata?.component === 'transcript' || item.metadata?.component === 'comments'
      const linkId = item.metadata?.link_id

      if (!groups.has(key)) {
        groups.set(key, {
          description,
          completed: 0,
          inProgress: 0,
          errors: [],
          // Initialize link_id tracking for transcript/comments summaries
          ...(isTranscriptOrCommentsSummary && {
            completedLinkIds: new Set<string>(),
            inProgressLinkIds: new Set<string>(),
          }),
        })
      }

      const group = groups.get(key)!
      if (isError) {
        group.errors.push(item)
      } else if (isCompleted) {
        // For transcript/comments summaries, count unique link_ids instead of stream items
        if (isTranscriptOrCommentsSummary && linkId) {
          if (!group.completedLinkIds) {
            group.completedLinkIds = new Set<string>()
          }
          // Only increment if this link_id hasn't been counted yet
          if (!group.completedLinkIds.has(linkId)) {
            group.completedLinkIds.add(linkId)
            group.completed++
            // Track latest completion time
            if (item.timestamp && (!group.lastUpdate || item.timestamp > group.lastUpdate)) {
              group.lastUpdate = item.timestamp
            }
          }
        } else {
          // For other types, count normally
          group.completed++
          // Track latest completion time
          if (item.timestamp && (!group.lastUpdate || item.timestamp > group.lastUpdate)) {
            group.lastUpdate = item.timestamp
          }
        }
      } else if (isStreaming) {
        // For transcript/comments summaries, count unique link_ids instead of stream items
        if (isTranscriptOrCommentsSummary && linkId) {
          if (!group.inProgressLinkIds) {
            group.inProgressLinkIds = new Set<string>()
          }
          // Only increment if this link_id hasn't been counted yet
          if (!group.inProgressLinkIds.has(linkId)) {
            group.inProgressLinkIds.add(linkId)
            group.inProgress++
          }
        } else {
          // For other types, count normally
          group.inProgress++
        }
      }
    })

    return Array.from(groups.values())
      .filter((g) => g.completed > 0 || g.inProgress > 0 || g.errors.length > 0)
  }, [items])

  // Merge reasoning items and grouped items, sorted chronologically
  const mergedTimeline = useMemo(() => {
    interface TimelineEntry {
      type: 'reasoning' | 'group'
      timestamp: number
      item?: PhaseTimelineItem
      group?: GroupedItem
    }

    const entries: TimelineEntry[] = []

    // Add reasoning items
    reasoningItems.forEach((item) => {
      entries.push({
        type: 'reasoning',
        timestamp: item.timestamp ? new Date(item.timestamp).getTime() : 0,
        item,
      })
    })

    // Add grouped items
    grouped.forEach((group) => {
      // Use lastUpdate for completed groups, or current time for in-progress groups
      let timestamp = 0
      if (group.lastUpdate) {
        timestamp = new Date(group.lastUpdate).getTime()
      } else if (group.inProgress > 0) {
        timestamp = Date.now() // In-progress items appear at the end
      }
      
      entries.push({
        type: 'group',
        timestamp,
        group,
      })
    })

    // Sort by timestamp
    const sorted = entries.sort((a, b) => a.timestamp - b.timestamp)
    
    console.log('🔍 Merged timeline:', {
      totalEntries: sorted.length,
      reasoningCount: sorted.filter(e => e.type === 'reasoning').length,
      groupCount: sorted.filter(e => e.type === 'group').length,
      entries: sorted.map(e => ({
        type: e.type,
        timestamp: e.timestamp,
        message: e.item?.message?.substring(0, 30) || e.group?.description,
      })),
    })
    
    return sorted
  }, [reasoningItems, grouped])

  const formatTimestamp = (timestamp: string): string => {
    try {
      return new Date(timestamp).toLocaleTimeString('zh-CN', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return ''
    }
  }

  const cardContainerClasses =
    'rounded-xl border border-neutral-100 bg-neutral-50 px-3 py-2 text-[10px]'

  if (mergedTimeline.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-neutral-200 bg-neutral-50 px-3 py-12 text-center text-[10px] text-neutral-500">
        暂无消息，发起研究后将实时显示
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {/* Merged timeline - reasoning items and grouped summaries in chronological order */}
      {mergedTimeline.map((entry, idx) => {
        if (entry.type === 'reasoning' && entry.item) {
          const item = entry.item
          const isStreaming = item.isStreaming && item.status === 'active'
          
          console.log('🔍 Rendering reasoning item:', {
            id: item.id,
            message: item.message?.substring(0, 50) || '(empty)',
            messageLength: item.message?.length || 0,
            isStreaming,
          })
          
          return (
            <div key={item.id} className="flex items-start gap-1.5 text-[10px] text-neutral-600 px-1">
              <span
                className={`text-neutral-400 flex-shrink-0 flex items-center leading-none ${isStreaming ? 'animate-pulse' : ''}`}
                style={{ fontStyle: 'normal', height: '1.6em' }}
              >
                <Icon name="message-circle" size={12} />
              </span>
              <div className="flex-1 leading-relaxed text-[10px] text-neutral-600">
                {item.message && item.message.trim() ? (
                  <ReactMarkdown components={reasoningMarkdownComponents}>{item.message}</ReactMarkdown>
                ) : (
                  <span className="text-neutral-600 font-normal">正在思考...</span>
                )}
              </div>
              {item.timestamp && (
                <span className="text-neutral-300 text-[9px] flex-shrink-0" style={{ fontStyle: 'normal' }}>
                  {formatTimestamp(item.timestamp)}
                </span>
              )}
            </div>
          )
        }

        if (entry.type === 'group' && entry.group) {
          const group = entry.group
          return (
            <div key={`group-${idx}`} className={`${cardContainerClasses} space-y-0.5`}>
              {/* Errors */}
              {group.errors.length > 0 && (
                <div className="text-red-600 flex items-center gap-2">
                  <span>⚠️ 错误 ({group.errors.length}): {group.description}</span>
                  {onDismiss && (
                    <button
                      type="button"
                      onClick={() => group.errors.forEach((item) => onDismiss?.(item))}
                      className="text-neutral-400 hover:text-neutral-600 transition-colors"
                      title="关闭"
                    >
                      ×
                    </button>
                  )}
                </div>
              )}

              {/* In progress - show only if there are active items */}
              {group.inProgress > 0 && (
                <div className="text-primary-600">
                  正在{group.description} · {group.inProgress} 项
                </div>
              )}

              {/* Completed - show count only */}
              {group.completed > 0 && (
                <div className="text-neutral-500 flex items-center gap-2">
                  <span>已完成: {group.description} · {group.completed} 项</span>
                  {group.lastUpdate && (
                    <span className="text-neutral-300 text-[9px]">{formatTimestamp(group.lastUpdate)}</span>
                  )}
                </div>
              )}
            </div>
          )
        }

        return null
      })}
    </div>
  )
}

export default StreamSummaryView

