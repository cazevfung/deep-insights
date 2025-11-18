import React from 'react'
import { PhaseTimelineItem } from '../../hooks/usePhaseInteraction'
import StreamSummaryView from './StreamSummaryView'

interface StreamTimelineProps {
  items: PhaseTimelineItem[]
  visibleCount: number
  onShowMore: () => void
  hasMore: boolean
  onDismiss?: (item: PhaseTimelineItem) => void
}

const StreamTimeline: React.FC<StreamTimelineProps> = ({
  items,
  visibleCount,
  onShowMore,
  hasMore,
  onDismiss,
}) => {
  // Use all items for summary (no need to slice - summary groups them)
  return (
    <div className="space-y-2">
      {/* Load more button (only if there are many items) */}
      {hasMore && items.length > 50 && (
        <button
          type="button"
          onClick={onShowMore}
          className="w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-[10px] text-neutral-600 transition hover:border-primary-200 hover:bg-primary-50 hover:text-primary-600"
        >
          显示详细信息
        </button>
      )}

      {/* Summary view - groups items and shows counts */}
      <StreamSummaryView items={items} onDismiss={onDismiss} />
    </div>
  )
}

export default StreamTimeline
