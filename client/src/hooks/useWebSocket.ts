import { useEffect, useRef, useMemo } from 'react'
import { useWorkflowStore } from '../stores/workflowStore'
import { useUiStore } from '../stores/uiStore'

// Global WebSocket connection manager to prevent multiple connections per batchId
const wsConnections = new Map<string, WebSocket>()
const wsConnectionRefs = new Map<string, Set<React.RefObject<WebSocket | null>>>()

export const useWebSocket = (batchId: string) => {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 5
  
  // Stabilize batchId to prevent unnecessary reconnections
  const stableBatchId = useMemo(() => batchId, [batchId])

  const {
    updateProgress,
    updateScrapingStatus,
    updateScrapingItem,
    updateScrapingItemProgress,
    updateResearchAgentStatus,
    setGoals,
    setPlan,
    setSynthesizedGoal,
    appendStreamToken,
    clearStreamBuffer,
    addPhase3Step,
    setFinalReport,
    addError,
    setCancelled,
  } = useWorkflowStore()

  const { addNotification } = useUiStore()

  useEffect(() => {
    let isManualClose = false
    let reconnectTimeout: NodeJS.Timeout | null = null

    // Cleanup function to close WebSocket when batchId changes or component unmounts
    const cleanup = () => {
      isManualClose = true
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout)
        reconnectTimeout = null
      }
      
      // Remove this ref from the connection manager
      if (stableBatchId && wsConnectionRefs.has(stableBatchId)) {
        const refs = wsConnectionRefs.get(stableBatchId)!
        refs.delete(wsRef)
        
        // Only close connection if no other components are using it
        // AND the connection is not currently waiting for user input
        if (refs.size === 0) {
          const globalWs = wsConnections.get(stableBatchId)
          if (globalWs) {
            // Check if connection is in a critical state (waiting for user input)
            // Don't close if connection is OPEN and might be needed
            const isOpen = globalWs.readyState === WebSocket.OPEN
            if (isOpen) {
              // Delay closing to allow for reconnection from other components
              // This prevents premature closure during component remounting
              console.log(`Deferring WebSocket closure for batchId ${stableBatchId} (connection still open, may be needed)`)
              setTimeout(() => {
                // Only close if still no refs and connection is still open
                const currentRefs = wsConnectionRefs.get(stableBatchId)
                const currentWs = wsConnections.get(stableBatchId)
                if ((!currentRefs || currentRefs.size === 0) && currentWs && currentWs.readyState === WebSocket.OPEN) {
                  try {
                    console.log(`Closing WebSocket connection for batchId ${stableBatchId} (delayed cleanup)`)
                    currentWs.close(1000, 'Last component unmounting (delayed)')
                  } catch (error) {
                    console.error('Error closing WebSocket:', error)
                  }
                  wsConnections.delete(stableBatchId)
                  wsConnectionRefs.delete(stableBatchId)
                }
              }, 1000) // 1 second delay to allow reconnection
            } else {
              // Connection is not open, safe to close immediately
              try {
                console.log(`Closing WebSocket connection for batchId ${stableBatchId} (last component unmounting, connection not open)`)
                globalWs.close(1000, 'Last component unmounting')
              } catch (error) {
                console.error('Error closing WebSocket:', error)
              }
              wsConnections.delete(stableBatchId)
              wsConnectionRefs.delete(stableBatchId)
            }
          }
        } else {
          // Other components still using this connection, don't close
          console.log(`Keeping WebSocket connection for batchId ${stableBatchId} (${refs.size} other components still using it)`)
        }
      }
      
      // Clear local reference but don't close if others are using it
      wsRef.current = null
    }

    // Validate batchId before connecting
    if (!stableBatchId || stableBatchId.trim() === '') {
      console.debug('WebSocket: batchId not set yet, closing any existing connection')
      cleanup()
      return cleanup
    }

    // Validate batchId format (basic check)
    if (stableBatchId.length < 3) {
      console.warn('WebSocket: batchId format invalid, closing any existing connection')
      cleanup()
      addNotification('批次ID格式无效，无法连接', 'warning')
      return cleanup
    }
    
    // Check if there's already an active connection for this batchId
    const existingConnection = wsConnections.get(stableBatchId)
    if (existingConnection && existingConnection.readyState === WebSocket.OPEN) {
      // Reuse existing connection
      console.log(`Reusing existing WebSocket connection for batchId ${stableBatchId}`)
      wsRef.current = existingConnection
      
      // Register this ref
      if (!wsConnectionRefs.has(stableBatchId)) {
        wsConnectionRefs.set(stableBatchId, new Set())
      }
      wsConnectionRefs.get(stableBatchId)!.add(wsRef)
      
      return cleanup
    }

    const connect = () => {
      // Don't reconnect if manually closed or component unmounted
      if (isManualClose) {
        return
      }

      try {
        // Use relative URL to go through Vite proxy (which forwards to localhost:3001)
        // Construct WebSocket URL based on current window location to use Vite proxy
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsUrl = `${protocol}//${window.location.host}/ws/${stableBatchId}`
        console.log(`Connecting to WebSocket: ${wsUrl}`)
        const ws = new WebSocket(wsUrl)
        
        // Register this connection in the global manager
        wsConnections.set(stableBatchId, ws)
        if (!wsConnectionRefs.has(stableBatchId)) {
          wsConnectionRefs.set(stableBatchId, new Set())
        }
        wsConnectionRefs.get(stableBatchId)!.add(wsRef)

        ws.onopen = () => {
          console.log('WebSocket connected')
          reconnectAttemptsRef.current = 0
          addNotification('已连接到服务器', 'success')
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            console.log('WebSocket message received:', data.type, data)
            console.log('Full WebSocket message data:', JSON.stringify(data, null, 2))
            handleMessage(data)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error, 'Raw data:', event.data)
          }
        }

        ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          // Don't show error notification on every error (it's noisy)
          // Only show on first error or after multiple failures
          if (reconnectAttemptsRef.current === 0) {
            addNotification('WebSocket连接错误，正在重试...', 'warning')
          }
        }

        ws.onclose = (event) => {
          console.log('WebSocket closed', event.code, event.reason)
          
          // Clean up global connection map
          if (wsConnections.get(stableBatchId) === ws) {
            wsConnections.delete(stableBatchId)
            wsConnectionRefs.delete(stableBatchId)
          }
          
          // Don't reconnect if manually closed
          if (isManualClose) {
            return
          }

          // Don't reconnect if it's a normal close (code 1000)
          if (event.code === 1000) {
            console.log('WebSocket closed normally')
            return
          }

          // Reconnect with exponential backoff
          if (reconnectAttemptsRef.current < maxReconnectAttempts) {
            reconnectAttemptsRef.current++
            const baseDelay = 1000  // 1 second
            const exponentialDelay = baseDelay * Math.pow(2, reconnectAttemptsRef.current - 1)
            const maxDelay = 30000  // Max 30 seconds
            const delay = Math.min(exponentialDelay, maxDelay)
            
            console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`)
            
            if (reconnectAttemptsRef.current === 1) {
              addNotification('连接断开，正在重连...', 'warning')
            }
            
            reconnectTimeout = setTimeout(() => {
              if (!isManualClose) {
                console.log(`Reconnecting (attempt ${reconnectAttemptsRef.current})...`)
                connect()
              }
            }, delay)
          } else {
            console.error('WebSocket: Max reconnection attempts reached')
            addNotification('连接中断，请刷新页面重试', 'error')
          }
        }

        wsRef.current = ws
      } catch (error) {
        console.error('Failed to create WebSocket:', error)
        addNotification('无法创建WebSocket连接，请检查服务器是否运行', 'error')
      }
    }

    const handleMessage = (data: any) => {
      switch (data.type) {
        case 'connected':
          // WebSocket connection confirmation
          console.log('WebSocket connected:', data.message)
          break

        case 'workflow:progress':
          updateProgress(data.progress || 0)
          // Also update currentAction if message is provided
          if (data.message) {
            updateResearchAgentStatus({
              currentAction: data.message,
            })
          }
          break

        case 'scraping:status':
          // Normalize status format in items (handle both snake_case and kebab-case)
          const normalizedItems = (data.items || []).map((item: any) => ({
            ...item,
            status: item.status === 'in_progress' ? 'in-progress' : item.status,
          }))
          updateScrapingStatus({
            total: data.total || 0,
            completed: data.completed || 0,
            failed: data.failed || 0,
            inProgress: data.inProgress || 0,
            items: normalizedItems,
          })
          break

        case 'scraping:item_progress':
          // Real-time progress update for a specific link
          updateScrapingItemProgress(
            data.link_id,
            data.url,
            {
              link_id: data.link_id,
              url: data.url,
              current_stage: data.stage,
              stage_progress: data.stage_progress,
              overall_progress: data.overall_progress,
              status_message: data.message,
              source: data.metadata?.source,
              bytes_downloaded: data.metadata?.bytes_downloaded,
              total_bytes: data.metadata?.total_bytes,
              status: 'in-progress',
            }
          )
          break

        case 'scraping:item_update':
          // Status change (completed/failed)
          updateScrapingItemProgress(
            data.link_id,
            data.url,
            {
              link_id: data.link_id,
              url: data.url,
              status: data.status === 'in_progress' ? 'in-progress' : data.status,
              error: data.error,
              word_count: data.metadata?.word_count,
              source: data.metadata?.source,
              completed_at: data.timestamp,
            }
          )
          break

        case 'research:phase_change':
          updateResearchAgentStatus({
            phase: data.phase,
            currentAction: data.message,
          })
          break

        case 'research:stream_start':
          clearStreamBuffer()
          break

        case 'research:stream_token':
          appendStreamToken(data.token)
          break

        case 'research:stream_end':
          // Handle stream end if needed
          break

        case 'research:user_input_required':
          updateResearchAgentStatus({
            waitingForUser: true,
            userInputRequired: {
              type: data.type,
              prompt_id: data.prompt_id,
              data: {
                prompt: data.prompt,
                choices: data.choices,
              },
            },
          })
          break

        case 'research:goals':
          setGoals(data.goals || [])
          break

        case 'research:plan':
        case 'research:plan_confirmation':
          setPlan(data.plan || [])
          if (data.type === 'research:plan_confirmation') {
            updateResearchAgentStatus({
              waitingForUser: true,
              userInputRequired: {
                type: 'plan_confirmation',
                data: {
                  plan: data.plan,
                },
              },
            })
          }
          break

        case 'research:synthesized_goal':
          setSynthesizedGoal(data.synthesized_goal || null)
          break

        case 'workflow:complete':
          updateResearchAgentStatus({
            currentAction: '工作流完成',
          })
          addNotification('研究已完成！', 'success')
          break

        case 'phase3:step_complete':
          // Add safeguard: validate step data before processing
          // The addPhase3Step function will handle deduplication, but this prevents invalid data
          if (data.stepData?.step_id !== undefined) {
            addPhase3Step(data.stepData)
          } else {
            console.warn('Received phase3:step_complete message without step_id', data)
          }
          break

        case 'phase4:report_ready':
          setFinalReport({
            content: data.report,
            generatedAt: new Date().toISOString(),
            status: 'ready',
          })
          addNotification('最终报告已生成', 'success')
          break

        case 'scraping:cancelled':
          setCancelled(true, {
            cancelled_at: data.timestamp,
            reason: data.reason,
            state_at_cancellation: data.state,
          })
          addNotification(`已取消: ${data.reason}`, 'warning')
          break

        case 'error':
          addError(data.phase || 'unknown', data.message)
          addNotification(data.message, 'error')
          break

        default:
          console.log('Unknown WebSocket message type:', data.type)
      }
    }

    connect()

    // Return cleanup function - will be called when batchId changes or component unmounts
    return cleanup
  }, [stableBatchId])

  const sendMessage = (type: string, data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify({ type, ...data }))
      } catch (error) {
        console.error('Failed to send WebSocket message:', error)
        addNotification('无法发送消息，请重试', 'error')
      }
    } else {
      console.warn('WebSocket is not connected. Cannot send message:', type)
      addNotification('WebSocket未连接，无法发送消息', 'warning')
    }
  }

  return { sendMessage }
}


