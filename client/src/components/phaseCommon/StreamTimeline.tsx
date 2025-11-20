import React from 'react'
import { PhaseTimelineItem } from '../../hooks/usePhaseInteraction'
import StreamSummaryView from './StreamSummaryView'

interface StreamTimelineProps {
  items: PhaseTimelineItem[]
  visibleCount: number
  onShowMore: () => void
  hasMore: boolean
  onDismiss?: (item: PhaseTimelineItem) => void
  onPin?: (item: PhaseTimelineItem) => void
  pinnedItems?: Set<string>
  onScrollToPinned?: (itemId: string) => void
}

const StreamTimeline: React.FC<StreamTimelineProps> = ({
  items,
  visibleCount,
  onShowMore,
  hasMore,
  onDismiss,
  onPin,
  pinnedItems,
  onScrollToPinned,
}) => {
  // Use all items for summary (no need to slice - summary groups them)
  return (
    <div className="space-y-2">
      {/* Pinned items navigation */}
      {pinnedItems && pinnedItems.size > 0 && onScrollToPinned && (
        <div className="sticky top-0 z-10 bg-neutral-white/95 backdrop-blur-sm border-b border-neutral-200 px-2 py-1.5 mb-2 rounded-lg">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[12px] text-neutral-500">固定:</span>
            {Array.from(pinnedItems).map((itemId) => {
              const item = items.find((i) => i.id === itemId)
              if (!item) return null
              return (
                <button
                  key={itemId}
                  type="button"
                  onClick={() => onScrollToPinned(itemId)}
                  className="px-2 py-0.5 rounded text-[12px] bg-primary-100 text-primary-700 hover:bg-primary-200 transition-colors"
                  title={item.subtitle || item.title}
                >
                  📌 {item.subtitle || item.title}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Load more button (only if there are many items) */}
      {hasMore && items.length > 50 && (
        <button
          type="button"
          onClick={onShowMore}
          className="w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-[13px] text-neutral-600 transition hover:border-primary-200 hover:bg-primary-50 hover:text-primary-600"
        >
          显示详细信息
        </button>
      )}

      {/* Summary view - groups items and shows counts */}
      <StreamSummaryView 
        items={items} 
        onDismiss={onDismiss}
        onPin={onPin}
        pinnedItems={pinnedItems}
      />
    </div>
  )
}

export default StreamTimeline
