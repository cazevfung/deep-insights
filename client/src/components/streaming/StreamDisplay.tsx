import React, { useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import Card from '../common/Card'
import Button from '../common/Button'
import { streamDesignTokens } from './streamDesignTokens'

export type StreamViewMode = 'stacked' | 'tabs' | 'split'

interface StreamDisplayProps {
  content: string
  phase?: string | null
  metadata?: Record<string, any> | null
  isStreaming?: boolean
  title?: string
  subtitle?: string | React.ReactNode
  showCopyButton?: boolean
  collapsible?: boolean
  className?: string
  minHeight?: string
  maxHeight?: string
  secondaryView?: React.ReactNode
  viewMode?: StreamViewMode
  toolbar?: React.ReactNode
}

const formatMetadataValue = (value: any): string => {
  if (value === null || value === undefined) {
    return '—'
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  try {
    return JSON.stringify(value)
  } catch (error) {
    return String(value)
  }
}

const StreamDisplay: React.FC<StreamDisplayProps> = ({
  content,
  phase,
  metadata,
  isStreaming = false,
  title,
  subtitle,
  showCopyButton = true,
  collapsible = false,
  className = '',
  minHeight = streamDesignTokens.sizing.minHeight,
  maxHeight = streamDesignTokens.sizing.maxHeight,
  secondaryView,
  viewMode: providedViewMode,
  toolbar,
}) => {
  const [isExpanded, setIsExpanded] = useState(true)
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied'>('idle')
  const [activeTab, setActiveTab] = useState<'raw' | 'structured'>(() => (secondaryView ? 'structured' : 'raw'))
  const streamRef = useRef<HTMLDivElement>(null)

  const hasSecondaryView = Boolean(secondaryView)
  const viewMode: StreamViewMode = hasSecondaryView ? providedViewMode || 'tabs' : providedViewMode || 'stacked'

  useEffect(() => {
    if (hasSecondaryView) {
      setActiveTab('structured')
    } else {
      setActiveTab('raw')
    }
  }, [hasSecondaryView])

  useEffect(() => {
    if (isExpanded && streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight
    }
  }, [content, isExpanded])

  const handleCopy = async () => {
    if (!showCopyButton || !content) {
      return
    }
    try {
      await navigator.clipboard.writeText(content)
      setCopyStatus('copied')
      setTimeout(() => setCopyStatus('idle'), 2000)
    } catch (error) {
      console.warn('Failed to copy stream buffer:', error)
    }
  }

  const metadataEntries = useMemo(() => {
    if (!metadata) {
      return []
    }
    return Object.entries(metadata).map(([key, value]) => ({
      key,
      value: formatMetadataValue(value),
    }))
  }, [metadata])

  const displayTitle = title || 'AI 响应流'

  const header = (
    <div className="flex w-full flex-col gap-2">
      <div className="flex w-full flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-base font-semibold text-neutral-black">{displayTitle}</span>
          {phase && (
            <span className="rounded-full bg-neutral-300 px-2 py-0.5 text-xs text-neutral-500">
              {phase}
            </span>
          )}
          <span
            className={`inline-flex h-2 w-2 items-center justify-center rounded-full ${
              isStreaming ? streamDesignTokens.colors.indicatorActive : streamDesignTokens.colors.indicatorIdle
            } ${isStreaming ? streamDesignTokens.animations.pulse : ''}`}
            aria-hidden="true"
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {toolbar}
          {collapsible && (
            <Button variant="ghost" size="sm" onClick={() => setIsExpanded((prev) => !prev)} className="text-xs">
              {isExpanded ? '收起' : '展开'}
            </Button>
          )}
          {showCopyButton && (
            <Button variant="ghost" size="sm" onClick={handleCopy} className="text-xs">
              {copyStatus === 'copied' ? '已复制' : '复制'}
            </Button>
          )}
        </div>
      </div>
      {subtitle && <div className="text-sm text-neutral-500">{subtitle}</div>}
      {metadataEntries.length > 0 && (
        <div className="flex flex-wrap gap-2 text-xs text-neutral-500">
          {metadataEntries.map(({ key, value }) => (
            <span key={key} className="rounded-md bg-neutral-300/60 px-2 py-1 text-neutral-600">
              <span className="mr-1 font-medium text-neutral-black">{key}:</span>
              {value}
            </span>
          ))}
        </div>
      )}
      {hasSecondaryView && viewMode === 'tabs' && (
        <div className="flex items-center gap-3 text-sm">
          <button
            type="button"
            className={`stream-tab ${activeTab === 'structured' ? 'stream-tab-active' : ''}`}
            onClick={() => setActiveTab('structured')}
          >
            结构化
          </button>
          <button
            type="button"
            className={`stream-tab ${activeTab === 'raw' ? 'stream-tab-active' : ''}`}
            onClick={() => setActiveTab('raw')}
          >
            原始流
          </button>
        </div>
      )}
    </div>
  )

  const rawContent = (
    <div className="stream-raw-container">
      <div className="stream-raw-header">
        <div className="stream-raw-header-controls" aria-hidden="true">
          <span className="stream-raw-dot stream-raw-dot-red" />
          <span className="stream-raw-dot stream-raw-dot-yellow" />
          <span className="stream-raw-dot stream-raw-dot-green" />
        </div>
        <span className="stream-raw-title">原始流</span>
      </div>
      <div
        ref={streamRef}
        className={`stream-content stream-raw-body ${minHeight} ${isExpanded ? maxHeight : ''} ${
          isExpanded ? 'overflow-auto' : 'overflow-hidden'
        }`}
      >
        {content ? (
          isExpanded ? (
            <div className="stream-content-text prose prose-sm prose-neutral max-w-none">
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          ) : (
            <p className="stream-content-preview">
              {content.length > 160 ? `${content.slice(0, 160)}…` : content}
            </p>
          )
        ) : (
          <p className="text-sm text-neutral-400">思考中...</p>
        )}
      </div>
    </div>
  )

  const structuredContent = secondaryView ? (
    <div className={`stream-structured ${isExpanded ? maxHeight : ''}`}>{secondaryView}</div>
  ) : null

  let body: React.ReactNode = rawContent

  if (hasSecondaryView) {
    if (viewMode === 'tabs') {
      body = activeTab === 'raw' ? rawContent : structuredContent
    } else if (viewMode === 'split') {
      body = (
        <div className="grid gap-4 md:grid-cols-2">
          <div>{rawContent}</div>
          <div className="max-h-full overflow-auto">{structuredContent}</div>
        </div>
      )
    } else {
      body = (
        <div className="flex flex-col gap-4">
          {rawContent}
          <div className="max-h-full overflow-auto">{structuredContent}</div>
        </div>
      )
    }
  }

  return (
    <Card className={`stream-display-container ${className}`} title={header}>
      {body}
    </Card>
  )
}

export default StreamDisplay
