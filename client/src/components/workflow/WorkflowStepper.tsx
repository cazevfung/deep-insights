import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useWorkflowSteps, useCurrentActiveStep } from '../../hooks/useWorkflowStep'
import { Icon } from '../common/Icon'

const WorkflowStepper: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const steps = useWorkflowSteps()
  const currentActiveStep = useCurrentActiveStep()
  const [isExpanded, setIsExpanded] = useState(true)

  // Filter to only show visible steps
  const visibleSteps = steps.filter((step) => step.isVisible)

  const handleStepClick = (step: typeof steps[0]) => {
    // Only allow navigation to in-progress or completed steps
    if (step.status === 'in-progress' || step.status === 'completed') {
      navigate(step.route)
    }
  }

  const getStepClassName = (step: typeof steps[0]) => {
    const baseClasses = 'flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200 cursor-pointer'
    const isActive = location.pathname === step.route || step.id === currentActiveStep

    if (step.status === 'completed') {
      return `${baseClasses} ${
        isActive
          ? 'bg-green-100 text-green-800 border-2 border-green-500'
          : 'bg-green-50 text-green-700 border border-green-300 hover:bg-green-100'
      }`
    }

    if (step.status === 'in-progress') {
      return `${baseClasses} ${
        isActive
          ? 'bg-yellow-100 text-yellow-800 border-2 border-yellow-500 animate-pulse'
          : 'bg-yellow-50 text-yellow-700 border border-yellow-300 hover:bg-yellow-100'
      }`
    }

    if (step.status === 'error') {
      return `${baseClasses} bg-red-50 text-red-700 border border-red-300`
    }

    return `${baseClasses} bg-gray-50 text-gray-400 border border-gray-200 cursor-not-allowed`
  }

  const getStatusIcon = (step: typeof steps[0]) => {
    if (step.status === 'completed') {
      return (
        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-500 flex items-center justify-center text-white">
          <Icon name="check" size={14} strokeWidth={3} className="text-white" />
        </span>
      )
    }

    if (step.status === 'in-progress') {
      return (
        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-yellow-500 flex items-center justify-center text-white animate-pulse">
          <Icon name="clock" size={14} strokeWidth={3} className="text-white" />
        </span>
      )
    }

    if (step.status === 'error') {
      return (
        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-red-500 flex items-center justify-center text-white">
          <Icon name="x" size={14} strokeWidth={3} className="text-white" />
        </span>
      )
    }

    return (
      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-300 flex items-center justify-center text-gray-500 text-xs font-bold">
        {step.id}
      </span>
    )
  }

  if (visibleSteps.length === 0) {
    return null // Don't render if no steps are visible
  }

  return (
    <div className="bg-neutral-white border-b border-neutral-300">
      <div className="max-w-7xl mx-auto px-6 py-4">
        {/* Expand/Collapse Button */}
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-neutral-600">研究进度</h3>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-neutral-400 hover:text-neutral-600 transition-colors"
            aria-label={isExpanded ? '收起进度' : '展开进度'}
          >
            <svg
              className={`w-5 h-5 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>
        </div>

        {/* Steps Container */}
        {isExpanded && (
          <div className="flex items-center gap-2 overflow-x-auto pb-2">
            {visibleSteps.map((step, index) => (
              <React.Fragment key={step.id}>
                {/* Step */}
                <div
                  onClick={() => handleStepClick(step)}
                  className={getStepClassName(step)}
                  role="button"
                  tabIndex={
                    step.status === 'in-progress' || step.status === 'completed' ? 0 : -1
                  }
                  onKeyDown={(e) => {
                    if (
                      e.key === 'Enter' &&
                      (step.status === 'in-progress' || step.status === 'completed')
                    ) {
                      handleStepClick(step)
                    }
                  }}
                  aria-label={`${step.label} - ${step.status === 'completed' ? '已完成' : step.status === 'in-progress' ? '某种努力中' : '待启动'}`}
                >
                  {getStatusIcon(step)}
                  <span className="font-medium text-sm whitespace-nowrap">{step.label}</span>
                </div>

                {/* Connector Line */}
                {index < visibleSteps.length - 1 && (
                  <div
                    className={`flex-shrink-0 w-8 h-0.5 ${
                      step.status === 'completed' ? 'bg-green-400' : 'bg-gray-300'
                    } transition-colors duration-200`}
                    aria-hidden="true"
                  />
                )}
              </React.Fragment>
            ))}
          </div>
        )}

        {/* Collapsed View */}
        {!isExpanded && (
          <div className="flex items-center gap-2">
            {visibleSteps.map((step) => {
              if (step.status === 'in-progress' || step.id === currentActiveStep) {
                return (
                  <div
                    key={step.id}
                    onClick={() => handleStepClick(step)}
                    className={getStepClassName(step)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleStepClick(step)
                      }
                    }}
                  >
                    {getStatusIcon(step)}
                    <span className="font-medium text-sm whitespace-nowrap">{step.label}</span>
                  </div>
                )
              }
              return null
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default WorkflowStepper
