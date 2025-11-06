import React, { useState, useEffect } from 'react'
import Card from '../components/common/Card'
import Button from '../components/common/Button'
import Textarea from '../components/common/Textarea'
import { useWorkflowStore } from '../stores/workflowStore'
import { useWebSocket } from '../hooks/useWebSocket'

const ResearchAgentPage: React.FC = () => {
  const { researchAgentStatus, batchId } = useWorkflowStore()
  const { sendMessage } = useWebSocket(batchId || '')
  const [userInput, setUserInput] = useState('')
  const [currentGoalIndex, setCurrentGoalIndex] = useState(0)
  const [currentPlanIndex, setCurrentPlanIndex] = useState(0)

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

  // Reset indices when goals/plan change
  useEffect(() => {
    if (researchAgentStatus.goals && researchAgentStatus.goals.length > 0) {
      setCurrentGoalIndex((prev) => {
        // Only reset if current index is out of bounds
        return prev >= researchAgentStatus.goals!.length ? 0 : prev
      })
    } else {
      setCurrentGoalIndex(0)
    }
  }, [researchAgentStatus.goals])

  useEffect(() => {
    if (researchAgentStatus.plan && researchAgentStatus.plan.length > 0) {
      setCurrentPlanIndex((prev) => {
        // Only reset if current index is out of bounds
        return prev >= researchAgentStatus.plan!.length ? 0 : prev
      })
    } else {
      setCurrentPlanIndex(0)
    }
  }, [researchAgentStatus.plan])

  // Navigation functions for goals
  const goToNextGoal = () => {
    if (researchAgentStatus.goals) {
      setCurrentGoalIndex((prev) =>
        prev < researchAgentStatus.goals!.length - 1 ? prev + 1 : prev
      )
    }
  }

  const goToPreviousGoal = () => {
    setCurrentGoalIndex((prev) => (prev > 0 ? prev - 1 : 0))
  }

  const goToGoal = (index: number) => {
    if (
      researchAgentStatus.goals &&
      index >= 0 &&
      index < researchAgentStatus.goals.length
    ) {
      setCurrentGoalIndex(index)
    }
  }

  // Navigation functions for plan
  const goToNextPlan = () => {
    if (researchAgentStatus.plan) {
      setCurrentPlanIndex((prev) =>
        prev < researchAgentStatus.plan!.length - 1 ? prev + 1 : prev
      )
    }
  }

  const goToPreviousPlan = () => {
    setCurrentPlanIndex((prev) => (prev > 0 ? prev - 1 : 0))
  }

  const goToPlan = (index: number) => {
    if (
      researchAgentStatus.plan &&
      index >= 0 &&
      index < researchAgentStatus.plan.length
    ) {
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

      // Goals navigation (Ctrl + Arrow keys)
      if (researchAgentStatus.goals && researchAgentStatus.goals.length > 0) {
        if (e.key === 'ArrowRight' && e.ctrlKey) {
          e.preventDefault()
          setCurrentGoalIndex((prev) =>
            prev < researchAgentStatus.goals!.length - 1 ? prev + 1 : prev
          )
        } else if (e.key === 'ArrowLeft' && e.ctrlKey) {
          e.preventDefault()
          setCurrentGoalIndex((prev) => (prev > 0 ? prev - 1 : 0))
        }
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
  }, [researchAgentStatus.goals, researchAgentStatus.plan])

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

          {/* Goals Display - Single View with Navigation */}
          {researchAgentStatus.goals && researchAgentStatus.goals.length > 0 && (
            <div className="bg-neutral-light-bg p-6 rounded-lg border border-neutral-300">
              <h3 className="text-lg font-semibold text-neutral-900 mb-3 shiny-text-hover">
                研究目标
              </h3>
              
              {/* Navigation Controls */}
              <div className="flex items-center justify-between mb-4">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={goToPreviousGoal}
                  disabled={currentGoalIndex === 0}
                  aria-label="上一个目标"
                >
                  ← 上一个
                </Button>
                
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-neutral-700 shiny-text-pulse">
                    目标 {currentGoalIndex + 1} / {researchAgentStatus.goals.length}
                  </span>
                  {researchAgentStatus.goals.length > 1 && (
                    <select
                      value={currentGoalIndex}
                      onChange={(e) => goToGoal(Number(e.target.value))}
                      className="text-sm border border-neutral-300 rounded px-2 py-1 bg-neutral-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      aria-label="选择目标"
                    >
                      {researchAgentStatus.goals.map((_, index) => (
                        <option key={index} value={index}>
                          目标 {index + 1}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
                
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={goToNextGoal}
                  disabled={currentGoalIndex === researchAgentStatus.goals.length - 1}
                  aria-label="下一个目标"
                >
                  下一个 →
                </Button>
              </div>

              {/* Current Goal Display */}
              {researchAgentStatus.goals[currentGoalIndex] && (
                <div className="bg-neutral-white rounded-lg border border-neutral-200 p-4">
                  <div className="flex items-start gap-3">
                    <span className="text-primary-500 font-medium text-lg">
                      {researchAgentStatus.goals[currentGoalIndex].id}.
                    </span>
                    <div className="flex-1">
                      <p className="text-neutral-800 text-base leading-relaxed">
                        {researchAgentStatus.goals[currentGoalIndex].goal_text}
                      </p>
                      {researchAgentStatus.goals[currentGoalIndex].uses &&
                        researchAgentStatus.goals[currentGoalIndex].uses!.length > 0 && (
                          <p className="text-sm text-neutral-500 mt-2">
                            <span className="font-medium">用途:</span>{' '}
                            {researchAgentStatus.goals[currentGoalIndex].uses!.join(', ')}
                          </p>
                        )}
                    </div>
                  </div>
                </div>
              )}

              {/* Keyboard hint */}
              {researchAgentStatus.goals.length > 1 && (
                <p className="text-xs text-neutral-400 mt-2 text-center">
                  提示: 使用 Ctrl + ←/→ 键快速导航
                </p>
              )}
            </div>
          )}

          {/* Plan Display - Single View with Navigation */}
          {researchAgentStatus.plan && researchAgentStatus.plan.length > 0 && (
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
                    步骤 {currentPlanIndex + 1} / {researchAgentStatus.plan.length}
                  </span>
                  {researchAgentStatus.plan.length > 1 && (
                    <select
                      value={currentPlanIndex}
                      onChange={(e) => goToPlan(Number(e.target.value))}
                      className="text-sm border border-neutral-300 rounded px-2 py-1 bg-neutral-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      aria-label="选择步骤"
                    >
                      {researchAgentStatus.plan.map((step, index) => (
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
                  disabled={currentPlanIndex === researchAgentStatus.plan.length - 1}
                  aria-label="下一个步骤"
                >
                  下一个 →
                </Button>
              </div>

              {/* Current Step Display */}
              {researchAgentStatus.plan[currentPlanIndex] && (
                <div className="bg-neutral-white rounded-lg border border-neutral-200 p-4">
                  <div className="flex items-start gap-3">
                    <span className="text-primary-500 font-semibold text-lg">
                      步骤 {researchAgentStatus.plan[currentPlanIndex].step_id}
                    </span>
                    <div className="flex-1">
                      <p className="font-medium text-neutral-900 text-base leading-relaxed">
                        {researchAgentStatus.plan[currentPlanIndex].goal}
                      </p>
                      {researchAgentStatus.plan[currentPlanIndex].required_data && (
                        <p className="text-sm text-neutral-600 mt-2">
                          <span className="font-medium">需要数据:</span>{' '}
                          {researchAgentStatus.plan[currentPlanIndex].required_data}
                        </p>
                      )}
                      {researchAgentStatus.plan[currentPlanIndex].chunk_strategy && (
                        <p className="text-sm text-neutral-600 mt-1">
                          <span className="font-medium">处理方式:</span>{' '}
                          {researchAgentStatus.plan[currentPlanIndex].chunk_strategy}
                        </p>
                      )}
                      {researchAgentStatus.plan[currentPlanIndex].notes && (
                        <p className="text-sm text-neutral-500 mt-2 italic border-l-2 border-neutral-300 pl-3">
                          {researchAgentStatus.plan[currentPlanIndex].notes}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Keyboard hint */}
              {researchAgentStatus.plan.length > 1 && (
                <p className="text-xs text-neutral-400 mt-2 text-center">
                  提示: 使用 Shift + ←/→ 键快速导航
                </p>
              )}
            </div>
          )}

          {/* AI Response Display - Only show when there's content */}
          {researchAgentStatus.streamBuffer && (
            <div className="bg-neutral-white p-6 rounded-lg border border-neutral-300 min-h-64">
              <div className="font-mono text-sm whitespace-pre-wrap">
                {researchAgentStatus.streamBuffer}
              </div>
            </div>
          )}

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
                          (choice, idx) => (
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


