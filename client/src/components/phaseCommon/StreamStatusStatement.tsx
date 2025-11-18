import React from 'react'
import { PhaseTimelineItem } from '../../hooks/usePhaseInteraction'

interface StreamStatusStatementProps {
  item: PhaseTimelineItem
}

const variantClassMap: Record<PhaseTimelineItem['statusVariant'], string> = {
  info: 'border-primary-200 bg-primary-50/70 text-primary-700',
  success: 'border-emerald-200 bg-emerald-50/80 text-emerald-700',
  warning: 'border-amber-200 bg-amber-50/80 text-amber-700',
  error: 'border-secondary-200 bg-secondary-50/80 text-secondary-700',
}

const StreamStatusStatement: React.FC<StreamStatusStatementProps> = ({ item }) => {
  const variantClasses = variantClassMap[item.statusVariant]

  return (
    <div className={`rounded-lg border px-3 py-1.5 text-[10px] shadow-sm ${variantClasses}`}>
      <div className="flex flex-wrap items-center gap-1.5 font-medium">
        <span>{item.title}</span>
        {item.subtitle && <span className="text-[10px] text-current/80">{item.subtitle}</span>}
        {item.timestamp && (
          <span className="ml-auto text-[10px] uppercase tracking-wide text-current/70">
            {new Date(item.timestamp).toLocaleTimeString('zh-CN', { hour12: false })}
          </span>
        )}
      </div>
      {item.message && (
        <p className="mt-0.5 text-[10px] leading-relaxed text-current/90">
          {item.message}
        </p>
      )}
    </div>
  )
}

export default StreamStatusStatement
