import React, { useMemo } from 'react'
import Card from '../components/common/Card'
import Phase3StatusBanner from '../components/phase3/Phase3StatusBanner'
import Phase3StepList from '../components/phase3/Phase3StepList'
import { usePhase3Steps } from '../hooks/usePhase3Steps'

const Phase3SessionPage: React.FC = () => {
  const phase3State = usePhase3Steps()

  const activeStep = useMemo(() => {
    if (!phase3State.activeStepId) {
      return undefined
    }
    return phase3State.steps.find((step) => step.id === phase3State.activeStepId)
  }, [phase3State.steps, phase3State.activeStepId])

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <Card title="深度研究 - 分析步骤">
        <div className="space-y-4">
          <Phase3StatusBanner rerunState={phase3State.rerunState} reportStale={phase3State.reportStale} />

          {activeStep && (
            <div className="rounded-xl border border-primary-200 bg-primary-50/60 px-4 py-3 text-sm text-primary-700 shadow-[0_10px_25px_-20px_rgba(59,130,246,0.75)]">
              正在聚焦步骤 {activeStep.id}: {activeStep.title}
            </div>
          )}

          {!phase3State.hasAnySteps ? (
            <p className="text-neutral-400 py-8 text-center">还没有分析步骤，研究完成后将显示在这里</p>
          ) : (
            <Phase3StepList
              steps={phase3State.steps}
              rerunState={phase3State.rerunState}
              onToggleStep={phase3State.handleToggleStep}
              onToggleRawData={phase3State.handleToggleRawData}
              onRerun={phase3State.handleRerunStep}
            />
          )}
        </div>
      </Card>
    </div>
  )
}

export default Phase3SessionPage
