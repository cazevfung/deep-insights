import React from 'react'
import { Icon } from '../common/Icon'
import Phase3StepContent from './Phase3StepContent'
import { Phase3StepViewModel, StepRerunState } from '../../hooks/usePhase3Steps'

interface Phase3StepCardProps {
  step: Phase3StepViewModel
  onToggleExpand: (stepId: number) => void
  onRerun: (stepId: number, regenerateReport: boolean) => void
  rerunState: StepRerunState
}

const classNames = (...classes: Array<string | false | null | undefined>) =>
  classes.filter(Boolean).join(' ')

const iconButtonClass =
  'flex h-9 w-9 items-center justify-center rounded-full border border-neutral-300 text-neutral-600 hover:bg-neutral-100 transition-colors disabled:opacity-40 disabled:cursor-not-allowed'

const StepBadge: React.FC<{ active: boolean; label: number | string }> = ({ active, label }) => (
  <span
    className={classNames(
      'flex-none rounded-full px-3 py-1 text-sm font-semibold tracking-wide transition-colors duration-200',
      active ? 'bg-primary-100 text-primary-700 shadow-[0_4px_12px_-6px_rgba(59,130,246,0.45)]' : 'bg-neutral-200 text-neutral-600'
    )}
  >
    {label}
  </span>
)

const PlaceholderCard: React.FC<{ step: Phase3StepViewModel }> = ({ step }) => (
  <div className="border border-dashed border-gray-300 rounded-xl p-4 bg-gray-50">
    <div className="flex items-start gap-3">
      <StepBadge active={false} label={step.id} />
      <div className="w-1 bg-neutral-300/60 rounded-full self-stretch ml-0.5 mr-3" />
      <div className="flex-1 space-y-1">
        <h3 className="font-semibold text-neutral-600 mt-0 line-clamp-1">{step.title}</h3>
        <p className="text-sm text-neutral-400">
          {step.status === 'in-progress' ? '正在处理中...' : '尚未开始'}
        </p>
      </div>
      <span className="text-xs px-2 py-1 bg-neutral-200 text-neutral-500 rounded-full">
        {step.status === 'in-progress' ? '进行中' : '待启动'}
      </span>
    </div>
  </div>
)

const Phase3StepCard: React.FC<Phase3StepCardProps> = ({
  step,
  onToggleExpand,
  onRerun,
  rerunState,
}) => {
  if (!step.canExpand) {
    return <PlaceholderCard step={step} />
  }

  const handleToggle = () => onToggleExpand(step.id)
  const handleRerun = (regenerateReport: boolean) => onRerun(step.id, regenerateReport)

  const showSummary = Boolean(step.summaryPreview)
  const showConfidenceBadge = typeof step.confidence === 'number' && !Number.isNaN(step.confidence)
  const isGlobalRerunInProgress = Boolean(rerunState?.inProgress)
  const spinnerActive = step.rerunSpinner.active
  const spinnerShowsReport = spinnerActive && step.rerunSpinner.regenerateReport
  const spinnerShowsStepOnly = spinnerActive && !step.rerunSpinner.regenerateReport

  return (
    <div
      className={classNames(
        'border transition-all duration-200',
        'rounded-xl',
        'bg-white shadow-sm hover:shadow-md',
        step.isActive
          ? 'border-primary-200 shadow-[0_20px_45px_-24px_rgba(59,130,246,0.6)] ring-1 ring-primary-300/50'
          : 'border-gray-200'
      )}
      data-active={step.isActive || undefined}
    >
      <div className={classNames(
        'sticky top-0 z-10 p-4 flex gap-4 items-start bg-white',
        step.isExpanded ? 'rounded-t-xl border-b border-neutral-100' : 'rounded-xl'
      )}>
        <StepBadge active={step.isActive} label={step.id} />
        <div
          className={classNames(
            'w-1 rounded-full self-stretch transition-colors duration-200',
            step.isActive ? 'bg-primary-300' : 'bg-neutral-200'
          )}
        />
        <div className="flex-1 flex items-start gap-6">
          <button
            onClick={handleToggle}
            className={classNames(
              'flex-1 text-left space-y-2 rounded-md transition-colors px-1 py-0 -ml-2',
              'focus:outline-none focus:ring-2 focus:ring-primary-400 focus:ring-offset-2',
              'hover:bg-neutral-50'
            )}
            aria-expanded={step.isExpanded}
          >
            <h3
              className={classNames(
                'font-semibold text-base md:text-lg leading-snug mt-0 transition-colors',
                step.isActive ? 'text-primary-900' : 'text-neutral-800'
              )}
            >
              {step.title}
            </h3>
            {showSummary && (
              <p className="text-sm text-neutral-500 line-clamp-1">{step.summaryPreview}</p>
            )}
          </button>
          <div className="flex items-center gap-2 self-start">
            {showConfidenceBadge && (
              <span className="text-xs px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full font-medium">
                {(step.confidence! * 100).toFixed(0)}%
              </span>
            )}
            <button
              className={iconButtonClass}
              onClick={() => handleRerun(true)}
              disabled={isGlobalRerunInProgress}
              title="重新执行并生成报告"
              aria-label="重新执行并生成报告"
            >
              {spinnerShowsReport ? (
                <span className="h-4 w-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
              ) : (
                <Icon name="refresh" size={16} strokeWidth={2} />
              )}
            </button>
            <button
              className={iconButtonClass}
              onClick={() => handleRerun(false)}
              disabled={isGlobalRerunInProgress}
              title="仅重新执行步骤"
              aria-label="仅重新执行步骤"
            >
              {spinnerShowsStepOnly ? (
                <span className="h-4 w-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
              ) : (
                <Icon name="file" size={16} strokeWidth={2} />
              )}
            </button>
            <button
              onClick={handleToggle}
              className={classNames(iconButtonClass, 'text-neutral-500')}
              aria-label={step.isExpanded ? '收起详情' : '展开详情'}
            >
              <Icon name={step.isExpanded ? 'chevron-up' : 'chevron-down'} size={16} strokeWidth={2} />
            </button>
          </div>
        </div>
      </div>
      {step.isExpanded && (
        <div className="px-4 pb-4 border-t border-neutral-100 bg-neutral-50 rounded-b-xl">
          <div className="pt-4">
            <Phase3StepContent
              content={step.content}
              confidence={step.confidence}
              stepId={step.id}
            />
          </div>
        </div>
      )}
    </div>
  )
}

export default Phase3StepCard
