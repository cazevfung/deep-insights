import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useLocation } from 'react-router-dom'

interface AnimatedPageProps {
  children: React.ReactNode
}

/**
 * Wrapper component for page transitions
 * Uses different animation styles based on navigation direction
 */
const AnimatedPage: React.FC<AnimatedPageProps> = ({ children }) => {
  const location = useLocation()

  // Animation variants for different directions
  const pageVariants = {
    initial: {
      opacity: 0,
      x: 0,
    },
    enter: {
      opacity: 1,
      x: 0,
    },
    exit: {
      opacity: 0,
      x: 0,
    },
  }

  const pageTransition = {
    type: 'tween',
    ease: 'easeInOut',
    duration: 0.3,
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial="initial"
        animate="enter"
        exit="exit"
        variants={pageVariants}
        transition={pageTransition}
        className="h-full"
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}

export default AnimatedPage


