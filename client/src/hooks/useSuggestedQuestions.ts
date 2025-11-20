import { useState, useEffect, useCallback, useRef } from 'react'
import { apiService } from '../services/api'
import { ConversationMessage } from '../stores/workflowStore'

interface UseSuggestedQuestionsOptions {
  batchId: string | null
  sessionId: string | null
  conversationMessages: ConversationMessage[]
  enabled?: boolean
  debounceMs?: number
}

interface UseSuggestedQuestionsResult {
  questions: string[]
  loading: boolean
  error: Error | null
  refresh: () => void
}

const CACHE_TTL = 30000 // 30 seconds
const DEFAULT_DEBOUNCE = 500 // 500ms

interface CacheEntry {
  questions: string[]
  timestamp: number
  conversationHash: string
}

const conversationHash = (messages: ConversationMessage[]): string => {
  // Hash based on last 5 messages
  const lastMessages = messages.slice(-5)
  return lastMessages.map(m => `${m.role}:${m.content.substring(0, 50)}`).join('|')
}

const getLatestAssistantMessage = (messages: ConversationMessage[]): ConversationMessage | undefined => {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const msg = messages[i]
    if (msg.role === 'assistant') {
      return msg
    }
  }
  return undefined
}

export const useSuggestedQuestions = ({
  batchId,
  sessionId,
  conversationMessages,
  enabled = true,
  debounceMs = DEFAULT_DEBOUNCE,
}: UseSuggestedQuestionsOptions): UseSuggestedQuestionsResult => {
  const [questions, setQuestions] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  
  const cacheRef = useRef<Map<string, CacheEntry>>(new Map())
  const debounceTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const lastCompletedAssistantRef = useRef<string | null>(null)

  const fetchSuggestions = useCallback(async () => {
    if (!batchId || !enabled) {
      setQuestions([])
      return
    }

    // Check cache
    const hash = conversationHash(conversationMessages)
    const cacheKey = `${batchId}:${sessionId || 'none'}:${hash}`
    const cached = cacheRef.current.get(cacheKey)
    
    if (cached && Date.now() - cached.timestamp < CACHE_TTL && cached.conversationHash === hash) {
      setQuestions(cached.questions)
      return
    }

    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    const controller = new AbortController()
    abortControllerRef.current = controller

    setLoading(true)
    setError(null)

    try {
      const response = await apiService.getSuggestedQuestions(
        {
          batch_id: batchId,
          session_id: sessionId ?? undefined,
          conversation_context: conversationMessages.slice(-10).map(msg => ({
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp,
          })),
        },
        { signal: controller.signal }
      )

      if (abortControllerRef.current?.signal.aborted) {
        return
      }

      const questionsList = response.questions || []
      setQuestions(questionsList)

      // Update cache
      cacheRef.current.set(cacheKey, {
        questions: questionsList,
        timestamp: Date.now(),
        conversationHash: hash,
      })

      // Clean old cache entries (keep last 10)
      if (cacheRef.current.size > 10) {
        const entries = Array.from(cacheRef.current.entries())
        entries.sort((a, b) => b[1].timestamp - a[1].timestamp)
        cacheRef.current.clear()
        entries.slice(0, 10).forEach(([key, value]) => {
          cacheRef.current.set(key, value)
        })
      }
    } catch (err) {
      if (abortControllerRef.current?.signal.aborted) {
        return
      }
      const error = err instanceof Error ? err : new Error('Failed to fetch suggested questions')
      setError(error)
      setQuestions([])
      console.error('Failed to fetch suggested questions:', err)
    } finally {
      if (!abortControllerRef.current?.signal.aborted) {
        setLoading(false)
      }
    }
  }, [batchId, sessionId, conversationMessages, enabled])

  const refresh = useCallback(() => {
    // Clear debounce
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current)
      debounceTimeoutRef.current = null
    }

    // Debounce the fetch
    debounceTimeoutRef.current = setTimeout(() => {
      fetchSuggestions()
    }, debounceMs)
  }, [fetchSuggestions, debounceMs])

  const latestAssistantMessage = getLatestAssistantMessage(conversationMessages)

  useEffect(() => {
    if (!batchId || !enabled) {
      return
    }
    if (!latestAssistantMessage) {
      return
    }
    if (latestAssistantMessage.status !== 'completed') {
      return
    }
    if (lastCompletedAssistantRef.current === latestAssistantMessage.id) {
      return
    }

    lastCompletedAssistantRef.current = latestAssistantMessage.id
    refresh()
  }, [batchId, enabled, latestAssistantMessage?.id, latestAssistantMessage?.status, refresh])

  useEffect(() => {
    lastCompletedAssistantRef.current = null
    cacheRef.current.clear()
  }, [batchId, sessionId])

  useEffect(() => {
    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current)
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  return {
    questions,
    loading,
    error,
    refresh,
  }
}

