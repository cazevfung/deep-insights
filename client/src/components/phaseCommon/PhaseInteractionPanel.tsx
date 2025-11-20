import React, { useCallback, useEffect, useMemo, useState, useRef } from 'react'
import { usePhaseInteraction, PhaseTimelineItem } from '../../hooks/usePhaseInteraction'
import { useWorkflowStore, ConversationContextRequest } from '../../stores/workflowStore'
import { useUiStore } from '../../stores/uiStore'
import Button from '../common/Button'
import StreamTimeline from './StreamTimeline'
import SuggestedQuestions from './SuggestedQuestions'
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
  const panelContainerRef = useRef<HTMLDivElement>(null)
  const [dismissedItems, setDismissedItems] = useState<Set<string>>(new Set())
  const [pinnedItems, setPinnedItems] = useState<Set<string>>(new Set())
  const [isPinnedToBottom, setIsPinnedToBottom] = useState(true)
  const [pendingItemCount, setPendingItemCount] = useState(0)
  const previousVisibleLengthRef = useRef(0)
  const lastScrollTopRef = useRef(0)
  const isProgrammaticScrollRef = useRef(false)
  const scrollTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const isSendingRef = useRef(false) // Synchronous guard to prevent duplicate sends
  const recentMessageHashesRef = useRef<Set<string>>(new Set()) // Track recent message hashes to prevent duplicates
  const batchId = useWorkflowStore((state) => state.batchId)
  const sessionId = useWorkflowStore((state) => state.sessionId)
  const contextRequests = useWorkflowStore((state) => state.conversationContextRequests)
  const conversationMessages = useWorkflowStore((state) => state.researchAgentStatus.conversationMessages)
  const upsertConversationMessage = useWorkflowStore((state) => state.upsertConversationMessage)
  const removeConversationMessage = useWorkflowStore((state) => state.removeConversationMessage)

  const promptId = userInputRequired?.prompt_id
  const hasProceduralPrompt =
    waitingForUser && typeof promptId === 'string' && promptId.trim().length > 0 && !promptSubmitted
  const pendingContextRequests = useMemo(
    () => contextRequests.filter((request) => request.status === 'pending'),
    [contextRequests]
  )
  const [contextDrafts, setContextDrafts] = useState<Record<string, Record<string, string>>>({})
  const [isSubmittingContextId, setIsSubmittingContextId] = useState<string | null>(null)
  const [isPanelAtTop, setIsPanelAtTop] = useState(true)
  useEffect(() => {
    const updatePanelState = () => {
      if (!panelContainerRef.current) return
      const rect = panelContainerRef.current.getBoundingClientRect()
      const atTop = rect.top <= 24
      setIsPanelAtTop(atTop)
    }

    updatePanelState()
    const scrollHost = panelContainerRef.current?.closest('.overflow-y-auto')
    if (scrollHost) {
      scrollHost.addEventListener('scroll', updatePanelState, { passive: true })
      return () => {
        scrollHost.removeEventListener('scroll', updatePanelState)
      }
    }
  }, [])
  
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
        // Mark as programmatic scroll to prevent scroll handler from interfering
        isProgrammaticScrollRef.current = true
        container.scrollTo({ top: container.scrollHeight })
        // Clear flag after scroll completes
        if (scrollTimeoutRef.current) {
          clearTimeout(scrollTimeoutRef.current)
        }
        scrollTimeoutRef.current = setTimeout(() => {
          isProgrammaticScrollRef.current = false
        }, 100)
        setPendingItemCount(0)
      } else {
        setPendingItemCount((prev) => prev + pendingIncrement)
      }
    } else if (isPinnedToBottom) {
      // Mark as programmatic scroll to prevent scroll handler from interfering
      isProgrammaticScrollRef.current = true
      container.scrollTo({ top: container.scrollHeight })
      // Clear flag after scroll completes
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current)
      }
      scrollTimeoutRef.current = setTimeout(() => {
        isProgrammaticScrollRef.current = false
      }, 100)
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
      // Ignore programmatic scrolls (from auto-scroll)
      if (isProgrammaticScrollRef.current) {
        // Update lastScrollTopRef but don't change pin state
        lastScrollTopRef.current = container.scrollTop
        return
      }

      const currentTop = container.scrollTop
      const previousTop = lastScrollTopRef.current
      const scrollingUp = currentTop < previousTop
      lastScrollTopRef.current = currentTop

      // Use requestAnimationFrame to ensure accurate scroll position after content changes
      requestAnimationFrame(() => {
        // Re-read scroll position in case it changed
        const latestTop = container.scrollTop
        const distanceFromBottom = container.scrollHeight - latestTop - container.clientHeight

        if (scrollingUp) {
          // User scrolled up - definitely unpin
          setIsPinnedToBottom(false)
          return
        }

        // User scrolled down - check if near bottom
        if (distanceFromBottom <= REPIN_THRESHOLD) {
          setIsPinnedToBottom((prev) => {
            if (!prev) {
              setPendingItemCount(0)
            }
            return true
          })
        } else if (distanceFromBottom > RELEASE_THRESHOLD) {
          // Only unpin if user is significantly away from bottom
          setIsPinnedToBottom((prev) => (prev ? false : prev))
        }
      })
    }

    container.addEventListener('scroll', handleScroll, { passive: true })
    return () => {
      container.removeEventListener('scroll', handleScroll)
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current)
      }
    }
  }, [])

  const handleDismissItem = useCallback((item: PhaseTimelineItem) => {
    setDismissedItems((prev) => {
      const next = new Set(prev)
      next.add(item.id)
      return next
    })
  }, [])

  const handlePinItem = useCallback((item: PhaseTimelineItem) => {
    setPinnedItems((prev) => {
      const next = new Set(prev)
      if (next.has(item.id)) {
        next.delete(item.id)
        addNotification('已取消固定消息', 'info')
      } else {
        next.add(item.id)
        addNotification('已固定消息', 'success')
      }
      return next
    })
  }, [addNotification])

  const handleScrollToPinned = useCallback((itemId: string) => {
    if (!scrollContainerRef.current) return
    
    // Find the element with the item ID
    const itemElement = scrollContainerRef.current.querySelector(`[data-item-id="${itemId}"]`)
    if (itemElement) {
      // Temporarily unpin from bottom to allow scrolling
      setIsPinnedToBottom(false)
      // Mark as programmatic scroll
      isProgrammaticScrollRef.current = true
      itemElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
      // Clear flag after scroll completes
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current)
      }
      scrollTimeoutRef.current = setTimeout(() => {
        isProgrammaticScrollRef.current = false
      }, 500)
    } else {
      addNotification('无法找到固定消息', 'warning')
    }
  }, [addNotification])

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
    // Mark as programmatic scroll
    isProgrammaticScrollRef.current = true
    scrollContainerRef.current.scrollTo({
      top: scrollContainerRef.current.scrollHeight,
      behavior: 'smooth',
    })
    // Clear flag after scroll completes
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current)
    }
    scrollTimeoutRef.current = setTimeout(() => {
      isProgrammaticScrollRef.current = false
    }, 500) // Longer timeout for smooth scroll
    setIsPinnedToBottom(true)
    setPendingItemCount(0)
  }, [])

  const hasMoreItems = visibleItems.length > visibleCount
  const handleShowMore = useCallback(() => {
    // Load more messages incrementally
    setVisibleCount((prev) => Math.min(prev + 10, visibleItems.length))
  }, [visibleItems.length])

  const handleConversationSend = useCallback(async () => {
    // Synchronous ref-based guard - prevents duplicate sends even if state hasn't updated yet
    if (isSendingRef.current) {
      console.warn('⚠️ Conversation send attempted while previous send still in progress (ref guard)')
      return
    }
    if (isConversationSending) {
      console.warn('⚠️ Conversation send attempted while previous send still in progress (state guard)')
      return
    }
    
    const trimmed = draft.trim()
    if (!trimmed) {
      addNotification('请输入内容后再发送', 'warning')
      return
    }
    if (!batchId) {
      addNotification('当前批次未初始化，无法发送消息', 'warning')
      return
    }
    
    // CRITICAL: Check if we've sent this exact message recently (within last 30 seconds)
    const messageHash = `${batchId}:${trimmed}`
    if (recentMessageHashesRef.current.has(messageHash)) {
      console.error('⛔ DUPLICATE MESSAGE BLOCKED:', trimmed.substring(0, 50))
      addNotification('该消息最近已发送，请勿重复发送', 'warning')
      return
    }
    
    // Set guard immediately (synchronous)
    isSendingRef.current = true
    recentMessageHashesRef.current.add(messageHash)
    
    // Clear message hash after 30 seconds
    setTimeout(() => {
      recentMessageHashesRef.current.delete(messageHash)
    }, 30000)
    
    console.log('🟣 handleConversationSend called (CONVERSATION MODE - not prompt response!)', {
      draft: trimmed.substring(0, 50),
      batchId,
      sessionId,
    })

    const tempId = `temp-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    const timestamp = new Date().toISOString()

    upsertConversationMessage({
      id: tempId,
      role: 'user',
      content: trimmed,
      status: 'in_progress',
      timestamp,
      metadata: { pending: true },
    })

    setIsConversationSending(true)
    setDraft('')
    try {
      console.log('🟣 Sending via HTTP API (not WebSocket prompt response)')
      const response = await apiService.sendConversationMessage({
        batch_id: batchId,
        message: trimmed,
        session_id: sessionId ?? undefined,
      })
      console.log('🟣 Conversation message sent via API:', response)
      removeConversationMessage(tempId)
      const nextStatus =
        response.status === 'ok'
          ? 'completed'
          : response.status === 'queued'
          ? 'queued'
          : 'in_progress'
      upsertConversationMessage({
        id: response.user_message_id ?? tempId,
        role: 'user',
        content: trimmed,
        status: nextStatus,
        timestamp,
        metadata: response.metadata ?? {},
      })
      if (response.status === 'queued') {
        addNotification(response.queued_reason || '阶段提示等待完成，消息已排队', 'info')
      } else if (response.status === 'context_required') {
        addNotification('AI 需要更多上下文，请在下方补充信息。', 'info')
      }
    } catch (error) {
      console.error('❌ Failed to send conversation message', error)
      setDraft(trimmed)
      upsertConversationMessage({
        id: tempId,
        role: 'user',
        content: trimmed,
        status: 'error',
        timestamp,
        metadata: {
          pending: false,
          error: '发送失败，请稍后重试',
        },
      })
      addNotification('发送反馈消息失败，请稍后重试', 'error')
    } finally {
      setIsConversationSending(false)
      isSendingRef.current = false // Reset synchronous guard
    }
  }, [
    addNotification,
    batchId,
    draft,
    isConversationSending,
    sessionId,
    upsertConversationMessage,
    removeConversationMessage,
  ])

  const handleContextFieldChange = useCallback(
    (requestId: string, slotKey: string, value: string) => {
      setContextDrafts((prev) => ({
        ...prev,
        [requestId]: {
          ...(prev[requestId] || {}),
          [slotKey]: value,
        },
      }))
    },
    []
  )

  const handleContextSubmit = useCallback(
    async (request: ConversationContextRequest) => {
      if (!batchId) {
        addNotification('当前批次未初始化，无法提交上下文', 'warning')
        return
      }
      const drafts = contextDrafts[request.id] || {}
      const items = (request.requirements || []).map((req) => ({
        slot_key: req.key,
        label: req.label,
        content: (drafts[req.key] || '').trim(),
      })).filter((item) => item.content.length > 0)

      if (!items.length) {
        addNotification('请至少填写一条上下文内容', 'warning')
        return
      }

      setIsSubmittingContextId(request.id)
      try {
        await apiService.supplyConversationContext({
          batch_id: batchId,
          request_id: request.id,
          items,
        })
        addNotification('上下文已提交，AI 将继续处理该消息。', 'success')
        setContextDrafts((prev) => {
          const next = { ...prev }
          delete next[request.id]
          return next
        })
      } catch (error) {
        console.error('❌ Failed to supply conversation context', error)
        addNotification('提交上下文失败，请稍后再试', 'error')
      } finally {
        setIsSubmittingContextId(null)
      }
    },
    [addNotification, batchId, contextDrafts]
  )

  const handleSendDraft = useCallback(() => {
    // Early guard check - prevent duplicate sends
    if (isSendingRef.current || isConversationSending) {
      console.warn('⚠️ handleSendDraft: Send already in progress, ignoring duplicate call')
      return
    }
    
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
    isConversationSending,
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
    <div
      ref={panelContainerRef}
      className={`flex flex-col rounded-2xl border bg-neutral-white h-full min-h-0 transition-all duration-200 ${
        isPanelAtTop ? 'border-transparent' : 'border-neutral-200'
      }`}
    >
      <header className="px-3 py-3 border-b border-neutral-200 space-y-2 flex-shrink-0">
        <div className="flex items-center justify-between text-[13px] font-medium text-neutral-700">
          <div className="flex items-center gap-2">
            <span className={`h-1.5 w-1.5 rounded-full ${statusIndicatorClass}`} aria-hidden="true" />
            {statusLabel}
            <span className="text-neutral-300">•</span>
            <span className="text-neutral-500">阶段 {phase ?? '—'}</span>
          </div>
          <div className="text-[13px] text-neutral-400">最近更新延迟 {latencyLabel}</div>
        </div>
        {currentActionSingleLine && (
          <div className="rounded-lg border border-primary-200 bg-primary-50 px-3 py-2 text-[13px] text-primary-700 whitespace-nowrap overflow-hidden text-ellipsis">
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
            className="sticky top-2 left-1/2 transform -translate-x-1/2 z-10 rounded-full bg-primary-500 text-white px-3 py-1.5 text-[13px] font-medium shadow-lg hover:bg-primary-600 transition-colors mb-2"
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
          onPin={handlePinItem}
          pinnedItems={pinnedItems}
          onScrollToPinned={handleScrollToPinned}
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
                <div className="font-medium text-amber-900 text-[13px] mb-0.5">需要用户输入</div>
                <div className="text-amber-800 text-[13px]">{userInputRequired.data.prompt}</div>
              </div>
            </div>
            {choiceOptions.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {choiceOptions.map((choice) => (
                  <button
                    key={choice}
                    type="button"
                    onClick={() => handleChoiceSelect(choice)}
                    className="px-3 py-1.5 rounded-lg border border-amber-300 bg-amber-100 text-[13px] font-medium text-amber-900 transition hover:bg-amber-200"
                  >
                    {choice}
                  </button>
                ))}
              </div>
            )}
            <div className="text-[13px] text-amber-700 pt-0.5">
              💡 留空并按 Enter 将使用默认设置
            </div>
          </div>
        )}

        {pendingContextRequests.length > 0 && (
          <div className="space-y-3 mb-3">
            {pendingContextRequests.map((request) => (
              <div
                key={request.id}
                className="rounded-xl border border-indigo-200 bg-indigo-50/70 px-3 py-2 text-[13px] text-indigo-900"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-indigo-800">需要补充上下文</span>
                  <span className="text-indigo-500">
                    {new Date(request.created_at).toLocaleTimeString()}
                  </span>
                </div>
                <div className="mt-1 text-indigo-600">
                  {request.reason || '提供 Phase 3 摘要或要点后，AI 将继续回答。'}
                </div>
                <div className="mt-2 space-y-2">
                  {request.requirements?.map((requirement) => (
                    <div key={`${request.id}-${requirement.key}`}>
                      <div className="flex items-center justify-between text-indigo-700 font-medium">
                        <span>{requirement.label}</span>
                        {!requirement.required && <span className="text-indigo-400">可选</span>}
                      </div>
                      <div className="text-indigo-500 mb-1">{requirement.description}</div>
                      <textarea
                        className="w-full rounded-lg border border-indigo-200 bg-white/80 px-2 py-1 text-[13px] text-indigo-900 focus:outline-none focus:ring-2 focus:ring-indigo-200"
                        rows={3}
                        value={contextDrafts[request.id]?.[requirement.key] ?? ''}
                        onChange={(event) =>
                          handleContextFieldChange(request.id, requirement.key, event.target.value)
                        }
                      />
                    </div>
                  ))}
                </div>
                {request.attachments?.length ? (
                  <div className="mt-2 text-indigo-600">
                    已提供的附件：
                    <ul className="list-disc pl-4">
                      {request.attachments.map((attachment) => (
                        <li key={attachment.id} className="mt-0.5">
                          <span className="font-medium">{attachment.label}</span>
                          {attachment.content_preview && (
                            <div className="text-indigo-500 whitespace-pre-line">
                              {attachment.content_preview}
                            </div>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                <div className="mt-3 flex justify-end">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => handleContextSubmit(request)}
                    disabled={isSubmittingContextId === request.id || !batchId}
                  >
                    {isSubmittingContextId === request.id ? '提交中...' : '提交上下文'}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {!hasProceduralPrompt && (
          <SuggestedQuestions
            batchId={batchId}
            sessionId={sessionId}
            conversationMessages={conversationMessages}
            onQuestionClick={async (question) => {
              // Auto-send: directly send the question without setting draft
              if (isSendingRef.current || isConversationSending) {
                console.log('⏸️  Skipping duplicate suggested question click')
                return
              }
              if (!batchId) {
                addNotification('当前批次未初始化，无法发送消息', 'warning')
                return
              }

              const trimmed = question.trim()
              if (!trimmed) {
                return
              }

              // CRITICAL: Check if we've sent this exact message recently (within last 30 seconds)
              const messageHash = `${batchId}:${trimmed}`
              if (recentMessageHashesRef.current.has(messageHash)) {
                console.error('⛔ DUPLICATE SUGGESTED QUESTION BLOCKED:', trimmed.substring(0, 50))
                addNotification('该问题最近已发送，请勿重复发送', 'warning')
                return
              }

              console.log('🚀 Sending suggested question:', trimmed)
              isSendingRef.current = true
              recentMessageHashesRef.current.add(messageHash)
              setIsConversationSending(true)

              // Clear message hash after 30 seconds
              setTimeout(() => {
                recentMessageHashesRef.current.delete(messageHash)
              }, 30000)

              const tempId = `temp-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
              const timestamp = new Date().toISOString()

              upsertConversationMessage({
                id: tempId,
                role: 'user',
                content: trimmed,
                status: 'in_progress',
                timestamp,
                metadata: { pending: true },
              })

              try {
                const response = await apiService.sendConversationMessage({
                  batch_id: batchId,
                  message: trimmed,
                  session_id: sessionId ?? undefined,
                })
                removeConversationMessage(tempId)
                const nextStatus =
                  response.status === 'ok'
                    ? 'completed'
                    : response.status === 'queued'
                    ? 'queued'
                    : 'in_progress'
                upsertConversationMessage({
                  id: response.user_message_id ?? tempId,
                  role: 'user',
                  content: trimmed,
                  status: nextStatus,
                  timestamp,
                  metadata: response.metadata ?? {},
                })
                if (response.status === 'queued') {
                  addNotification(response.queued_reason || '阶段提示等待完成，消息已排队', 'info')
                } else if (response.status === 'context_required') {
                  addNotification('AI 需要更多上下文，请在下方补充信息。', 'info')
                }
              } catch (error) {
                console.error('❌ Failed to send conversation message', error)
                upsertConversationMessage({
                  id: tempId,
                  role: 'user',
                  content: trimmed,
                  status: 'error',
                  timestamp,
                  metadata: {
                    pending: false,
                    error: '发送失败，请稍后重试',
                  },
                })
                addNotification('发送反馈消息失败，请稍后重试', 'error')
              } finally {
                setIsConversationSending(false)
                isSendingRef.current = false
              }
            }}
            disabled={isConversationSending || !batchId || isStreaming}
          />
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
            className="w-full resize-none border-0 bg-transparent text-[13px] text-neutral-700 placeholder:text-neutral-300 focus:outline-none focus:ring-0"
            disabled={!hasProceduralPrompt && (isConversationSending || !batchId)}
          />
          <div className="flex items-center justify-between pt-1.5 text-[13px] text-neutral-400">
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
          <div className="text-[13px] text-warning-500 mt-1">请先启动研究工作流，再发送对话消息。</div>
        )}
      </footer>
    </div>
  )
}

export default PhaseInteractionPanel
