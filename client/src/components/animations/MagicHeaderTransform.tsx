import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface MagicHeaderTransformProps {
  comprehensiveTopic: string | null
}

const MagicHeaderTransform: React.FC<MagicHeaderTransformProps> = ({ comprehensiveTopic }) => {
  const [displayText, setDisplayText] = useState('Deep Insights')
  const [isAnimating, setIsAnimating] = useState(false)
  const [showShimmer, setShowShimmer] = useState(false)

  useEffect(() => {
    if (comprehensiveTopic && displayText === 'Deep Insights') {
      setIsAnimating(true)
      
      // Sequence: fade out → shimmer → fade in
      // Step 1: Fade out (300ms)
      setTimeout(() => {
        setShowShimmer(true)
        // Step 2: Shimmer effect (200ms)
        setTimeout(() => {
          setShowShimmer(false)
          setDisplayText(comprehensiveTopic)
          // Step 3: Fade in (400ms)
          setTimeout(() => {
            setIsAnimating(false)
          }, 400)
        }, 200)
      }, 300)
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

