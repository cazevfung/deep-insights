import React, { useMemo } from 'react'
import Phase3StepCard from './Phase3StepCard'
import { Phase3StepViewModel, StepRerunState } from '../../hooks/usePhase3Steps'

interface Phase3StepListProps {
  steps: Phase3StepViewModel[]
  rerunState: StepRerunState
  onToggleStep: (stepId: number) => void
  onRerun: (stepId: number, regenerateReport: boolean) => void
}

const Phase3StepList: React.FC<Phase3StepListProps> = ({
  steps,
  rerunState,
  onToggleStep,
  onRerun,
}) => {
  // Ensure steps are sorted by id (step_id) to maintain correct display order
  // This is a defensive measure to ensure proper ordering even if the hook returns unsorted steps
  const sortedSteps = useMemo(() => {
    return [...steps].sort((a, b) => a.id - b.id)
  }, [steps])

  if (!sortedSteps.length) {
    return null
  }

  return (
    <div className="space-y-4">
      {sortedSteps.map((step) => (
        <Phase3StepCard
          key={step.id}
          step={step}
          rerunState={rerunState}
          onToggleExpand={onToggleStep}
          onRerun={onRerun}
        />
      ))}
    </div>
  )
}

export default Phase3StepList








