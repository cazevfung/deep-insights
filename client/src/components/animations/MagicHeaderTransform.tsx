import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface MagicHeaderTransformProps {
  comprehensiveTopic: string | null
}

const DEFAULT_TEXT = 'Deep Insights'

const MagicHeaderTransform: React.FC<MagicHeaderTransformProps> = ({ comprehensiveTopic }) => {
  const [displayText, setDisplayText] = useState(DEFAULT_TEXT)
  const [isAnimating, setIsAnimating] = useState(false)
  const [showShimmer, setShowShimmer] = useState(false)
  const timeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([])

  const clearAllTimeouts = () => {
    timeoutsRef.current.forEach((timeoutId) => clearTimeout(timeoutId))
    timeoutsRef.current = []
  }

  useEffect(() => {
    const nextText = comprehensiveTopic?.trim() ? comprehensiveTopic : DEFAULT_TEXT
    if (nextText === displayText) {
      return
    }

    clearAllTimeouts()

    setIsAnimating(true)

    // Sequence: fade out → shimmer → fade in
    const fadeTimeout = setTimeout(() => {
      setShowShimmer(true)
      const shimmerTimeout = setTimeout(() => {
        setShowShimmer(false)
        setDisplayText(nextText)
        const finishTimeout = setTimeout(() => {
          setIsAnimating(false)
        }, 400)
        timeoutsRef.current.push(finishTimeout)
      }, 200)
      timeoutsRef.current.push(shimmerTimeout)
    }, 300)

    timeoutsRef.current.push(fadeTimeout)

    return () => {
      clearAllTimeouts()
    }
  }, [comprehensiveTopic, displayText])

  return (
    <div className="relative">
      <AnimatePresence mode="wait">
        <motion.h2
          key={displayText}
          initial={isAnimating ? { opacity: 0, scale: 0.95, filter: 'blur(2px)' } : false}
          animate={{ 
            opacity: 1, 
            scale: 1, 
            filter: 'blur(0px)',
          }}
          exit={{ opacity: 0, scale: 0.95, filter: 'blur(2px)' }}
          transition={{
            duration: isAnimating ? 0.4 : 0.3,
            ease: isAnimating ? 'easeIn' : 'easeInOut',
          }}
          className="text-lg font-semibold text-neutral-black"
        >
          {displayText}
        </motion.h2>
      </AnimatePresence>
      
      {/* Shimmer effect overlay */}
      {showShimmer && (
        <motion.div
          initial={{ opacity: 0, boxShadow: '0 0 0 rgba(254, 199, 74, 0)' }}
          animate={{ 
            opacity: 1, 
            boxShadow: '0 0 20px rgba(254, 199, 74, 0.5)',
          }}
          exit={{ opacity: 0, boxShadow: '0 0 0 rgba(254, 199, 74, 0)' }}
          transition={{ duration: 0.2 }}
          className="absolute inset-0 pointer-events-none rounded"
          style={{
            background: 'linear-gradient(90deg, transparent, rgba(254, 199, 74, 0.3), transparent)',
          }}
        />
      )}
    </div>
  )
}

export default MagicHeaderTransform

