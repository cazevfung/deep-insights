import React, { useMemo } from 'react'

interface Checkpoint {
  id: string
  label: string
  completed: boolean
}

interface CheckpointProgressBarProps {
  checkpoints: Checkpoint[]
  currentCheckpointIndex?: number
  className?: string
}

const CheckpointProgressBar: React.FC<CheckpointProgressBarProps> = ({
  checkpoints,
  currentCheckpointIndex,
  className = '',
}) => {
  // Calculate the progress line width
  const progressWidth = useMemo(() => {
    if (checkpoints.length === 0) return 0
    
    // Find the last completed checkpoint index
    let lastCompletedIndex = -1
    for (let i = checkpoints.length - 1; i >= 0; i--) {
      if (checkpoints[i].completed) {
        lastCompletedIndex = i
        break
      }
    }
    
    // If all checkpoints are completed
    if (checkpoints.every((cp) => cp.completed)) {
      return 100
    }
    
    // If we have completed checkpoints, extend line to the last completed one
    if (lastCompletedIndex >= 0) {
      // Calculate percentage: position of last completed checkpoint
      // There are (checkpoints.length - 1) segments between checkpoints
      const segments = checkpoints.length - 1
      if (segments === 0) return 100
      
      // Position of the last completed checkpoint as percentage
      // For the first checkpoint (index 0), show minimal progress (2%)
      if (lastCompletedIndex === 0) {
        return 2
      }
      
      return (lastCompletedIndex / segments) * 100
    }
    
    // No completed checkpoints yet - show progress to current active checkpoint if any
    if (currentCheckpointIndex !== undefined && currentCheckpointIndex >= 0) {
      const segments = checkpoints.length - 1
      if (segments === 0) return 0
      // Show partial progress to current checkpoint (maybe 10% of the segment)
      return (currentCheckpointIndex / segments) * 100
    }
    
    return 0
  }, [checkpoints, currentCheckpointIndex])

  // Check if session is actively processing (has active checkpoint)
  const isProcessing = currentCheckpointIndex !== undefined && 
    currentCheckpointIndex >= 0 && 
    !checkpoints[currentCheckpointIndex]?.completed

  return (
    <div className={`${className}`}>
      <div className="relative flex items-start justify-start py-3">
        {/* Background track line */}
        <div 
          className="absolute left-0 right-0 h-0.5 bg-gray-200"
          style={{ 
            top: '50%', 
            transform: 'translateY(-50%)',
            left: '10px',
            right: '10px',
          }} 
        />
        
        {/* Progress line with animation */}
        {progressWidth > 0 && (
          <div className="relative">
            <div
              className="absolute h-0.5 bg-primary-500 transition-all duration-500 ease-out"
              style={{
                left: '10px',
                width: `${progressWidth}%`,
                top: '50%',
                transform: 'translateY(-50%)',
                maxWidth: 'calc(100% - 20px)',
              }}
            />
            {/* Animated shimmer effect when processing */}
            {isProcessing && (
              <div
                className="absolute h-0.5 bg-primary-400 opacity-60 animate-pulse"
                style={{
                  left: '10px',
                  width: `${progressWidth}%`,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  maxWidth: 'calc(100% - 20px)',
                  animation: 'shimmer 2s ease-in-out infinite',
                }}
              />
            )}
          </div>
        )}

        {/* Checkpoints */}
        {checkpoints.map((checkpoint, index) => {
          const isCompleted = checkpoint.completed
          const isActive = currentCheckpointIndex === index && !isCompleted
          const totalCheckpoints = checkpoints.length

          return (
            <div
              key={checkpoint.id}
              className="relative flex flex-col items-center z-10"
              style={{ minWidth: totalCheckpoints > 5 ? '70px' : '80px' }}
            >
              {/* Checkpoint circle */}
              <div
                className={`relative flex items-center justify-center transition-all duration-300 mb-2 ${
                  isCompleted
                    ? 'bg-primary-500'
                    : isActive
                    ? 'bg-primary-400'
                    : 'bg-gray-300'
                }`}
                style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                }}
              >
                {/* Inner white dot for completed checkpoints */}
                {isCompleted && (
                  <div
                    className="bg-white rounded-full"
                    style={{
                      width: '4px',
                      height: '4px',
                    }}
                  />
                )}
                {/* Pulse animation for active checkpoint */}
                {isActive && (
                  <div
                    className="absolute inset-0 rounded-full bg-primary-400 opacity-75 animate-ping"
                    style={{
                      width: '12px',
                      height: '12px',
                    }}
                  />
                )}
              </div>

              {/* Checkpoint label */}
              <div
                className={`text-center transition-colors duration-200 ${
                  isCompleted
                    ? 'text-primary-600'
                    : isActive
                    ? 'text-primary-500'
                    : 'text-gray-400'
                }`}
                style={{
                  fontSize: totalCheckpoints > 5 ? '8px' : '9px',
                  lineHeight: '1.3',
                  maxWidth: totalCheckpoints > 5 ? '60px' : '70px',
                  fontWeight: isCompleted || isActive ? 500 : 400,
                  marginTop: '4px',
                }}
              >
                {checkpoint.label}
              </div>
            </div>
          )
        })}
      </div>
      
      {/* Add keyframe animation for shimmer effect */}
      <style>{`
        @keyframes shimmer {
          0%, 100% {
            opacity: 0.3;
            transform: translateY(-50%) translateX(0);
          }
          50% {
            opacity: 0.7;
            transform: translateY(-50%) translateX(10px);
          }
        }
      `}</style>
    </div>
  )
}

export default CheckpointProgressBar

