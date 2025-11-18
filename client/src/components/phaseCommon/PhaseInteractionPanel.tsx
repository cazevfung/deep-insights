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
  const [visibleCount, setVisibleCount] = useState(50) // Not used in summary view, but kept for compatibility
  const [promptSubmitted, setPromptSubmitted] = useState(false)
  const [isPromptExiting, setIsPromptExiting] = useState(false)
  const [lastProcessedPromptId, setLastProcessedPromptId] = useState<string | null>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const [dismissedItems, setDismissedItems] = useState<Set<string>>(new Set())
  const [isPinnedToBottom, setIsPinnedToBottom] = useState(true)
  const [pendingItemCount, setPendingItemCount] = useState(0)
  const previousVisibleLengthRef = useRef(0)
  const lastScrollTopRef = useRef(0)
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

  // Helper: Determine if item is critical (for auto-scroll)
  const isCriticalItem = useCallback((item: PhaseTimelineItem): boolean => {
    // Reasoning items are always critical - they should always be visible
    if (item.type === 'reasoning') return true
    // User prompts, errors, and phase transitions are critical
    if (item.status === 'error') return true
    if (item.statusVariant === 'error') return true
    // Check if it's a user prompt (waiting for user input)
    if (waitingForUser && item.metadata?.prompt_id) return true
    return false
  }, [waitingForUser])

  // Filter out dismissed items
  const visibleItems = useMemo(() => {
    return timelineItems.filter(item => !dismissedItems.has(item.id))
  }, [timelineItems, dismissedItems])

  // Summary view doesn't need visible count management

  const lastVisibleItem = visibleItems[visibleItems.length - 1]

  // Chat-like smart auto-scroll with pin logic
  useEffect(() => {
    const container = scrollContainerRef.current
    if (!container) return

    const newItemsCount = Math.max(0, visibleItems.length - previousVisibleLengthRef.current)
    const pendingIncrement = Math.max(newItemsCount, 1)
    const isCritical = lastVisibleItem && isCriticalItem(lastVisibleItem)

    if (isCritical) {
      if (isPinnedToBottom) {
        container.scrollTo({ top: container.scrollHeight })
        setPendingItemCount(0)
      } else {
        setPendingItemCount((prev) => prev + pendingIncrement)
      }
    } else if (isPinnedToBottom) {
      container.scrollTo({ top: container.scrollHeight })
      if (newItemsCount > 0) {
        setPendingItemCount(0)
      }
    } else if (newItemsCount > 0) {
      setPendingItemCount((prev) => prev + newItemsCount)
    }

    previousVisibleLengthRef.current = visibleItems.length
  }, [visibleItems.length, lastVisibleItem?.id, isCriticalItem, isPinnedToBottom, lastVisibleItem])

  // Track scroll position with hysteresis for pin state
  useEffect(() => {
    const container = scrollContainerRef.current
    if (!container) return
    lastScrollTopRef.current = container.scrollTop

    const RELEASE_THRESHOLD = 60
    const REPIN_THRESHOLD = 40

    const handleScroll = () => {
      const currentTop = container.scrollTop
      const previousTop = lastScrollTopRef.current
      const scrollingUp = currentTop < previousTop
      lastScrollTopRef.current = currentTop

      if (scrollingUp) {
        setIsPinnedToBottom(false)
        return
      }

      const distanceFromBottom = container.scrollHeight - currentTop - container.clientHeight

      if (distanceFromBottom <= REPIN_THRESHOLD) {
        setIsPinnedToBottom((prev) => {
          if (!prev) {
            setPendingItemCount(0)
          }
          return true
        })
      } else if (distanceFromBottom > RELEASE_THRESHOLD) {
        setIsPinnedToBottom((prev) => (prev ? false : prev))
      }
    }

    container.addEventListener('scroll', handleScroll, { passive: true })
    return () => container.removeEventListener('scroll', handleScroll)
  }, [])

  const handleDismissItem = useCallback((item: PhaseTimelineItem) => {
    setDismissedItems((prev) => {
      const next = new Set(prev)
      next.add(item.id)
      return next
    })
  }, [])

  // Auto-dismiss errors after 5 seconds (only if not manually dismissed)
  useEffect(() => {
    const errorItems = visibleItems.filter(
      item => (item.status === 'error' || item.statusVariant === 'error') && !dismissedItems.has(item.id)
    )

    const timers = errorItems.map(item => {
      return setTimeout(() => {
        setDismissedItems((prev) => {
          if (!prev.has(item.id)) {
            const next = new Set(prev)
            next.add(item.id)
            return next
          }
          return prev
        })
      }, 5000)
    })

    return () => {
      timers.forEach(timer => clearTimeout(timer))
    }
  }, [visibleItems, dismissedItems])

  const handleJumpToBottom = useCallback(() => {
    if (!scrollContainerRef.current) return
    scrollContainerRef.current.scrollTo({
      top: scrollContainerRef.current.scrollHeight,
      behavior: 'smooth',
    })
    setIsPinnedToBottom(true)
    setPendingItemCount(0)
  }, [])

  const hasMoreItems = visibleItems.length > visibleCount
  const handleShowMore = useCallback(() => {
    // Load more messages incrementally
    setVisibleCount((prev) => Math.min(prev + 10, visibleItems.length))
  }, [visibleItems.length])

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
  const currentActionSingleLine = currentAction?.split('\n')[0] ?? ''

  return (
    <div className="flex flex-col rounded-2xl border border-neutral-200 bg-neutral-white shadow-[0_30px_80px_-40px_rgba(15,23,42,0.45)] h-full min-h-0">
      <header className="px-3 py-3 border-b border-neutral-200 space-y-2 flex-shrink-0">
        <div className="flex items-center justify-between text-[10px] font-medium text-neutral-700">
          <div className="flex items-center gap-2">
            <span className={`h-1.5 w-1.5 rounded-full ${statusIndicatorClass}`} aria-hidden="true" />
            {statusLabel}
            <span className="text-neutral-300">•</span>
            <span className="text-neutral-500">阶段 {phase ?? '—'}</span>
          </div>
          <div className="text-[10px] text-neutral-400">最近更新延迟 {latencyLabel}</div>
        </div>
        {currentActionSingleLine && (
          <div className="rounded-lg border border-primary-200 bg-primary-50 px-3 py-2 text-[10px] text-primary-700 whitespace-nowrap overflow-hidden text-ellipsis">
            当前动作：{currentActionSingleLine}
          </div>
        )}
      </header>

      <div ref={scrollContainerRef} className="flex-1 min-h-0 overflow-y-auto px-3 py-3 relative">
        {/* New content indicator */}
        {pendingItemCount > 0 && (
          <button
            type="button"
            onClick={handleJumpToBottom}
            className="sticky top-2 left-1/2 transform -translate-x-1/2 z-10 rounded-full bg-primary-500 text-white px-3 py-1.5 text-[10px] font-medium shadow-lg hover:bg-primary-600 transition-colors mb-2"
            style={{ backgroundColor: '#FEC74A' }}
          >
            ↓ 新消息 · {pendingItemCount}
          </button>
        )}
        
        <StreamTimeline
          items={visibleItems}
          visibleCount={visibleCount}
          onShowMore={handleShowMore}
          hasMore={hasMoreItems}
          onDismiss={handleDismissItem}
        />
        
        {/* Jump to bottom button (floating) */}
        {pendingItemCount > 0 && (
          <button
            type="button"
            onClick={handleJumpToBottom}
            className="fixed bottom-24 right-8 rounded-full bg-primary-500 text-white p-3 shadow-lg hover:bg-primary-600 transition-colors z-20"
            style={{ backgroundColor: '#FEC74A' }}
            aria-label="跳到底部"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </button>
        )}
      </div>

      <footer className="border-t border-neutral-200 px-3 py-3 space-y-2 flex-shrink-0">
        {hasProceduralPrompt && userInputRequired?.data?.prompt && (
          <div 
            className={`rounded-lg border-2 border-amber-400 bg-amber-50 px-3 py-2 space-y-1.5 transition-all duration-300 ${
              isPromptExiting ? 'opacity-0 scale-95 -translate-y-2' : 'opacity-100 scale-100 translate-y-0'
            }`}
          >
            <div className="flex items-start gap-2">
              <span className="text-amber-600 text-base">⚠️</span>
              <div className="flex-1">
                <div className="font-medium text-amber-900 text-[10px] mb-0.5">需要用户输入</div>
                <div className="text-amber-800 text-[10px]">{userInputRequired.data.prompt}</div>
              </div>
            </div>
            {choiceOptions.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {choiceOptions.map((choice) => (
                  <button
                    key={choice}
                    type="button"
                    onClick={() => handleChoiceSelect(choice)}
                    className="px-3 py-1.5 rounded-lg border border-amber-300 bg-amber-100 text-[10px] font-medium text-amber-900 transition hover:bg-amber-200"
                  >
                    {choice}
                  </button>
                ))}
              </div>
            )}
            <div className="text-[10px] text-amber-700 pt-0.5">
              💡 留空并按 Enter 将使用默认设置
            </div>
          </div>
        )}

        <div className={`rounded-xl border shadow-inner px-3 py-2 transition-colors duration-300 ${
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
            className="w-full resize-none border-0 bg-transparent text-[10px] text-neutral-700 placeholder:text-neutral-300 focus:outline-none focus:ring-0"
            disabled={!hasProceduralPrompt && (isConversationSending || !batchId)}
          />
          <div className="flex items-center justify-between pt-1.5 text-[10px] text-neutral-400">
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
          <div className="text-[10px] text-warning-500 mt-1">请先启动研究工作流，再发送对话消息。</div>
        )}
      </footer>
    </div>
  )
}

export default PhaseInteractionPanel
