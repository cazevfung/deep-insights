import React, { useState, useEffect, useMemo } from 'react'
import Card from '../components/common/Card'
import Button from '../components/common/Button'
import Textarea from '../components/common/Textarea'
import { useWorkflowStore, LiveGoal, LivePlanStep } from '../stores/workflowStore'
import { useWebSocket } from '../hooks/useWebSocket'
import StreamDisplay from '../components/streaming/StreamDisplay'
import StreamStructuredView from '../components/streaming/StreamStructuredView'
import { useStreamState } from '../hooks/useStreamState'
import ResearchGoalList from '../components/research/ResearchGoalList'

const classNames = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(' ')

const ResearchAgentPage: React.FC = () => {
  const researchAgentStatus = useWorkflowStore((state) => state.researchAgentStatus)
  const batchId = useWorkflowStore((state) => state.batchId)
  const setActiveStream = useWorkflowStore((state) => state.setActiveStream)
  const pinStream = useWorkflowStore((state) => state.pinStream)
  const unpinStream = useWorkflowStore((state) => state.unpinStream)
  const { sendMessage } = useWebSocket(batchId || '')
  const [userInput, setUserInput] = useState('')
  const [currentPlanIndex, setCurrentPlanIndex] = useState(0)
  const streamState = useStreamState({ inactivityTimeout: 4000 })
  const activeStreamBuffer = streamState.streamId ? researchAgentStatus.streams.buffers[streamState.streamId] : undefined

  const streamMetadata = useMemo(() => {
    const base: Record<string, any> = streamState.metadata ? { ...streamState.metadata } : {}
    if (streamState.startedAt) {
      base.startedAt = streamState.startedAt
    }
    if (streamState.lastTokenAt) {
      base.lastTokenAt = streamState.lastTokenAt
    }
    if (streamState.endedAt && !streamState.isStreaming) {
      base.endedAt = streamState.endedAt
    }
    if (activeStreamBuffer?.tokenCount) {
      base.tokens = activeStreamBuffer.tokenCount
    }
    if (activeStreamBuffer?.status) {
      base.status = activeStreamBuffer.status
    }
    return Object.keys(base).length > 0 ? base : null
  }, [streamState.metadata, streamState.startedAt, streamState.lastTokenAt, streamState.endedAt, streamState.isStreaming, activeStreamBuffer?.tokenCount, activeStreamBuffer?.status])

  const goalItems = useMemo(() => {
    const orderedIds = researchAgentStatus.goalOrder
    if (orderedIds.length > 0) {
      const liveGoals = orderedIds
        .map((id) => researchAgentStatus.liveGoals[id])
        .filter((goal): goal is NonNullable<typeof goal> => Boolean(goal))
      if (liveGoals.length > 0) {
        return liveGoals
      }
    }

    if (researchAgentStatus.goals && researchAgentStatus.goals.length > 0) {
      return researchAgentStatus.goals.map((goal, index) => ({
        id: goal.id ?? index + 1,
        goal_text: goal.goal_text,
        uses: goal.uses,
        status: 'ready' as LiveGoal['status'],
      }))
    }

    return []
  }, [researchAgentStatus.goalOrder, researchAgentStatus.liveGoals, researchAgentStatus.goals])

  const displayGoals = useMemo(() => {
    if (goalItems.length > 0) {
      return goalItems
    }

    const phaseKey = streamState.phase || activeStreamBuffer?.phase || activeStreamBuffer?.metadata?.phase_key
    if (streamState.isStreaming && phaseKey && phaseKey.toLowerCase().includes('phase1')) {
      return Array.from({ length: 3 }, (_, idx) => ({
        id: idx + 1,
        goal_text: '',
        status: 'streaming' as LiveGoal['status'],
      } as LiveGoal))
    }

    return []
  }, [goalItems, streamState.isStreaming, streamState.phase, activeStreamBuffer?.phase, activeStreamBuffer?.metadata?.phase_key])

  const planEntries = useMemo(() => {
    const orderedIds = researchAgentStatus.planOrder
    if (orderedIds.length > 0) {
      const liveSteps = orderedIds
        .map((id) => researchAgentStatus.livePlanSteps[id])
        .filter((step): step is NonNullable<typeof step> => Boolean(step))
      if (liveSteps.length > 0) {
        return liveSteps
      }
    }

    if (researchAgentStatus.plan && researchAgentStatus.plan.length > 0) {
      return researchAgentStatus.plan.map((step) => ({
        step_id: step.step_id,
        goal: step.goal,
        required_data: step.required_data,
        chunk_strategy: step.chunk_strategy,
        notes: step.notes,
        status: 'ready' as LivePlanStep['status'],
      }))
    }

    return []
  }, [researchAgentStatus.planOrder, researchAgentStatus.livePlanSteps, researchAgentStatus.plan])

  const displayPlanEntries = useMemo(() => {
    if (planEntries.length > 0) {
      return planEntries
    }

    const phaseKey = streamState.phase || activeStreamBuffer?.phase || activeStreamBuffer?.metadata?.phase_key
    if (streamState.isStreaming && phaseKey && phaseKey.toLowerCase().includes('phase2')) {
      return Array.from({ length: 3 }, (_, idx) => ({
        step_id: idx + 1,
        goal: '',
        status: 'streaming' as LivePlanStep['status'],
      } as LivePlanStep))
    }

    return []
  }, [planEntries, streamState.isStreaming, streamState.phase, activeStreamBuffer?.phase, activeStreamBuffer?.metadata?.phase_key])

  const streamToolbar = useMemo(() => {
    const { order, buffers, pinned } = researchAgentStatus.streams
    if (!order || order.length === 0) {
      return null
    }
    const pinnedSet = new Set(pinned)
    const sortedIds = [
      ...order.filter((id) => pinnedSet.has(id)),
      ...order.filter((id) => !pinnedSet.has(id)),
    ]

    return (
      <div className="flex flex-wrap items-center gap-2">
        {sortedIds.map((id) => {
          const buffer = buffers[id]
          if (!buffer) {
            return null
          }
          const label =
            buffer.metadata?.title ||
            buffer.metadata?.component ||
            buffer.metadata?.link_id ||
            buffer.phase ||
            id.split(':').slice(-2).join(':')
          const isActive = streamState.streamId === id
          const isPinned = pinnedSet.has(id)
          const statusClass =
            buffer.status === 'error'
              ? 'bg-red-500'
              : buffer.status === 'completed'
              ? 'bg-neutral-400'
              : 'bg-primary-500 animate-pulse'

          return (
            <button
              key={id}
              type="button"
              className={classNames(
                'inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs transition',
                isActive ? 'border-primary-300 bg-primary-50 text-primary-700' : 'border-neutral-200 bg-white text-neutral-600 hover:border-primary-200 hover:text-primary-600'
              )}
              onClick={() => setActiveStream(id)}
            >
              <span className={classNames('h-2 w-2 rounded-full', statusClass)} aria-hidden="true" />
              <span className="truncate max-w-[120px]" title={label}>
                {label}
              </span>
              {typeof buffer.tokenCount === 'number' && buffer.tokenCount > 0 && (
                <span className="text-[10px] text-neutral-400">{buffer.tokenCount}</span>
              )}
              <button
                type="button"
                className={classNames(
                  'ml-1 text-xs transition',
                  isPinned ? 'text-amber-500 hover:text-amber-600' : 'text-neutral-300 hover:text-neutral-500'
                )}
                onClick={(event) => {
                  event.preventDefault()
                  event.stopPropagation()
                  if (isPinned) {
                    unpinStream(id)
                  } else {
                    pinStream(id)
                  }
                }}
                aria-label={isPinned ? '取消固定' : '固定流'}
              >
                {isPinned ? '★' : '☆'}
              </button>
            </button>
          )
        })}
      </div>
    )
  }, [researchAgentStatus.streams, pinStream, unpinStream, setActiveStream, streamState.streamId])

  const handleSendInput = () => {
    // Debug logging
    console.log('handleSendInput called', {
      userInput: userInput,
      userInputTrimmed: userInput.trim(),
      hasUserInputRequired: !!researchAgentStatus.userInputRequired,
      userInputRequired: researchAgentStatus.userInputRequired,
      prompt_id: researchAgentStatus.userInputRequired?.prompt_id,
      batchId: batchId,
    })

    // Check if userInputRequired state exists
    if (!researchAgentStatus.userInputRequired) {
      console.warn('Early return: userInputRequired is null/undefined')
      return
    }

    // Extract prompt_id
    const promptId = researchAgentStatus.userInputRequired.prompt_id
    if (!promptId) {
      console.error('Cannot send user input: prompt_id is missing', {
        userInputRequired: researchAgentStatus.userInputRequired,
      })
      return
    }

    // Send message (empty string is valid for approval)
    const response = userInput.trim()
    console.log('Sending message:', { prompt_id: promptId, response })
    
    sendMessage('research:user_input', {
      prompt_id: promptId,
      response: response,
    })

    // Clear input after sending
    setUserInput('')
  }

  const handleChoiceClick = (choice: string) => {
    console.log('handleChoiceClick called', {
      choice: choice,
      hasUserInputRequired: !!researchAgentStatus.userInputRequired,
      prompt_id: researchAgentStatus.userInputRequired?.prompt_id,
    })

    if (!researchAgentStatus.userInputRequired) {
      console.warn('Early return: userInputRequired is null/undefined')
      return
    }

    const promptId = researchAgentStatus.userInputRequired.prompt_id
    if (!promptId) {
      console.error('Cannot send user input: prompt_id is missing', {
        userInputRequired: researchAgentStatus.userInputRequired,
      })
      return
    }

    console.log('Sending choice:', { prompt_id: promptId, response: choice })
    sendMessage('research:user_input', {
      prompt_id: promptId,
      response: choice,
    })
  }

  useEffect(() => {
    if (displayPlanEntries.length > 0) {
      setCurrentPlanIndex((prev) => (prev >= displayPlanEntries.length ? 0 : prev))
    } else {
      setCurrentPlanIndex(0)
    }
  }, [displayPlanEntries.length])

  // Navigation functions for plan
  const goToNextPlan = () => {
    if (displayPlanEntries.length > 0) {
      setCurrentPlanIndex((prev) => (prev < displayPlanEntries.length - 1 ? prev + 1 : prev))
    }
  }

  const goToPreviousPlan = () => {
    setCurrentPlanIndex((prev) => (prev > 0 ? prev - 1 : 0))
  }

  const goToPlan = (index: number) => {
    if (index >= 0 && index < displayPlanEntries.length) {
      setCurrentPlanIndex(index)
    }
  }

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle if not typing in an input/textarea
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return
      }

      // Plan navigation (Shift + Arrow keys)
      if (researchAgentStatus.plan && researchAgentStatus.plan.length > 0) {
        if (e.key === 'ArrowRight' && e.shiftKey) {
          e.preventDefault()
          setCurrentPlanIndex((prev) =>
            prev < researchAgentStatus.plan!.length - 1 ? prev + 1 : prev
          )
        } else if (e.key === 'ArrowLeft' && e.shiftKey) {
          e.preventDefault()
          setCurrentPlanIndex((prev) => (prev > 0 ? prev - 1 : 0))
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [researchAgentStatus.plan])

  return (
    <div className="max-w-6xl mx-auto">
      <Card
        title="研究规划"
        subtitle={
          <span className="shiny-text-hover">
            当前阶段: {researchAgentStatus.phase || '准备中'}
          </span>
        }
      >
        <div className="space-y-6">
          {/* Synthesized Goal Display */}
          {researchAgentStatus.synthesizedGoal && (
            <div className="bg-primary-50 p-6 rounded-lg border border-primary-200">
              <h3 className="text-lg font-semibold text-primary-900 mb-3 shiny-text-hover">
                研究主题
              </h3>
              <p className="text-primary-800 mb-2">
                {researchAgentStatus.synthesizedGoal.comprehensive_topic}
              </p>
              {researchAgentStatus.synthesizedGoal.unifying_theme && (
                <p className="text-sm text-primary-600 mt-2">
                  <span className="font-medium">核心主题:</span>{' '}
                  {researchAgentStatus.synthesizedGoal.unifying_theme}
                </p>
              )}
              {researchAgentStatus.synthesizedGoal.component_questions &&
                researchAgentStatus.synthesizedGoal.component_questions.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm font-medium text-primary-700 mb-2">
                      相关问题:
                    </p>
                    <ul className="list-disc list-inside space-y-1 text-sm text-primary-600">
                      {researchAgentStatus.synthesizedGoal.component_questions.map(
                        (q, idx) => (
                          <li key={idx}>{q}</li>
                        )
                      )}
                    </ul>
                  </div>
                )}
            </div>
          )}

          {/* Goals Display - List View */}
          {researchAgentStatus.goals && researchAgentStatus.goals.length > 0 && (
            <div className="bg-neutral-light-bg p-6 rounded-lg border border-neutral-300">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-neutral-900 shiny-text-hover">研究目标</h3>
                <span className="text-sm text-neutral-500">一次性浏览所有目标，提升审阅效率</span>
              </div>

              <ResearchGoalList goals={displayGoals} />
            </div>
          )}

          {/* Plan Display - Single View with Navigation */}
          {displayPlanEntries.length > 0 && (
            <div className="bg-neutral-light-bg p-6 rounded-lg border border-neutral-300">
              <h3 className="text-lg font-semibold text-neutral-900 mb-3 shiny-text-hover">
                研究计划
              </h3>
              
              {/* Navigation Controls */}
              <div className="flex items-center justify-between mb-4">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={goToPreviousPlan}
                  disabled={currentPlanIndex === 0}
                  aria-label="上一个步骤"
                >
                  ← 上一个
                </Button>
                
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-neutral-700 shiny-text-pulse">
                    步骤 {currentPlanIndex + 1} / {displayPlanEntries.length}
                  </span>
                  {displayPlanEntries.length > 1 && (
                    <select
                      value={currentPlanIndex}
                      onChange={(e) => goToPlan(Number(e.target.value))}
                      className="text-sm border border-neutral-300 rounded px-2 py-1 bg-neutral-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      aria-label="选择步骤"
                    >
                      {displayPlanEntries.map((step, index) => (
                        <option key={step.step_id} value={index}>
                          步骤 {step.step_id}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
                
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={goToNextPlan}
                  disabled={currentPlanIndex === displayPlanEntries.length - 1}
                  aria-label="下一个步骤"
                >
                  下一个 →
                </Button>
              </div>

              {/* Current Step Display */}
              {displayPlanEntries[currentPlanIndex] && (() => {
                const currentPlan = displayPlanEntries[currentPlanIndex]
                if (!currentPlan) return null
                return (
                <div className="bg-neutral-white rounded-lg border border-neutral-200 p-4">
                  <div className="flex items-start gap-3">
                    <span className="text-primary-500 font-semibold text-lg">
                      步骤 {currentPlan.step_id}
                    </span>
                    <div className="flex-1">
                      <p className="font-medium text-neutral-900 text-base leading-relaxed">
                        {currentPlan.goal || '正在生成研究步骤…'}
                      </p>
                      {currentPlan.required_data && (
                        <p className="text-sm text-neutral-600 mt-2">
                          <span className="font-medium">需要数据:</span>{' '}
                          {currentPlan.required_data}
                        </p>
                      )}
                      {currentPlan.chunk_strategy && (
                        <p className="text-sm text-neutral-600 mt-1">
                          <span className="font-medium">处理方式:</span>{' '}
                          {currentPlan.chunk_strategy}
                        </p>
                      )}
                      {currentPlan.notes && (
                        <p className="text-sm text-neutral-500 mt-2 italic border-l-2 border-neutral-300 pl-3">
                          {currentPlan.notes}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
                )
              })()}

              {/* Keyboard hint */}
              {displayPlanEntries.length > 1 && (
                <p className="text-xs text-neutral-400 mt-2 text-center">
                  提示: 使用 Shift + ←/→ 键快速导航
                </p>
              )}
            </div>
          )}

          <StreamDisplay
            content={streamState.content}
            phase={streamState.phase}
            metadata={streamMetadata}
            isStreaming={streamState.isStreaming}
            subtitle={researchAgentStatus.currentAction || undefined}
            secondaryView={<StreamStructuredView streamId={streamState.streamId ?? undefined} />}
            viewMode="tabs"
            collapsible
            toolbar={streamToolbar}
          />

          {/* Current Action */}
          {researchAgentStatus.currentAction && (
            <div className="text-sm text-neutral-600 shiny-text-pulse">
              {researchAgentStatus.currentAction}
            </div>
          )}

          {/* User Input Area */}
          {researchAgentStatus.waitingForUser &&
            researchAgentStatus.userInputRequired && (
              <div className="bg-neutral-light-bg p-6 rounded-lg border-2 border-primary-300">
                <h3 className="text-lg font-semibold text-neutral-900 mb-3 shiny-text-pulse">
                  需要您的确认
                </h3>
                <p className="text-neutral-700 mb-4 shiny-text-pulse">
                  {researchAgentStatus.userInputRequired.data?.prompt ||
                    researchAgentStatus.userInputRequired.prompt}
                </p>

                {/* Choice Buttons */}
                {researchAgentStatus.userInputRequired.data?.choices &&
                  researchAgentStatus.userInputRequired.data.choices.length >
                    0 && (
                    <div className="mb-4">
                      <p className="text-sm text-neutral-600 mb-2">
                        请选择:
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {researchAgentStatus.userInputRequired.data.choices.map(
                          (choice: string, idx: number) => (
                            <Button
                              key={idx}
                              variant="secondary"
                              size="sm"
                              onClick={() => handleChoiceClick(choice)}
                            >
                              {choice}
                            </Button>
                          )
                        )}
                      </div>
                    </div>
                  )}

                {/* Text Input */}
                {(!researchAgentStatus.userInputRequired.data?.choices ||
                  researchAgentStatus.userInputRequired.data.choices.length ===
                    0) && (
                  <div className="space-y-3">
                    <Textarea
                      value={userInput}
                      onChange={(e) => setUserInput(e.target.value)}
                      placeholder='请输入您的回复或直接点击"确认继续"以批准...'
                      rows={4}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                          handleSendInput()
                        }
                      }}
                    />
                    <Button 
                      onClick={handleSendInput} 
                      disabled={!researchAgentStatus.userInputRequired}
                    >
                      {userInput.trim() ? '发送' : '确认继续'}
                    </Button>
                  </div>
                )}
              </div>
            )}
        </div>
      </Card>
    </div>
  )
}

export default ResearchAgentPage


