import React from 'react'

interface CardProps {
  children: React.ReactNode
  className?: string
  title?: string
  subtitle?: string | React.ReactNode
  actions?: React.ReactNode
}

const Card: React.FC<CardProps> = ({
  children,
  className = '',
  title,
  subtitle,
  actions,
}) => {
  return (
    <div className={`card ${className}`}>
      {(title || subtitle || actions) && (
        <div className="mb-4 pb-4 border-b border-neutral-300">
          <div className="flex items-center justify-between">
            <div>
              {title && (
                <h3 className="text-lg font-semibold text-neutral-black">
                  {title}
                </h3>
              )}
              {subtitle && (
                <div className="text-sm text-neutral-400 mt-1">{subtitle}</div>
              )}
            </div>
            {actions && <div className="flex items-center space-x-2">{actions}</div>}
          </div>
        </div>
      )}
      <div>{children}</div>
    </div>
  )
}

export default Card


