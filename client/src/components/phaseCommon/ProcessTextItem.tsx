import React, { useMemo, useState } from 'react'
import { PhaseTimelineItem } from '../../hooks/usePhaseInteraction'

interface ProcessTextItemProps {
  item: PhaseTimelineItem
  onDismiss?: (item: PhaseTimelineItem) => void
}

// Generate simple process description from metadata
const generateProcessDescription = (item: PhaseTimelineItem): string => {
  const { metadata, stepLabel } = item

  if (!metadata) {
    return '正在处理中...'
  }

  // Check for stage_label or component (Phase 4 stages)
  const stageLabel = metadata.stage_label || metadata.component
  if (stageLabel) {
    const stageMap: Record<string, string> = {
      'phase4-outline': '正在生成报告大纲',
      'phase4-coverage': '正在生成覆盖检查',
      'phase4-article': '正在生成最终报告',
      'Phase4-Outline': '正在生成报告大纲',
      'Phase4-Coverage': '正在生成覆盖检查',
      'Phase4-Article': '正在生成最终报告',
    }
    if (stageMap[stageLabel]) {
      return stageMap[stageLabel]
    }
  }

  // Check for component
  if (metadata.component) {
    const componentMap: Record<string, string> = {
      role_generation: '正在生成研究角色',
      goal_generation: '正在生成研究目标',
      synthesis: '正在综合研究结果',
      step_initial: '正在执行初始分析',
      step_followup: '正在执行补充分析',
      json_repair: '正在修复JSON格式',
      transcript: '正在处理转录摘要',
      comments: '正在处理评论摘要',
      summarization: '正在生成内容摘要',
    }
    const description = componentMap[metadata.component]
    if (description) {
      return description
    }
  }

  // Use stepLabel if available
  if (stepLabel) {
    return `正在处理 ${stepLabel}`
  }

  // Fallback
  return '正在处理中...'
}

const ProcessTextItem: React.FC<ProcessTextItemProps> = ({ item, onDismiss }) => {
  const [isExpanded, setIsExpanded] = useState(false)

  const isStreaming = item.isStreaming && item.status === 'active'
  const isCompleted = item.status === 'completed' || (!item.isStreaming && item.status === 'active')
  const isError = item.status === 'error' || item.statusVariant === 'error'
  const isStatus = item.type === 'status'

  const description = useMemo(() => {
    if (isStatus) {
      return item.message || item.title
    }
    return generateProcessDescription(item)
  }, [item, isStatus])

  const displayText = useMemo(() => {
    if (isCompleted && !isStatus) {
      // Remove "正在" and "..." from description for completed items
      const cleanDescription = description.replace(/^正在/, '').replace(/\.\.\.$/, '')
      return `已完成: ${cleanDescription}`
    }
    if (isError) {
      return `⚠️  错误: ${description}`
    }
    // Add "..." for streaming items
    if (isStreaming && !description.endsWith('...')) {
      return `${description}...`
    }
    return description
  }, [description, isCompleted, isError, isStreaming, isStatus])

  const handleDismiss = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (onDismiss) {
      onDismiss(item)
    }
  }

  const handleToggleExpand = () => {
    if (isError && item.message) {
      setIsExpanded(!isExpanded)
    }
  }

  // Format timestamp for display
  const formatTimestamp = (timestamp: string | null): string => {
    if (!timestamp) return ''
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

  return (
    <div
      className={`
        text-sm transition-colors duration-300
        ${isStreaming ? 'text-primary-600 shiny-text-streaming' : ''}
        ${isCompleted ? 'text-gray-500' : ''}
        ${isError ? 'text-red-600 cursor-pointer' : ''}
        ${isStatus ? 'text-neutral-600' : ''}
      `}
      onClick={isError ? handleToggleExpand : undefined}
    >
      <div className="flex items-center gap-2">
        <span>{displayText}</span>
        {isCompleted && item.timestamp && (
          <span className="text-[10px] text-gray-300">
            {formatTimestamp(item.timestamp)}
          </span>
        )}
        {isError && onDismiss && (
          <button
            type="button"
            onClick={handleDismiss}
            className="ml-auto text-[10px] text-gray-400 hover:text-gray-600 transition-colors"
            title="关闭"
          >
            ×
          </button>
        )}
      </div>
      {isError && isExpanded && item.message && (
        <div className="mt-1 text-xs text-red-500 whitespace-pre-wrap break-words">
          {item.message}
        </div>
      )}
    </div>
  )
}

export default ProcessTextItem

