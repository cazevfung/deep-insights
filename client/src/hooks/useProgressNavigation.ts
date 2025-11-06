import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkflowStore } from '../stores/workflowStore'
import { useCurrentActiveStep } from './useWorkflowStep'

const STEP_ROUTES: Record<number, string> = {
  1: '/',
  2: '/scraping',
  3: '/research',
  4: '/phase3',
  5: '/report',
}

/**
 * Hook to automatically navigate to the current active step based on workflow progress
 */
export const useProgressNavigation = () => {
  const navigate = useNavigate()
  const currentActiveStep = useCurrentActiveStep()
  const {
    batchId,
    scrapingStatus,
    cancelled,
    researchAgentStatus,
    phase3Steps,
    finalReport,
  } = useWorkflowStore()

  // Track if we've already navigated to avoid loops
  const lastNavigatedStepRef = useRef<number | null>(null)
  const navigationTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    // Don't navigate if no batchId (still on initial step)
    if (!batchId && currentActiveStep === 1) {
      lastNavigatedStepRef.current = 1
      return
    }

    // Don't navigate if we've already navigated to this step
    if (lastNavigatedStepRef.current === currentActiveStep) {
      return
    }

    // Clear any pending navigation
    if (navigationTimeoutRef.current) {
      clearTimeout(navigationTimeoutRef.current)
    }

    // Debounce navigation to avoid rapid changes
    navigationTimeoutRef.current = setTimeout(() => {
      const targetRoute = STEP_ROUTES[currentActiveStep]
      if (targetRoute) {
        // Only navigate if we're not already on the target route
        if (window.location.pathname !== targetRoute) {
          console.log(`Auto-navigating to step ${currentActiveStep}: ${targetRoute}`)
          navigate(targetRoute, { replace: true })
          lastNavigatedStepRef.current = currentActiveStep
        }
      }
    }, 300) // Small delay to batch rapid state changes

    return () => {
      if (navigationTimeoutRef.current) {
        clearTimeout(navigationTimeoutRef.current)
      }
    }
  }, [currentActiveStep, navigate, batchId])

  // Reset navigation tracking when batchId changes (new session)
  useEffect(() => {
    if (!batchId) {
      lastNavigatedStepRef.current = null
    }
  }, [batchId])
}


