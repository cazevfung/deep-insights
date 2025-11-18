import React from 'react'
import ProgressBar from './ProgressBar'

interface LinkProgressItemProps {
  item: {
    link_id?: string
    url: string
    status: 'pending' | 'in-progress' | 'completed' | 'failed'
    error?: string
    current_stage?: string
    stage_progress?: number
    overall_progress?: number
    status_message?: string
    started_at?: string
    completed_at?: string
    source?: string
    word_count?: number
    bytes_downloaded?: number
    total_bytes?: number
  }
  isNew?: boolean
}

const LinkProgressItem: React.FC<LinkProgressItemProps> = ({ item, isNew = false }) => {
  const isActive = item.status === 'in-progress' || item.status === 'pending'
  const progress = item.overall_progress !== undefined 
    ? item.overall_progress 
    : item.stage_progress !== undefined 
      ? item.stage_progress 
      : 0

  return (
    <div
      className={`p-4 bg-gray-50 rounded-xl border transition-colors ${
        isNew
          ? 'border-primary-500 new-item-highlight'
          : 'border-gray-200 hover:border-primary-500'
      }`}
    >
      <div className="flex items-center space-x-2 mb-3">
        <p className={`text-sm font-medium text-gray-900 truncate flex-1 ${isNew ? 'shiny-text-once' : ''}`}>
          {item.url}
        </p>
      </div>

      {/* Progress Bar */}
      {isActive && progress > 0 && (
        <ProgressBar progress={progress} />
      )}
    </div>
  )
}

export default LinkProgressItem
