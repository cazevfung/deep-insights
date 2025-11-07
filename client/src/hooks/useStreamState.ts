import { useEffect, useMemo, useState } from 'react'
import { useWorkflowStore, StreamState } from '../stores/workflowStore'

interface UseStreamStateOptions {
  /** Milliseconds to keep the streaming indicator active after the last token */
  inactivityTimeout?: number
}

interface StreamStateResult {
  content: string
  streamId: string | null
  phase: string | null
  metadata: Record<string, any> | null
  isStreaming: boolean
  startedAt: string | null
  lastTokenAt: string | null
  endedAt: string | null
  hasContent: boolean
}

const EMPTY_STREAM_STATE: StreamState = {
  isStreaming: false,
  phase: null,
  metadata: null,
  startedAt: null,
  lastTokenAt: null,
  endedAt: null,
}

export const useStreamState = (options: UseStreamStateOptions = {}): StreamStateResult => {
  const { inactivityTimeout = 3000 } = options
  const researchAgentStatus = useWorkflowStore((state) => state.researchAgentStatus)
  const [activeOverride, setActiveOverride] = useState(false)

  const resolvedActiveStreamId = useMemo(() => {
    return (
      researchAgentStatus.streams.activeStreamId ||
      researchAgentStatus.streams.order[0] ||
      null
    )
  }, [researchAgentStatus.streams.activeStreamId, researchAgentStatus.streams.order])

  const activeBuffer = resolvedActiveStreamId
    ? researchAgentStatus.streams.buffers[resolvedActiveStreamId]
    : undefined

  const streamingState = useMemo<StreamState>(() => {
    if (activeBuffer) {
      return {
        isStreaming: activeBuffer.isStreaming,
        phase: activeBuffer.phase ?? null,
        metadata: activeBuffer.metadata ?? null,
        startedAt: activeBuffer.startedAt ?? null,
        lastTokenAt: activeBuffer.lastTokenAt ?? null,
        endedAt: activeBuffer.endedAt ?? null,
      }
    }
    return researchAgentStatus.streamingState || EMPTY_STREAM_STATE
  }, [activeBuffer, researchAgentStatus.streamingState])

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout> | undefined

    if (streamingState.isStreaming) {
      setActiveOverride(false)  // Real streaming takes precedence
      return () => {
        if (timeout) {
          clearTimeout(timeout)
        }
      }
    }

    const lastTokenAt = streamingState.lastTokenAt
    if (lastTokenAt) {
      const elapsed = Date.now() - new Date(lastTokenAt).getTime()
      if (elapsed < inactivityTimeout) {
        setActiveOverride(true)
        timeout = setTimeout(() => setActiveOverride(false), inactivityTimeout - elapsed)
        return () => {
          if (timeout) {
            clearTimeout(timeout)
          }
        }
      }
    }

    setActiveOverride(false)
    return () => {
      if (timeout) {
        clearTimeout(timeout)
      }
    }
  }, [streamingState.isStreaming, streamingState.lastTokenAt, inactivityTimeout])

  const content = activeBuffer?.raw ?? researchAgentStatus.streamBuffer ?? ''
  const phase = streamingState.phase ?? researchAgentStatus.phase ?? null
  const metadata = streamingState.metadata ?? null
  const hasContent = content.length > 0

  return {
    content,
    streamId: resolvedActiveStreamId,
    phase,
    metadata,
    isStreaming: streamingState.isStreaming || activeOverride,
    startedAt: streamingState.startedAt ?? null,
    lastTokenAt: streamingState.lastTokenAt ?? null,
    endedAt: streamingState.endedAt ?? null,
    hasContent,
  }
}
