import React, { useEffect, useRef, useState } from 'react'
import Card from '../components/common/Card'
import Phase3StatusBanner from '../components/phase3/Phase3StatusBanner'
import Phase3StepList from '../components/phase3/Phase3StepList'
import { usePhase3Steps } from '../hooks/usePhase3Steps'

const Phase3SessionPage: React.FC = () => {
  const phase3State = usePhase3Steps()
  const containerRef = useRef<HTMLDivElement>(null)
  const [isAtTop, setIsAtTop] = useState(true)

  useEffect(() => {
    const checkPosition = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        const mainElement = containerRef.current.closest('main')
        
        // Check if container is at or near the top (within Layout's pt-6 padding)
        const atTop = rect.top <= 24 // 24px = 1.5rem = pt-6
        setIsAtTop(atTop)
        
        // Directly manipulate the main element's padding-top
        if (mainElement) {
          if (atTop) {
            mainElement.style.paddingTop = '0'
          } else {
            mainElement.style.paddingTop = '' // Reset to default
          }
        }
      }
    }

    checkPosition()
    const scrollContainer = containerRef.current?.closest('.overflow-y-auto')
    
    if (scrollContainer) {
      scrollContainer.addEventListener('scroll', checkPosition)
      return () => {
        scrollContainer.removeEventListener('scroll', checkPosition)
        // Cleanup: restore padding when component unmounts
        const mainElement = containerRef.current?.closest('main')
        if (mainElement) {
          mainElement.style.paddingTop = ''
        }
      }
    }
  }, [])

  return (
    <div 
      ref={containerRef}
      className="max-w-5xl mx-auto"
    >
      <div 
        className={`transition-all duration-200 ${
          isAtTop 
            ? 'border-b border-gray-300' 
            : ''
        }`}
      >
        <Card 
          className={`!rounded-2xl transition-all duration-200 ${
            isAtTop 
              ? '!shadow-lg !border-0' 
              : '!shadow-xl !border !border-gray-100'
          }`}
        >
        <div className="space-y-4">
          <Phase3StatusBanner rerunState={phase3State.rerunState} reportStale={phase3State.reportStale} />

          {!phase3State.hasAnySteps ? (
            <div className="py-12 text-center">
              <p className="text-gray-400 text-base">还没有分析步骤，研究完成后将显示在这里</p>
            </div>
          ) : (
            <Phase3StepList
              steps={phase3State.steps}
              rerunState={phase3State.rerunState}
              onToggleStep={phase3State.handleToggleStep}
              onRerun={phase3State.handleRerunStep}
            />
          )}
        </div>
      </Card>
      </div>
    </div>
  )
}

export default Phase3SessionPage
