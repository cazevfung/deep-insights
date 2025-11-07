import { useMemo } from 'react'
import { useWorkflowStore } from '../stores/workflowStore'
import { IconName } from '../components/common/Icon'

export type StepStatus = 'not-started' | 'in-progress' | 'completed' | 'error'

export interface WorkflowStep {
  id: number
  label: string
  icon: IconName
  route: string
  status: StepStatus
  isVisible: boolean
}

export const useWorkflowSteps = (): WorkflowStep[] => {
  const {
    batchId,
    currentPhase,
    scrapingStatus,
    cancelled,
    researchAgentStatus,
    phase3Steps,
    finalReport,
  } = useWorkflowStore()

  return useMemo(() => {
    const steps: WorkflowStep[] = []

    // Step 1: Link Input
    const step1Status: StepStatus = batchId ? 'completed' : 'in-progress'
    steps.push({
      id: 1,
      label: '链接输入',
      icon: 'link',
      route: '/',
      status: step1Status,
      isVisible: true, // Always visible
    })

    // Step 2: Scraping
    // Use backend's is_100_percent flag (calculated against expected_total)
    // This ensures we only mark complete when ALL expected processes are done
    const scrapingComplete = scrapingStatus.is100Percent || scrapingStatus.canProceedToResearch
    const scrapingInProgress =
      scrapingStatus.total > 0 &&
      scrapingStatus.inProgress > 0 &&
      !scrapingComplete &&
      !cancelled
    const step2Status: StepStatus = cancelled
      ? 'error'
      : scrapingComplete
      ? 'completed'
      : scrapingInProgress || batchId
      ? 'in-progress'
      : 'not-started'
    const step2Visible = batchId !== null // Show when batchId exists
    steps.push({
      id: 2,
      label: '内容抓取',
      icon: 'download',
      route: '/scraping',
      status: step2Status,
      isVisible: step2Visible,
    })

    // Step 3: Research Agent
    const researchStarted = researchAgentStatus.phase !== '0.5' || researchAgentStatus.goals !== null
    const researchComplete = researchAgentStatus.phase === '2' && researchAgentStatus.plan !== null && researchAgentStatus.plan.length > 0
    const step3Status: StepStatus = researchComplete
      ? 'completed'
      : researchStarted || scrapingComplete
      ? 'in-progress'
      : 'not-started'
    // Only show when scraping is COMPLETELY done AND research has started
    // This prevents premature appearance before all scraping results are finalized
    const step3Visible = scrapingComplete && researchStarted
    steps.push({
      id: 3,
      label: '研究代理',
      icon: 'research',
      route: '/research',
      status: step3Status,
      isVisible: step3Visible,
    })

    // Step 4: Phase 3
    const phase3Started = phase3Steps.length > 0
    const phase3Complete = researchAgentStatus.plan !== null && 
      phase3Steps.length > 0 &&
      phase3Steps.length >= researchAgentStatus.plan.length
    const step4Status: StepStatus = phase3Complete
      ? 'completed'
      : phase3Started || researchComplete
      ? 'in-progress'
      : 'not-started'
    const step4Visible = researchComplete || phase3Started // Show when research completes or phase3 starts
    steps.push({
      id: 4,
      label: '深度研究',
      icon: 'chart',
      route: '/phase3',
      status: step4Status,
      isVisible: step4Visible,
    })

    // Step 5: Final Report
    const reportReady = finalReport?.status === 'ready'
    const reportGenerating = finalReport?.status === 'generating'
    const step5Status: StepStatus = reportReady
      ? 'completed'
      : reportGenerating || phase3Complete
      ? 'in-progress'
      : 'not-started'
    const step5Visible = phase3Complete || reportGenerating || reportReady // Show when phase3 completes or report starts
    steps.push({
      id: 5,
      label: '最终报告',
      icon: 'file',
      route: '/report',
      status: step5Status,
      isVisible: step5Visible,
    })

    return steps
  }, [
    batchId,
    currentPhase,
    scrapingStatus,
    cancelled,
    researchAgentStatus,
    phase3Steps,
    finalReport,
  ])
}

/**
 * Get the current active step (the one that should be displayed)
 */
export const useCurrentActiveStep = (): number | null => {
  const steps = useWorkflowSteps()
  
  return useMemo(() => {
    // Find the first in-progress step
    const inProgressStep = steps.find((step) => step.status === 'in-progress' && step.isVisible)
    if (inProgressStep) return inProgressStep.id

    // If no in-progress, find the last completed step
    const completedSteps = steps.filter((step) => step.status === 'completed' && step.isVisible)
    if (completedSteps.length > 0) {
      return completedSteps[completedSteps.length - 1].id
    }

    // Default to step 1
    return 1
  }, [steps])
}

