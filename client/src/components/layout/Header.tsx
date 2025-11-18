import React, { useMemo } from 'react'
import { useUiStore } from '../../stores/uiStore'
import { useWorkflowStore } from '../../stores/workflowStore'
import MagicHeaderTransform from '../animations/MagicHeaderTransform'
import CheckpointProgressBar from '../progress/CheckpointProgressBar'

const Header: React.FC = () => {
  const { sidebarOpen, toggleSidebar } = useUiStore()
  const synthesizedGoal = useWorkflowStore((state) => state.researchAgentStatus.synthesizedGoal)
  const comprehensiveTopic = synthesizedGoal?.comprehensive_topic || null
  
  // Get workflow state for checkpoint bar
  const {
    batchId,
    scrapingStatus,
    researchAgentStatus,
    phase3Steps,
    finalReport,
  } = useWorkflowStore()

  // Define checkpoints for the entire session
  const checkpoints = useMemo(() => {
    if (!batchId) return []
    
    const isScrapingComplete = scrapingStatus.is100Percent || scrapingStatus.canProceedToResearch
    const hasSummarization = researchAgentStatus.phase !== '0.5' || researchAgentStatus.summarizationProgress !== null
    const hasGoals = researchAgentStatus.goals !== null && researchAgentStatus.goals.length > 0
    const hasPlan = researchAgentStatus.plan !== null && researchAgentStatus.plan.length > 0
    const hasPhase3Steps = phase3Steps.length > 0
    const phase3Complete = researchAgentStatus.plan !== null && 
      phase3Steps.length > 0 &&
      phase3Steps.length >= researchAgentStatus.plan.length
    const hasReport = finalReport !== null && finalReport.status === 'ready'

    return [
      {
        id: 'content-collection',
        label: '内容收集',
        completed: isScrapingComplete,
      },
      {
        id: 'summarization',
        label: '内容摘要',
        completed: hasSummarization && isScrapingComplete,
      },
      {
        id: 'goal-generation',
        label: '目标生成',
        completed: hasGoals,
      },
      {
        id: 'research-planning',
        label: '研究规划',
        completed: hasPlan,
      },
      {
        id: 'in-depth-research',
        label: '深度研究',
        completed: phase3Complete,
      },
      {
        id: 'report-generation',
        label: '报告生成',
        completed: hasReport,
      },
    ]
  }, [
    batchId,
    scrapingStatus.is100Percent,
    scrapingStatus.canProceedToResearch,
    researchAgentStatus.phase,
    researchAgentStatus.summarizationProgress,
    researchAgentStatus.goals,
    researchAgentStatus.plan,
    phase3Steps,
    finalReport,
  ])

  // Determine current checkpoint index
  const currentCheckpointIndex = useMemo(() => {
    if (!batchId) return undefined
    
    const isScrapingComplete = scrapingStatus.is100Percent || scrapingStatus.canProceedToResearch
    const hasSummarization = researchAgentStatus.phase !== '0.5' || researchAgentStatus.summarizationProgress !== null
    const hasGoals = researchAgentStatus.goals !== null && researchAgentStatus.goals.length > 0
    const hasPlan = researchAgentStatus.plan !== null && researchAgentStatus.plan.length > 0
    const phase3Complete = researchAgentStatus.plan !== null && 
      phase3Steps.length > 0 &&
      phase3Steps.length >= researchAgentStatus.plan.length
    
    if (!isScrapingComplete) {
      return 0 // Content Collection
    }
    if (!hasSummarization) {
      return 1 // Summarization
    }
    if (!hasGoals) {
      return 2 // Goal Generation
    }
    if (!hasPlan) {
      return 3 // Research Planning
    }
    if (!phase3Complete) {
      return 4 // In-depth Research
    }
    if (!finalReport || finalReport.status !== 'ready') {
      return 5 // Report Generation
    }
    return undefined // All completed
  }, [
    batchId,
    scrapingStatus.is100Percent,
    scrapingStatus.canProceedToResearch,
    researchAgentStatus.phase,
    researchAgentStatus.summarizationProgress,
    researchAgentStatus.goals,
    researchAgentStatus.plan,
    phase3Steps,
    finalReport,
  ])

  const showCheckpointBar = batchId && checkpoints.length > 0

  return (
    <header className="bg-neutral-white border-b border-neutral-300">
      <div className="px-6 py-3">
        <div className="flex items-center justify-between">
          {/* Mobile menu button */}
          <button
            onClick={toggleSidebar}
            className="lg:hidden p-2 rounded-lg hover:bg-neutral-300 transition-colors"
            aria-label="Toggle sidebar"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>

          {/* Dynamic title with magic animation */}
          <div className="flex-1">
            <MagicHeaderTransform comprehensiveTopic={comprehensiveTopic} />
          </div>

          {/* Right side - minimal, no version info during workflow */}
          <div className="flex items-center space-x-4">
            {/* Empty for now - can add action button here when needed */}
          </div>
        </div>
      </div>
      
      {/* Checkpoint Progress Bar - Show when workflow is active */}
      {showCheckpointBar && (
        <div className="px-6 pb-2 flex justify-start">
          <CheckpointProgressBar
            checkpoints={checkpoints}
            currentCheckpointIndex={currentCheckpointIndex}
            className="max-w-4xl"
          />
        </div>
      )}
    </header>
  )
}

export default Header


