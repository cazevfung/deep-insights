import React, { useCallback, useEffect, useMemo, useState, useRef } from 'react'
import { usePhaseInteraction, PhaseTimelineItem } from '../../hooks/usePhaseInteraction'
import { useWorkflowStore } from '../../stores/workflowStore'
import { useUiStore } from '../../stores/uiStore'
import Button from '../common/Button'
import StreamTimeline from './StreamTimeline'
import { apiService } from '../../services/api'

interface PhaseInteractionPanelProps {
  onSendMessage: (type: string, data: any) => void
}

const formatLatency = (lastTokenAt?: string | null): string => {
  if (!lastTokenAt) {
    return '暂无延迟数据'
  }
  const delta = Date.now() - new Date(lastTokenAt).getTime()
  if (Number.isNaN(delta) || delta < 0) {
    return '延迟未知'
  }
  if (delta < 1000) {
    return `${delta}ms`
  }
  return `${Math.round(delta / 1000)}s`
}

const PhaseInteractionPanel: React.FC<PhaseInteractionPanelProps> = ({ onSendMessage }) => {
  const {
    timelineItems,
    combinedRaw,
    latestUpdateAt,
    statusIndicatorClass,
    statusLabel,
    activeStreamId,
    isStreaming,
    waitingForUser,
    userInputRequired,
    currentAction,
    phase,
    summarizationProgress,
  } = usePhaseInteraction()
  const { addNotification } = useUiStore()
  const [draft, setDraft] = useState('')
  const [isConversationSending, setIsConversationSending] = useState(false)
  const [collapsedState, setCollapsedState] = useState<Record<string, boolean>>({})
  const [visibleCount, setVisibleCount] = useState(8)
  const [promptSubmitted, setPromptSubmitted] = useState(false)
  const [isPromptExiting, setIsPromptExiting] = useState(false)
  const [lastProcessedPromptId, setLastProcessedPromptId] = useState<string | null>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  // Track auto-collapse: streamId -> { thresholdMs, startTime, manuallyExpanded }
  const autoCollapseRef = useRef<Record<string, { thresholdMs: number; startTime: number; manuallyExpanded: boolean }>>({})
  const batchId = useWorkflowStore((state) => state.batchId)
  const sessionId = useWorkflowStore((state) => state.sessionId)

  const promptId = userInputRequired?.prompt_id
  const hasProceduralPrompt =
    waitingForUser && typeof promptId === 'string' && promptId.trim().length > 0 && !promptSubmitted
  
  // Debug logging for state
  useEffect(() => {
    console.log('🔍 PhaseInteractionPanel state:', {
      waitingForUser,
      promptId,
      promptSubmitted,
      hasProceduralPrompt,
      userInputRequired: userInputRequired ? {
        type: userInputRequired.type,
        prompt_id: userInputRequired.prompt_id,
        hasPrompt: !!userInputRequired.data?.prompt,
      } : null,
    })
  }, [waitingForUser, promptId, promptSubmitted, hasProceduralPrompt, userInputRequired])

  const choiceOptions = useMemo(() => {
    const rawChoices = userInputRequired?.data?.choices
    if (Array.isArray(rawChoices)) {
      return rawChoices.filter((choice): choice is string => typeof choice === 'string' && choice.trim().length > 0)
    }
    return []
  }, [userInputRequired?.data?.choices])

  // Reset promptSubmitted when a new prompt arrives
  useEffect(() => {
    // If waitingForUser becomes false, reset everything
    if (!waitingForUser) {
      setPromptSubmitted(false)
      setIsPromptExiting(false)
      setLastProcessedPromptId(null)
      return
    }

    // If we have a new prompt_id that's different from the last one, reset promptSubmitted
    if (waitingForUser && promptId && promptId !== lastProcessedPromptId) {
      console.log('🔄 New prompt detected, resetting promptSubmitted', {
        oldPromptId: lastProcessedPromptId,
        newPromptId: promptId,
      })
      setPromptSubmitted(false)
      setIsPromptExiting(false)
      setLastProcessedPromptId(promptId)
    }
  }, [waitingForUser, promptId, lastProcessedPromptId])

  // Initialize auto-collapse tracking for new streaming items
  useEffect(() => {
    timelineItems.forEach((item) => {
      if (item.isStreaming && item.status === 'active' && !autoCollapseRef.current[item.id]) {
        // Generate random threshold between 2-4 seconds
        const thresholdMs = 2000 + Math.random() * 2000 // 2000-4000ms
        autoCollapseRef.current[item.id] = {
          thresholdMs,
          startTime: Date.now(),
          manuallyExpanded: false,
        }
        // Start expanded (not collapsed) for streaming items
        setCollapsedState((prev) => {
          if (prev[item.id] === undefined) {
            return { ...prev, [item.id]: false } // false = expanded
          }
          return prev
        })
      }
      // Clean up completed streams
      if (item.status !== 'active' && autoCollapseRef.current[item.id]) {
        delete autoCollapseRef.current[item.id]
      }
    })
  }, [timelineItems])

  // Auto-collapse logic: check elapsed time and collapse if threshold passed
  useEffect(() => {
    const interval = setInterval(() => {
      setCollapsedState((prev) => {
        const next = { ...prev }
        let changed = false

        timelineItems.forEach((item) => {
          const autoCollapse = autoCollapseRef.current[item.id]
          if (!autoCollapse || autoCollapse.manuallyExpanded) {
            return // Skip if not tracked or manually expanded
          }

          if (item.isStreaming && item.status === 'active') {
            const elapsed = Date.now() - autoCollapse.startTime
            if (elapsed >= autoCollapse.thresholdMs && !next[item.id]) {
              // Auto-collapse: set to true (collapsed)
              next[item.id] = true
              changed = true
            }
          }
        })

        return changed ? next : prev
      })
    }, 100) // Check every 100ms

    return () => clearInterval(interval)
  }, [timelineItems])

  useEffect(() => {
    setCollapsedState((prev) => {
      const next: Record<string, boolean> = {}
      timelineItems.forEach((item) => {
        const previous = prev[item.id]
        if (item.type === 'status') {
          next[item.id] = false
        } else {
          // If user has manually toggled, keep their preference
          // But if it's streaming or never been set, use defaultCollapsed
          const hasBeenManuallyToggled = typeof previous === 'boolean' && !item.isStreaming
          next[item.id] = hasBeenManuallyToggled ? previous : item.defaultCollapsed
        }
      })
      return next
    })
  }, [timelineItems])

  useEffect(() => {
    if (timelineItems.length > 0) {
      setVisibleCount((prev) => Math.max(8, prev))
    }
  }, [timelineItems.length])

  // Auto-scroll to bottom when new items are added
  useEffect(() => {
    if (!scrollContainerRef.current) return

    const container = scrollContainerRef.current
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 150

    // Only auto-scroll if user is already near the bottom (to avoid disrupting manual scrolling)
    if (isNearBottom || timelineItems.length === 1) {
      // Use requestAnimationFrame to ensure DOM has updated
      requestAnimationFrame(() => {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: 'smooth',
        })
      })
    }
  }, [timelineItems.length, timelineItems[timelineItems.length - 1]?.id])

  const handleToggleCollapse = useCallback((item: PhaseTimelineItem) => {
    if (item.type === 'status') {
      return
    }
    setCollapsedState((prev) => {
      const newCollapsed = !(prev[item.id] ?? item.defaultCollapsed)
      // Mark as manually expanded if user expands it
      if (autoCollapseRef.current[item.id] && !newCollapsed) {
        autoCollapseRef.current[item.id].manuallyExpanded = true
      }
      return {
        ...prev,
        [item.id]: newCollapsed,
      }
    })
  }, [])

  const hasMoreItems = timelineItems.length > visibleCount
  const handleShowMore = useCallback(() => {
    setVisibleCount((prev) => prev + 6)
  }, [])

  const handleConversationSend = useCallback(async () => {
    console.log('🟣 handleConversationSend called (CONVERSATION MODE - not prompt response!)', {
      draft: draft.substring(0, 50),
      batchId,
      sessionId,
    })
    
    const trimmed = draft.trim()
    if (!trimmed) {
      addNotification('请输入内容后再发送', 'warning')
      return
    }
    if (!batchId) {
      addNotification('当前批次未初始化，无法发送消息', 'warning')
      return
    }

    setIsConversationSending(true)
    try {
      console.log('🟣 Sending via HTTP API (not WebSocket prompt response)')
      const response = await apiService.sendConversationMessage({
        batch_id: batchId,
        message: trimmed,
        session_id: sessionId ?? undefined,
      })
      console.log('🟣 Conversation message sent via API:', response)
      if (response.status === 'queued') {
        addNotification(response.queued_reason || '阶段提示等待完成，消息已排队', 'info')
      }
      setDraft('')
    } catch (error) {
      console.error('❌ Failed to send conversation message', error)
      addNotification('发送反馈消息失败，请稍后重试', 'error')
    } finally {
      setIsConversationSending(false)
    }
  }, [addNotification, batchId, draft, sessionId])

  const handleSendDraft = useCallback(() => {
    console.log('🔵 handleSendDraft called', {
      waitingForUser,
      promptId,
      promptSubmitted,
      draft: draft.substring(0, 50),
      batchId,
    })
    
    // CRITICAL: Use hasProceduralPrompt logic to determine mode
    // This ensures consistency between UI state and handler behavior
    const isPromptMode = waitingForUser && typeof promptId === 'string' && promptId.trim().length > 0 && !promptSubmitted
    console.log('🔵 isPromptMode:', isPromptMode, '(must match hasProceduralPrompt)')
    
    if (!isPromptMode) {
      console.log('🔵 Not in prompt mode, checking for conversation mode')
      if (!batchId) {
        addNotification('当前批次未初始化，无法发送消息', 'warning')
        return
      }
      void handleConversationSend()
      return
    }

    if (!promptId) {
      console.error('❌ No promptId available')
      addNotification('提交失败：缺少 prompt_id', 'error')
      return
    }

    const response = draft.trim()
    console.log('🔵 Attempting to send user input:', {
      promptId,
      response: response.substring(0, 50) || '(empty)',
      messageType: 'research:user_input',
    })
    
    // Send the message FIRST and check if it was sent successfully
    const messageSent = onSendMessage('research:user_input', {
      prompt_id: promptId,
      response,
    })
    
    console.log('🔵 Message send result:', messageSent ? '✅ SUCCESS' : '❌ FAILED')
    
    // Only proceed with UI updates if message was sent successfully
    if (messageSent) {
      console.log('✅ Message sent successfully, updating UI')
      // Trigger exit animation
      setIsPromptExiting(true)
      
      // Mark as submitted and clear draft after animation
      setTimeout(() => {
        setPromptSubmitted(true)
        setDraft('')
      }, 300)
    } else {
      console.error('❌ Message failed to send, keeping prompt visible')
      // Message failed to send, show error to user
      addNotification('消息发送失败，请检查连接后重试', 'error')
    }
  }, [
    addNotification,
    batchId,
    draft,
    handleConversationSend,
    onSendMessage,
    promptId,
    promptSubmitted,
    waitingForUser,
  ])

  const handleChoiceSelect = useCallback(
    (choice: string) => {
      console.log('🔵 handleChoiceSelect called', {
        choice,
        waitingForUser,
        promptId,
        promptSubmitted,
      })
      
      // CRITICAL: Use hasProceduralPrompt logic to determine mode
      const isPromptMode = waitingForUser && typeof promptId === 'string' && promptId.trim().length > 0 && !promptSubmitted
      console.log('🔵 isPromptMode:', isPromptMode, '(must match hasProceduralPrompt)')
      
      if (!isPromptMode) {
        addNotification('当前无需输入，AI 正在继续执行任务', 'info')
        return
      }

      if (!promptId) {
        console.error('❌ No promptId available')
        addNotification('提交失败：缺少 prompt_id', 'error')
        return
      }

      console.log('🔵 Attempting to send choice:', {
        promptId,
        choice,
        messageType: 'research:user_input',
      })
      
      // Send the message FIRST and check if it was sent successfully
      const messageSent = onSendMessage('research:user_input', {
        prompt_id: promptId,
        response: choice,
      })
      
      console.log('🔵 Message send result:', messageSent ? '✅ SUCCESS' : '❌ FAILED')
      
      // Only proceed with UI updates if message was sent successfully
      if (messageSent) {
        console.log('✅ Choice sent successfully, updating UI')
        // Trigger exit animation
        setIsPromptExiting(true)
        
        // Mark as submitted after animation
        setTimeout(() => {
          setPromptSubmitted(true)
        }, 300)
      } else {
        console.error('❌ Choice failed to send, keeping prompt visible')
        // Message failed to send, show error to user
        addNotification('消息发送失败，请检查连接后重试', 'error')
      }
    },
    [addNotification, onSendMessage, promptId, promptSubmitted, waitingForUser]
  )

  const handleStop = useCallback(() => {
    addNotification('停止功能即将上线，敬请期待', 'info')
  }, [addNotification])

  const handleRetry = useCallback(() => {
    addNotification('重试功能即将上线，敬请期待', 'info')
  }, [addNotification])

  const handleKeyDown: React.KeyboardEventHandler<HTMLTextAreaElement> = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      console.log('🔵 Enter key pressed (without Shift)')
      event.preventDefault()
      handleSendDraft()
    }
  }

  const handleCopyItem = useCallback(
    async (item: PhaseTimelineItem) => {
      try {
        await navigator.clipboard.writeText(item.message)
        addNotification(`已复制 ${item.title}`, 'success')
      } catch (error) {
        console.error('Failed to copy timeline item', error)
        addNotification('复制失败，请稍后再试', 'error')
      }
    },
    [addNotification]
  )

  const handleCopyRaw = useCallback(async () => {
    if (!combinedRaw) {
      addNotification('暂无原始流内容', 'warning')
      return
    }
    try {
      await navigator.clipboard.writeText(combinedRaw)
      addNotification('已复制原始流内容', 'success')
    } catch (error) {
      console.error('Failed to copy raw stream', error)
      addNotification('复制失败，请稍后再试', 'error')
    }
  }, [combinedRaw, addNotification])

  const latencyLabel = formatLatency(latestUpdateAt)

  return (
    <div className="flex flex-col rounded-2xl border border-neutral-200 bg-neutral-white shadow-[0_30px_80px_-40px_rgba(15,23,42,0.45)] h-full min-h-0">
      <header className="px-3 py-2 border-b border-neutral-200 space-y-2 flex-shrink-0">
        <div className="flex items-center justify-between text-xs font-medium text-neutral-700">
          <div className="flex items-center gap-2">
            <span className={`h-1.5 w-1.5 rounded-full ${statusIndicatorClass}`} aria-hidden="true" />
            {statusLabel}
            <span className="text-neutral-300">•</span>
            <span className="text-neutral-500">阶段 {phase ?? '—'}</span>
          </div>
          <div className="text-xs text-neutral-400">最近更新延迟 {latencyLabel}</div>
        </div>
        {currentAction && (
          <div className="rounded-lg border border-primary-200 bg-primary-50 px-2 py-1.5 text-xs text-primary-700">
            当前动作：{currentAction}
          </div>
        )}
        {summarizationProgress && summarizationProgress.totalItems > 0 && (
          <div className="rounded-lg border border-neutral-200 bg-neutral-50 px-2 py-1.5 text-xs text-neutral-700 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-medium text-neutral-600">
                摘要进度 · {summarizationProgress.stage || '进行中'}
              </span>
              <span className="text-neutral-400">
                {summarizationProgress.currentItem}/{summarizationProgress.totalItems}
              </span>
            </div>
            <div className="text-neutral-600">{summarizationProgress.message}</div>
            <div className="h-1 w-full rounded-full bg-neutral-200">
              <div
                className="h-full rounded-full bg-primary-500 transition-all duration-300 ease-out"
                style={{
                  width: `${Math.max(
                    0,
                    Math.min(100, Math.round(summarizationProgress.progress ?? 0))
                  )}%`,
                }}
              />
            </div>
          </div>
        )}
      </header>

      <div ref={scrollContainerRef} className="flex-1 min-h-0 overflow-y-auto px-3 py-2">
        <StreamTimeline
          items={timelineItems}
          collapsedState={collapsedState}
          onToggleCollapse={handleToggleCollapse}
          onCopy={handleCopyItem}
          activeStreamId={activeStreamId}
          visibleCount={visibleCount}
          onShowMore={handleShowMore}
          hasMore={hasMoreItems}
        />
      </div>

      <footer className="border-t border-neutral-200 px-3 py-2 space-y-2 flex-shrink-0">
        {hasProceduralPrompt && userInputRequired?.data?.prompt && (
          <div 
            className={`rounded-lg border-2 border-amber-400 bg-amber-50 px-2 py-1.5 space-y-1.5 transition-all duration-300 ${
              isPromptExiting ? 'opacity-0 scale-95 -translate-y-2' : 'opacity-100 scale-100 translate-y-0'
            }`}
          >
            <div className="flex items-start gap-2">
              <span className="text-amber-600 text-base">⚠️</span>
              <div className="flex-1">
                <div className="font-medium text-amber-900 text-xs mb-0.5">需要用户输入</div>
                <div className="text-amber-800 text-xs">{userInputRequired.data.prompt}</div>
              </div>
            </div>
            {choiceOptions.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {choiceOptions.map((choice) => (
                  <button
                    key={choice}
                    type="button"
                    onClick={() => handleChoiceSelect(choice)}
                    className="px-2 py-1 rounded-lg border border-amber-300 bg-amber-100 text-xs font-medium text-amber-900 transition hover:bg-amber-200"
                  >
                    {choice}
                  </button>
                ))}
              </div>
            )}
            <div className="text-xs text-amber-700 pt-0.5">
              💡 留空并按 Enter 将使用默认设置
            </div>
          </div>
        )}

        <div className={`rounded-xl border shadow-inner px-2 py-1.5 transition-colors duration-300 ${
          hasProceduralPrompt 
            ? 'border-amber-300 bg-amber-50' 
            : 'border-neutral-200 bg-neutral-white'
        } focus-within:border-primary-300 focus-within:ring-2 focus-within:ring-primary-100`}>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={
              hasProceduralPrompt
                ? userInputRequired?.data?.prompt || '请输入阶段提示的回复...'
                : '向 AI 发送消息以获取实时反馈...'
            }
            onKeyDown={handleKeyDown}
            rows={hasProceduralPrompt ? 3 : 2}
            className="w-full resize-none border-0 bg-transparent text-xs text-neutral-700 placeholder:text-neutral-300 focus:outline-none focus:ring-0"
            disabled={!hasProceduralPrompt && (isConversationSending || !batchId)}
          />
          <div className="flex items-center justify-between pt-1.5 text-xs text-neutral-400">
            <span>{hasProceduralPrompt ? '⏰ 回复阶段提示或留空使用默认' : 'Shift + Enter 换行'}</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleStop}
                className="text-neutral-400 hover:text-neutral-600 transition disabled:opacity-40"
                disabled={!isStreaming}
              >
                停止
              </button>
              <span className="text-neutral-200">|</span>
              <button
                type="button"
                onClick={handleRetry}
                className="text-neutral-400 hover:text-neutral-600 transition"
              >
                重试
              </button>
              <Button
                size="sm"
                variant="primary"
                onClick={() => {
                  console.log('🔵 Submit button clicked', {
                    hasProceduralPrompt,
                    promptId,
                    isDisabled: hasProceduralPrompt ? !promptId : isConversationSending || draft.trim().length === 0 || !batchId,
                  })
                  handleSendDraft()
                }}
                disabled={
                  hasProceduralPrompt
                    ? !promptId
                    : isConversationSending || draft.trim().length === 0 || !batchId
                }
              >
                {hasProceduralPrompt ? '提交' : isConversationSending ? '发送中...' : '发送'}
              </Button>
            </div>
          </div>
        </div>
        {!hasProceduralPrompt && !batchId && (
          <div className="text-xs text-warning-500 mt-1">请先启动研究工作流，再发送对话消息。</div>
        )}
      </footer>
    </div>
  )
}

export default PhaseInteractionPanel
