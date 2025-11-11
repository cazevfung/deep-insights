import React, { useMemo } from 'react'
import Button from '../common/Button'
import { PhaseTimelineItem } from '../../hooks/usePhaseInteraction'
import Phase0SummaryDisplay from '../streaming/Phase0SummaryDisplay'

interface StreamContentBubbleProps {
  item: PhaseTimelineItem
  collapsed: boolean
  onToggle: (item: PhaseTimelineItem) => void
  onCopy: (item: PhaseTimelineItem) => void
  isActive: boolean
}

const badgeVariantMap: Record<PhaseTimelineItem['statusVariant'], string> = {
  info: 'bg-primary-100 text-primary-700',
  success: 'bg-emerald-100 text-emerald-700',
  warning: 'bg-amber-100 text-amber-700',
  error: 'bg-secondary-100 text-secondary-700',
}

const StreamContentBubble: React.FC<StreamContentBubbleProps> = ({ item, collapsed, onToggle, onCopy, isActive }) => {
  const badgeClass = badgeVariantMap[item.statusVariant]

  // Try to parse message as JSON and check if it's a Phase 0 summary
  const parsedSummary = useMemo(() => {
    try {
      const parsed = JSON.parse(item.message)
      // Check if this looks like a Phase 0 summary (transcript or comments)
      const isTranscriptSummary = 
        parsed.key_facts || parsed.key_opinions || parsed.key_datapoints || parsed.topic_areas
      const isCommentsSummary = 
        parsed.key_facts_from_comments || parsed.key_opinions_from_comments || parsed.major_themes
      
      if (isTranscriptSummary || isCommentsSummary) {
        return parsed
      }
    } catch {
      // Not valid JSON or not a Phase 0 summary, will render as text
    }
    return null
  }, [item.message])

  return (
    <div
      className={`rounded-xl border px-4 py-4 shadow-sm transition ${
        isActive ? 'border-primary-300 ring-2 ring-primary-200/60 bg-primary-50/40' : 'border-neutral-200 bg-neutral-white'
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2 text-sm font-semibold text-neutral-800">
            <span>{item.title}</span>
            {item.subtitle && (
              <span className="rounded-full bg-neutral-200 px-2 py-0.5 text-xs text-neutral-600">
                {item.subtitle}
              </span>
            )}
            <span className={`rounded-full px-2 py-0.5 text-xs ${badgeClass}`}>
              {item.status === 'active' ? '进行中' : item.status === 'completed' ? '已完成' : '错误'}
            </span>
            {item.timestamp && (
              <span className="text-xs text-neutral-400">
                {new Date(item.timestamp).toLocaleTimeString('zh-CN', { hour12: false })}
              </span>
            )}
          </div>
          {item.isStreaming && (
            <span className="flex items-center gap-2 text-xs text-primary-500">
              <span className="h-2 w-2 rounded-full bg-primary-500 animate-pulse" />
              正在流式输出…
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {item.isCollapsible && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="px-3 py-1 text-xs"
              onClick={() => onToggle(item)}
            >
              {collapsed ? '展开' : '收起'}
            </Button>
          )}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="px-3 py-1 text-xs"
            onClick={() => onCopy(item)}
          >
            复制
          </Button>
        </div>
      </div>
      <div className="mt-3 rounded-lg bg-neutral-50 px-3 py-2 text-sm text-neutral-700">
        {parsedSummary ? (
          // Render Phase 0 summary with specialized component
          collapsed && item.isCollapsible ? (
            <p className="whitespace-pre-wrap leading-relaxed text-neutral-600">{item.preview}</p>
          ) : (
            <Phase0SummaryDisplay data={parsedSummary} />
          )
        ) : (
          // Render as plain text
          item.isCollapsible && collapsed ? (
            <p className="whitespace-pre-wrap leading-relaxed text-neutral-600">{item.preview}</p>
          ) : (
            <pre className="whitespace-pre-wrap leading-relaxed text-neutral-700">{item.message}</pre>
          )
        )}
      </div>
    </div>
  )
}

export default StreamContentBubble
