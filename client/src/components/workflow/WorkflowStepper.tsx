import React from 'react'
import { useWorkflowSteps } from '../../hooks/useWorkflowStep'
import { Icon } from '../common/Icon'

const WorkflowStepper: React.FC = () => {
  const steps = useWorkflowSteps()

  // Filter to only show visible steps
  const visibleSteps = steps.filter((step) => step.isVisible)

  // Find current step (in-progress or most recent completed)
  const currentStep = React.useMemo(() => {
    const inProgressStep = visibleSteps.find((step) => step.status === 'in-progress')
    if (inProgressStep) return inProgressStep

    // If no in-progress, find the last completed step
    const completedSteps = visibleSteps.filter((step) => step.status === 'completed')
    if (completedSteps.length > 0) {
      return completedSteps[completedSteps.length - 1]
    }

    // Fallback to first step
    return visibleSteps[0]
  }, [visibleSteps])

  const getStatusIcon = (step: typeof steps[0]) => {
    if (step.status === 'completed') {
      return (
        <span className="flex-shrink-0 w-5 h-5 rounded-full bg-green-500 flex items-center justify-center text-white">
          <Icon name="check" size={12} strokeWidth={3} className="text-white" />
        </span>
      )
    }

    if (step.status === 'in-progress') {
      return (
        <span className="flex-shrink-0 w-5 h-5 rounded-full bg-yellow-500 flex items-center justify-center text-white animate-pulse">
          <Icon name="clock" size={12} strokeWidth={3} className="text-white" />
        </span>
      )
    }

    if (step.status === 'error') {
      return (
        <span className="flex-shrink-0 w-5 h-5 rounded-full bg-red-500 flex items-center justify-center text-white">
          <Icon name="x" size={12} strokeWidth={3} className="text-white" />
        </span>
      )
    }

    return (
      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-gray-300 flex items-center justify-center text-gray-500 text-xs font-bold">
        {step.id}
      </span>
    )
  }

  // Calculate progress if available
  const getProgressText = () => {
    if (!currentStep) return ''
    
    const totalVisible = visibleSteps.length
    const currentIndex = visibleSteps.findIndex(s => s.id === currentStep.id)
    if (currentIndex === -1) return ''
    
    return ` (${currentIndex + 1}/${totalVisible})`
  }

  if (!currentStep || visibleSteps.length === 0) {
    return null // Don't render if no steps are visible
  }

  // Minimal stepper: Show only current step
  return (
    <div className="bg-neutral-white border-b border-neutral-300">
      <div className="max-w-7xl mx-auto px-6 py-2">
        <div className="flex items-center gap-2">
          {getStatusIcon(currentStep)}
          <span className="font-medium text-sm text-neutral-700">
            {currentStep.label}
            {currentStep.status === 'in-progress' && '...'}
            {getProgressText()}
          </span>
        </div>
      </div>
    </div>
  )
}

export default WorkflowStepper
