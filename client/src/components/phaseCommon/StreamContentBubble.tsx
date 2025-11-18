import React, { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import Button from '../common/Button'
import { PhaseTimelineItem } from '../../hooks/usePhaseInteraction'
import Phase0SummaryDisplay from '../streaming/Phase0SummaryDisplay'

interface StreamContentBubbleProps {
  item: PhaseTimelineItem
  collapsed: boolean
  onToggle: (item: PhaseTimelineItem) => void
  onPin?: (item: PhaseTimelineItem) => void
  onCopy: (item: PhaseTimelineItem) => void
  isActive: boolean
  isPinned?: boolean
}

const badgeVariantMap: Record<PhaseTimelineItem['statusVariant'], string> = {
  info: 'bg-primary-100 text-primary-700',
  success: 'bg-emerald-100 text-emerald-700',
  warning: 'bg-amber-100 text-amber-700',
  error: 'bg-secondary-100 text-secondary-700',
}

// Helper function to determine response type from message content
const determineResponseTypeFromContent = (message: string | null | undefined): 'request' | 'final' | 'analyzing' | null => {
  if (!message) return null
  
  try {
    // Try to parse as JSON
    const parsed = JSON.parse(message)
    if (typeof parsed !== 'object' || parsed === null) return null
    
    // Check if it has requests/missing_context but no findings (request type)
    const hasRequests = (parsed.requests && Array.isArray(parsed.requests) && parsed.requests.length > 0) ||
                       (parsed.missing_context && Array.isArray(parsed.missing_context) && parsed.missing_context.length > 0)
    const hasFindings = parsed.findings && typeof parsed.findings === 'object'
    
    if (hasRequests && !hasFindings) {
      return 'request'
    }
    if (hasFindings) {
      return 'final'
    }
  } catch {
    // Not valid JSON or can't determine, return null
  }
  
  return null
}

// Generate summary text from metadata for collapsed streaming state
const generateSummaryText = (metadata: Record<string, any> | null | undefined, stepLabel: string | null, message?: string | null): string => {
  if (!metadata) {
    return '正在处理中...'
  }

  // Check for stage_label or component first (Phase 4 stages)
  const stageLabel = metadata.stage_label || metadata.component
  if (stageLabel) {
    const stageMap: Record<string, string> = {
      'phase4-outline': '正在生成报告大纲...',
      'phase4-coverage': '正在生成覆盖检查...',
      'phase4-article': '正在生成最终报告...',
      'Phase4-Outline': '正在生成报告大纲...',
      'Phase4-Coverage': '正在生成覆盖检查...',
      'Phase4-Article': '正在生成最终报告...',
    }
    if (stageMap[stageLabel]) {
      return stageMap[stageLabel]
    }
  }

  // Check for step_id (Phase 3 steps)
  if (metadata.step_id) {
    const goal = metadata.goal || ''
    const goalPreview = goal.length > 30 ? goal.substring(0, 30) + '...' : goal
    return `正在分析步骤 ${metadata.step_id}${goalPreview ? `: ${goalPreview}` : ''}...`
  }

  // Check for component label with response_type
  if (metadata.component) {
    // Determine actual response type from metadata or message content
    const responseType = metadata.response_type || determineResponseTypeFromContent(message) || 'analyzing'
    
    const componentMap: Record<string, Record<string, string>> = {
      step_initial: {
        request: '正在请求更多信息...',
        final: '正在生成最终分析...',
        analyzing: '正在执行初始分析...',
      },
      step_followup: {
        request: '正在请求补充信息...',
        final: '正在完善最终答案...',
        analyzing: '正在执行补充分析...',
      },
      role_generation: {
        analyzing: '正在生成研究角色...',
      },
      goal_generation: {
        analyzing: '正在生成研究目标...',
      },
      synthesis: {
        analyzing: '正在综合研究结果...',
      },
      json_repair: {
        analyzing: '正在修复JSON格式...',
      },
    }
    
    const componentMessages = componentMap[metadata.component]
    if (componentMessages) {
      return componentMessages[responseType] || componentMessages['analyzing'] || '正在处理中...'
    }
  }

  // Use stepLabel if available
  if (stepLabel) {
    return `正在处理 ${stepLabel}...`
  }

  // Fallback
  return '正在处理中...'
}

const StreamContentBubble: React.FC<StreamContentBubbleProps> = ({ 
  item, 
  collapsed, 
  onToggle, 
  onPin,
  onCopy, 
  isActive,
  isPinned = false,
}) => {
  const badgeClass = badgeVariantMap[item.statusVariant]

  // Generate summary text for collapsed streaming state
  const summaryText = useMemo(() => {
    if (collapsed && item.isStreaming && item.status === 'active') {
      return generateSummaryText(item.metadata, item.stepLabel, item.message)
    }
    return null
  }, [collapsed, item.isStreaming, item.status, item.metadata, item.stepLabel, item.message])

  // Try to parse message as JSON and check if it's a Phase 0 summary
  const parsedSummary = useMemo(() => {
    try {
      const parsed = JSON.parse(item.message)
      // Check if this looks like a Phase 0 summary (transcript or comments)
      // Handle both flat structure (from stream) and nested structure (from backend)
      const transcriptSummary = parsed.transcript_summary || parsed
      const commentsSummary = parsed.comments_summary || parsed
      const summaryType = parsed.summary_type || parsed.type || item.metadata?.summary_type
      
      const isTranscriptSummary = 
        summaryType === 'transcript' ||
        transcriptSummary.key_facts || 
        transcriptSummary.key_opinions || 
        transcriptSummary.key_datapoints || 
        transcriptSummary.topic_areas
      
      const isCommentsSummary = 
        summaryType === 'comments' ||
        commentsSummary.key_facts_from_comments || 
        commentsSummary.key_opinions_from_comments || 
        commentsSummary.major_themes
      
      if (isTranscriptSummary || isCommentsSummary) {
        return parsed
      }
    } catch {
      // Not valid JSON or not a Phase 0 summary, will render as text
    }
    return null
  }, [item.message, item.metadata])

  // Chat-like styling: simpler, cleaner appearance
  const isCritical = item.status === 'error' || item.statusVariant === 'error'
  const isStreaming = item.isStreaming && item.status === 'active'
  const isReasoning = item.type === 'reasoning'

  if (isReasoning) {
    const timestampText = item.timestamp
      ? new Date(item.timestamp).toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit' })
      : ''

    return (
      <div className="flex items-start gap-2 px-1 py-1 text-[12px] text-neutral-600">
        <span className={`flex-shrink-0 text-amber-500 ${isStreaming ? 'animate-pulse' : ''}`}>💭</span>
        <div className="flex-1 space-y-1">
          <div className="prose prose-xs max-w-none prose-p:my-1 prose-strong:text-neutral-800 prose-em:not-italic text-neutral-700 leading-relaxed">
            {item.message && item.message.trim() ? (
              <ReactMarkdown>{item.message}</ReactMarkdown>
            ) : isStreaming ? (
              <div className="text-amber-500">正在思考...</div>
            ) : null}
          </div>
          {timestampText && (
            <div className="text-[10px] text-neutral-400">
              {timestampText}
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={() => onCopy(item)}
          className="p-1 rounded hover:bg-neutral-100 text-neutral-400 transition-colors text-[10px]"
          title="复制思考内容"
        >
          📋
        </button>
      </div>
    )
  }

  return (
    <div
      className={`rounded-lg border transition-all duration-200 ${
        isActive || isStreaming
          ? 'border-primary-300 bg-primary-50/30 shadow-sm'
          : isCritical
          ? 'border-amber-300 bg-amber-50/30 shadow-sm'
          : collapsed
          ? 'border-neutral-200 bg-neutral-50/50'
          : 'border-neutral-200 bg-neutral-white shadow-sm'
      } ${isPinned ? 'ring-1 ring-primary-200' : ''} ${collapsed ? 'opacity-90' : ''}`}
    >
      {/* Chat-like header: minimal, clean */}
      <div className={`flex items-start justify-between gap-2 px-3 ${collapsed ? 'py-2' : 'py-3'}`}>
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {/* AI icon/indicator */}
          <div className="flex-shrink-0">
            {isStreaming ? (
              <span className="h-2 w-2 rounded-full bg-primary-500 animate-pulse" />
            ) : isCritical ? (
              <span className="text-amber-500 text-[10px]">⚠️</span>
            ) : (
              <span className="text-neutral-400 text-[10px]">🤖</span>
            )}
          </div>
          
          {/* Title/subtitle - chat-like */}
          <div className="flex items-center gap-1.5 min-w-0 flex-1">
            {item.subtitle && (
              <span className="text-[10px] font-medium text-neutral-600 truncate">
                {item.subtitle}
              </span>
            )}
            {item.timestamp && (
              <span className="text-[10px] text-neutral-400 flex-shrink-0">
                {new Date(item.timestamp).toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>
        </div>

        {/* Actions - minimal, chat-like */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {onPin && (
            <button
              type="button"
              onClick={() => onPin(item)}
              className={`p-1 rounded hover:bg-neutral-100 transition-colors ${
                isPinned ? 'text-primary-500' : 'text-neutral-400'
              }`}
              title={isPinned ? '取消固定' : '固定消息'}
            >
              <svg className="w-3.5 h-3.5" fill={isPinned ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
            </button>
          )}
          {item.isCollapsible && (
            <button
              type="button"
              onClick={() => onToggle(item)}
              className="p-1 rounded hover:bg-neutral-100 text-neutral-400 transition-colors text-[10px]"
            >
              {collapsed ? '▼' : '▲'}
            </button>
          )}
          <button
            type="button"
            onClick={() => onCopy(item)}
            className="p-1 rounded hover:bg-neutral-100 text-neutral-400 transition-colors text-[10px]"
            title="复制"
          >
            📋
          </button>
        </div>
      </div>

      {/* Content - chat message style */}
      <div className={`px-3 ${collapsed ? 'pb-2 pt-0' : 'pb-3 pt-0'}`}>
        <div className={`rounded-md ${collapsed ? 'bg-transparent' : 'bg-transparent'} ${collapsed ? 'px-3 py-1' : 'px-3 py-2'}`}>
        {parsedSummary ? (
          // Render Phase 0 summary with specialized component
          collapsed && item.isCollapsible ? (
            <div className="prose prose-xs max-w-none prose-p:my-1 prose-strong:text-neutral-600">
              <ReactMarkdown>{item.preview}</ReactMarkdown>
            </div>
          ) : (
            <Phase0SummaryDisplay data={parsedSummary} />
          )
        ) : (
          // Render as plain text or markdown
          item.isCollapsible && collapsed ? (
            // Show summary text with shining animation if streaming, otherwise show preview
            summaryText ? (
              <div className="prose prose-xs max-w-none prose-p:my-1 prose-strong:text-neutral-600 relative">
                <div className="relative z-10">
                  <ReactMarkdown>{summaryText}</ReactMarkdown>
                </div>
                <span 
                  className="absolute inset-0 z-20 pointer-events-none"
                  style={{
                    background: 'linear-gradient(90deg, transparent 0%, rgba(148,163,184,0.4) 50%, transparent 100%)',
                    backgroundSize: '200% 100%',
                    animation: 'shine 2.5s ease-in-out infinite',
                    mixBlendMode: 'overlay',
                  }}
                />
              </div>
            ) : (
              <div className="text-[10px] text-neutral-500 leading-relaxed">
                {item.preview || '已折叠'}
              </div>
            )
          ) : (
            <div className={`prose prose-xs max-w-none prose-p:my-1 prose-strong:text-neutral-700 prose-pre:bg-transparent prose-pre:p-0 prose-pre:border-0 prose-sm ${!collapsed ? 'max-h-[400px] overflow-y-auto' : ''}`}>
              <ReactMarkdown>{item.message}</ReactMarkdown>
            </div>
          )
        )}
        </div>
      </div>
    </div>
  )
}

export default StreamContentBubble
