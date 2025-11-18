import { useMemo } from 'react'
import { useLocation } from 'react-router-dom'
import { useWorkflowStore } from '../stores/workflowStore'

/**
 * Hook to determine what navigation elements should be visible
 * Based on the radical reduction strategy: hide by default, show only when essential
 */
export const useAdaptiveNavigation = () => {
  const location = useLocation()
  const { batchId, scrapingStatus, researchAgentStatus, phase3Steps, finalReport } = useWorkflowStore()

  // Determine if workflow has started
  const workflowStarted = useMemo(() => {
    return batchId !== null
  }, [batchId])

  // Determine if workflow is active (scraping, research, or phase3)
  const workflowActive = useMemo(() => {
    if (!workflowStarted) return false
    
    const scrapingComplete = scrapingStatus.is100Percent || scrapingStatus.canProceedToResearch
    const researchComplete = researchAgentStatus.phase === '2' && researchAgentStatus.plan !== null
    const phase3Complete = phase3Steps.length > 0 && 
      researchAgentStatus.plan !== null &&
      phase3Steps.length >= researchAgentStatus.plan.length
    const reportComplete = finalReport?.status === 'ready'

    // Active if any phase is in progress or completed (but not fully done)
    return !reportComplete && (scrapingComplete || researchComplete || phase3Complete || 
      scrapingStatus.inProgress > 0 || phase3Steps.length > 0)
  }, [workflowStarted, scrapingStatus, researchAgentStatus, phase3Steps, finalReport])

  // Determine if workflow is complete
  const workflowComplete = useMemo(() => {
    return finalReport?.status === 'ready' || false
  }, [finalReport])

  // Sidebar: Always visible (per user requirement)
  const showSidebar = true // Always true - always visible

  // Show stepper only:
  // - During active workflow
  // - NOT before workflow starts
  // - NOT after completion (show summary in content instead)
  const showWorkflowStepper = useMemo(() => {
    if (!workflowStarted) return false // Before workflow: hide
    if (workflowComplete) return false // After completion: hide (show summary instead)
    return workflowActive // During workflow: show
  }, [workflowStarted, workflowActive, workflowComplete])

  // PhaseInteractionPanel: Always visible (right column)
  // Per user requirement: should always be there
  const showPhaseInteractionPanel = true // Always true - always visible

  // Determine navigation mode
  const navigationMode = useMemo(() => {
    if (!workflowStarted) return 'minimal' as const
    if (workflowComplete) return 'minimal' as const
    return 'standard' as const
  }, [workflowStarted, workflowComplete])

  return {
    showSidebar,
    showWorkflowStepper,
    showPhaseInteractionPanel,
    navigationMode,
    workflowStarted,
    workflowActive,
    workflowComplete,
  }
}

