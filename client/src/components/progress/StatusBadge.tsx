import React from 'react'
import { Icon, IconName } from '../common/Icon'

type StatusBadgeVariant = 'success' | 'error' | 'warning' | 'info' | 'pending'

interface StatusBadgeProps {
  status: StatusBadgeVariant
  children: React.ReactNode
  className?: string
}

const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  children,
  className = '',
}) => {
  const statusConfig: Record<StatusBadgeVariant, { bg: string; text: string; icon: IconName }> = {
    success: {
      bg: 'bg-supportive-green',
      text: 'text-white',
      icon: 'check',
    },
    error: {
      bg: 'bg-secondary-500',
      text: 'text-white',
      icon: 'x',
    },
    warning: {
      bg: 'bg-supportive-orange',
      text: 'text-white',
      icon: 'warning',
    },
    info: {
      bg: 'bg-supportive-blue',
      text: 'text-white',
      icon: 'info',
    },
    pending: {
      bg: 'bg-neutral-400',
      text: 'text-white',
      icon: 'clock',
    },
  }

  const config = statusConfig[status]

  // Determine shiny text variant based on status
  const getShinyVariant = () => {
    switch (status) {
      case 'success':
        return 'shiny-text-success'
      case 'error':
        return 'shiny-text-error'
      case 'pending':
        return 'shiny-text-active'
      default:
        return 'shiny-text-hover'
    }
  }

  return (
    <span
      className={`inline-flex items-center space-x-1 px-3 py-1 rounded-full text-sm font-medium ${config.bg} ${config.text} ${className}`}
    >
      <Icon name={config.icon} size={14} strokeWidth={2.5} className="flex-shrink-0" />
      <span className={status === 'pending' ? getShinyVariant() : ''}>{children}</span>
    </span>
  )
}

export default StatusBadge


