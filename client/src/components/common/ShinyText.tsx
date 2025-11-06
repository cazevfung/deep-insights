import React from 'react'
import { motion } from 'framer-motion'

interface ShinyTextProps {
  children: React.ReactNode
  variant?: 'hover' | 'focus' | 'once' | 'pulse' | 'active' | 'primary' | 'success' | 'error'
  className?: string
  trigger?: 'hover' | 'focus' | 'always' | 'once'
  duration?: number
  delay?: number
  as?: 'span' | 'div' | 'p' | 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6'
}

const ShinyText: React.FC<ShinyTextProps> = ({
  children,
  variant = 'hover',
  className = '',
  trigger = 'hover',
  duration = 2,
  delay = 0,
  as = 'span',
}) => {
  const baseClasses = `shiny-text shiny-text-${variant}`
  const combinedClasses = `${baseClasses} ${className}`.trim()

  // For programmatic control with Framer Motion
  if (trigger === 'always') {
    const MotionComponent = motion[as] as any
    return (
      <MotionComponent
        className={combinedClasses}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay, duration: duration / 2 }}
      >
        {children}
      </MotionComponent>
    )
  }

  const Component = as
  return (
    <Component className={combinedClasses}>
      {children}
    </Component>
  )
}

export default ShinyText


