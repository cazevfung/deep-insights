import React from 'react'

interface ProgressBarProps {
  progress: number // 0-100
  label?: string
  showPercentage?: boolean
  color?: 'primary' | 'secondary' | 'success' | 'danger'
  className?: string
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  label,
  showPercentage = true,
  color = 'primary',
  className = '',
}) => {
  const colorClasses = {
    primary: 'bg-primary-500',
    secondary: 'bg-secondary-500',
    success: 'bg-supportive-green',
    danger: 'bg-secondary-500',
  }

  const clampedProgress = Math.min(100, Math.max(0, progress))

  return (
    <div className={`w-full ${className}`}>
      {(label || showPercentage) && (
        <div className="flex items-center justify-between mb-2">
          {label && (
            <span className="text-sm font-medium text-neutral-black">
              {label}
            </span>
          )}
          {showPercentage && (
            <span className="text-sm text-neutral-400">
              {Math.round(clampedProgress)}%
            </span>
          )}
        </div>
      )}
      <div className="progress-bar">
        <div
          className={`progress-fill ${colorClasses[color]}`}
          style={{ width: `${clampedProgress}%` }}
        />
      </div>
    </div>
  )
}

export default ProgressBar



