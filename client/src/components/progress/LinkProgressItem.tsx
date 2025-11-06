import React from 'react'
import StatusBadge from './StatusBadge'
import ProgressBar from './ProgressBar'
import { Icon } from '../common/Icon'

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
  const getStatusBadgeStatus = () => {
    switch (item.status) {
      case 'completed':
        return 'success'
      case 'failed':
        return 'error'
      case 'in-progress':
        return 'pending'
      default:
        return 'info'
    }
  }

  const getStatusText = () => {
    switch (item.status) {
      case 'completed':
        return '已完成'
      case 'failed':
        return 'OMG出错了'
      case 'in-progress':
        return '某种努力中'
      default:
        return '等待Ta的出现'
    }
  }

  const getStatusIcon = () => {
    switch (item.status) {
      case 'completed':
        return <Icon name="check-circle" size={18} strokeWidth={2.5} className="text-supportive-green" />
      case 'failed':
        return <Icon name="x-circle" size={18} strokeWidth={2.5} className="text-secondary-500" />
      case 'in-progress':
        return <Icon name="refresh" size={18} strokeWidth={2.5} className="text-primary-400 animate-spin" />
      default:
        return <Icon name="circle" size={18} strokeWidth={2.5} className="text-neutral-400" />
    }
  }

  const formatStageName = (stage?: string) => {
    if (!stage) return ''
    const stageMap: Record<string, string> = {
      loading: '加载中',
      downloading: '下载中',
      converting: '正在转换成人话',
      uploading: '上传处理中',
      transcribing: '正在生成文字稿',
      extracting: '正在阅读内容',
      completed: '已完成',
      unknown: '某种努力中',
    }
    return stageMap[stage] || stage
  }

  const formatBytes = (bytes?: number) => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  const formatTime = (isoString?: string) => {
    if (!isoString) return ''
    const date = new Date(isoString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffSecs = Math.floor(diffMs / 1000)
    
    if (diffSecs < 60) return `${diffSecs}秒前`
    if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)}分钟前`
    return `${Math.floor(diffSecs / 3600)}小时前`
  }

  const isActive = item.status === 'in-progress' || item.status === 'pending'

  return (
    <div
      className={`p-4 bg-neutral-light-bg rounded-lg border transition-colors ${
        isNew
          ? 'border-primary-500 new-item-highlight'
          : 'border-neutral-border hover:border-primary-500'
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 mb-1">
            {getStatusIcon()}
            <p className={`text-sm font-medium text-neutral-black truncate ${isNew ? 'shiny-text-once' : ''}`}>
              {item.url}
            </p>
          </div>
          {item.source && (
            <span className="text-xs text-neutral-secondary">
              来源: {item.source}
            </span>
          )}
        </div>
        <StatusBadge status={getStatusBadgeStatus()}>
          {getStatusText()}
        </StatusBadge>
      </div>

      {/* Status Message */}
      {item.status_message && (
        <div className="mb-2 text-sm text-neutral-secondary">
          {item.status_message}
          {item.bytes_downloaded && item.total_bytes && (
            <span className="ml-2">
              ({formatBytes(item.bytes_downloaded)} / {formatBytes(item.total_bytes)})
            </span>
          )}
        </div>
      )}

      {/* Progress Bars */}
      {isActive && (
        <div className="space-y-2 mb-2">
          {item.overall_progress !== undefined && (
            <div>
              <div className="flex justify-between text-xs text-neutral-secondary mb-1">
                <span>整体进度</span>
                <span className="shiny-text-pulse">{item.overall_progress.toFixed(1)}%</span>
              </div>
              <ProgressBar progress={item.overall_progress} />
            </div>
          )}
          {item.current_stage && item.stage_progress !== undefined && (
            <div>
              <div className="flex justify-between text-xs text-neutral-secondary mb-1">
                <span className="shiny-text-once">
                  当前: {formatStageName(item.current_stage)}
                </span>
                <span className="shiny-text-pulse">{item.stage_progress.toFixed(1)}%</span>
              </div>
              <ProgressBar progress={item.stage_progress} />
            </div>
          )}
        </div>
      )}

      {/* Completed Info */}
      {item.status === 'completed' && (
        <div className="text-sm text-neutral-secondary space-y-1">
          {item.word_count && (
            <div>内容字数: {item.word_count.toLocaleString()}</div>
          )}
          {item.completed_at && (
            <div>完成于: {formatTime(item.completed_at)}</div>
          )}
        </div>
      )}

      {/* Error Message */}
      {item.status === 'failed' && item.error && (
        <div className="mt-2 text-sm text-error-main bg-error-light p-2 rounded">
          {item.error}
        </div>
      )}

      {/* Active Indicator Animation */}
      {isActive && (
        <div className="flex items-center space-x-2 mt-2">
          <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse"></div>
          <span className="text-xs text-neutral-secondary">正在处理...</span>
        </div>
      )}
    </div>
  )
}

export default LinkProgressItem
