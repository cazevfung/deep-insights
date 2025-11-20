import React from 'react'
import { useSuggestedQuestions } from '../../hooks/useSuggestedQuestions'
import { ConversationMessage } from '../../stores/workflowStore'

interface SuggestedQuestionsProps {
  batchId: string | null
  sessionId: string | null
  conversationMessages: ConversationMessage[]
  onQuestionClick: (question: string) => void
  disabled?: boolean
}

const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({
  batchId,
  sessionId,
  conversationMessages,
  onQuestionClick,
  disabled = false,
}) => {
  const [clickedQuestion, setClickedQuestion] = React.useState<string | null>(null)
  const processingQuestionsRef = React.useRef<Set<string>>(new Set())

  const { questions, loading, error } = useSuggestedQuestions({
    batchId,
    sessionId,
    conversationMessages,
    enabled: !disabled && !!batchId,
  })

  // Don't render if no questions and not loading
  if (!loading && questions.length === 0 && !error) {
    return null
  }

  const handleQuestionClick = (question: string) => {
    if (disabled || clickedQuestion) {
      console.log('⏸️ Question click ignored (disabled or already clicked)', { disabled, clickedQuestion })
      return
    }
    
    // Synchronous duplicate prevention using ref
    if (processingQuestionsRef.current.has(question)) {
      console.warn('⚠️ DUPLICATE PREVENTION: Question already being processed', question)
      return
    }
    
    console.log('✅ Processing suggested question click:', question)
    processingQuestionsRef.current.add(question)
    setClickedQuestion(question)
    
    onQuestionClick(question)
    
    // Reset after 5 seconds (longer timeout for network lag)
    setTimeout(() => {
      setClickedQuestion(null)
      processingQuestionsRef.current.delete(question)
    }, 5000)
  }

  return (
    <div className="mb-3">
      {loading && (
        <div className="flex items-center gap-2 text-[13px] text-neutral-400">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-neutral-300 border-t-primary-500" />
          <span>正在生成建议问题...</span>
        </div>
      )}

      {error && !loading && (
        <div className="text-[13px] text-warning-500">
          无法加载建议问题
        </div>
      )}

      {!loading && !error && questions.length > 0 && (
        <div className="space-y-2">
          <div className="text-[12px] text-neutral-400 font-medium">
            建议问题
          </div>
          <div className="flex flex-wrap gap-2">
            {questions.map((question, index) => (
              <button
                key={index}
                type="button"
                onClick={() => handleQuestionClick(question)}
                disabled={disabled || clickedQuestion === question}
                className="px-3 py-1.5 rounded-lg border border-neutral-200 bg-neutral-50 text-left text-[13px] text-neutral-700 font-medium transition-all hover:bg-neutral-100 hover:border-neutral-300 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default SuggestedQuestions

