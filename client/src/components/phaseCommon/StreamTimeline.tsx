import React from 'react'
import { PhaseTimelineItem } from '../../hooks/usePhaseInteraction'
import StreamStatusStatement from './StreamStatusStatement'
import StreamContentBubble from './StreamContentBubble'

interface StreamTimelineProps {
  items: PhaseTimelineItem[]
  collapsedState: Record<string, boolean>
  onToggleCollapse: (item: PhaseTimelineItem) => void
  onCopy: (item: PhaseTimelineItem) => void
  activeStreamId: string | null
  visibleCount: number
  onShowMore: () => void
  hasMore: boolean
}

const StreamTimeline: React.FC<StreamTimelineProps> = ({
  items,
  collapsedState,
  onToggleCollapse,
  onCopy,
  activeStreamId,
  visibleCount,
  onShowMore,
  hasMore,
}) => {
  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-neutral-200 bg-neutral-50 px-3 py-8 text-center text-xs text-neutral-500">
        暂无流式内容，发起研究后将实时显示
      </div>
    )
  }

  // Show the last N items (most recent) - newest at bottom
  const startIndex = Math.max(0, items.length - visibleCount)
  const visibleItems = items.slice(startIndex)

  return (
    <div className="space-y-2">
      {hasMore && (
        <button
          type="button"
          onClick={onShowMore}
          className="w-full rounded-lg border border-neutral-200 bg-neutral-50 py-1.5 text-xs text-neutral-600 transition hover:border-primary-200 hover:text-primary-600"
        >
          显示更早的消息
        </button>
      )}

      {visibleItems.map((item) => {
        if (item.type === 'status') {
          return <StreamStatusStatement key={item.id} item={item} />
        }
        const collapsed = collapsedState[item.id] ?? item.defaultCollapsed
        const isActive = activeStreamId === item.id && item.status === 'active'
        return (
          <StreamContentBubble
            key={item.id}
            item={item}
            collapsed={collapsed}
            onToggle={onToggleCollapse}
            onCopy={onCopy}
            isActive={isActive}
          />
        )
      })}
    </div>
  )
}

export default StreamTimeline
