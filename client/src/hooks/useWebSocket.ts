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
    startStream,
    appendStreamToken,
    completeStream,
    setStreamError,
    setActiveStream,
    pinStream,
    unpinStream,
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

        case 'summarization:progress':
          // Update summarization progress
          updateResearchAgentStatus({
            summarizationProgress: {
              currentItem: data.current_item || 0,
              totalItems: data.total_items || 0,
              linkId: data.link_id || '',
              stage: data.stage || '',
              progress: data.progress || 0,
              message: data.message || '',
            },
            // Also update currentAction to show the message
            currentAction: data.message || null,
          })
          break

        case 'batch:initialized':
          // Store expected total from batch initialization
          // This is the TOTAL scraping processes that need to run, not just started ones
          // Backend sends expected_total (snake_case), we map to expectedTotal (camelCase)
          console.log('🔵 Received batch:initialized message:', {
            expected_total: data.expected_total,
            total_processes: data.total_processes,
            all_keys: Object.keys(data),
          })
          const expectedTotalFromInit = data.expected_total || data.total_processes
          // Only update if we have a valid value (> 0)
          if (expectedTotalFromInit && expectedTotalFromInit > 0) {
            console.log('✅ Setting expectedTotal (camelCase) from expected_total (snake_case):', expectedTotalFromInit)
            updateScrapingStatus({
              expectedTotal: expectedTotalFromInit,  // Map snake_case to camelCase
            })
            console.log('✅ Batch initialized with expected total:', expectedTotalFromInit)
          } else {
            console.error('❌ batch:initialized message missing expected_total or total_processes, or value is 0:', {
              expected_total: data.expected_total,
              total_processes: data.total_processes,
              calculated: expectedTotalFromInit,
              full_data: data,
            })
          }
          break

        case 'scraping:status':
          // Normalize status format in items (handle both snake_case and kebab-case)
          const normalizedItems = (data.items || []).map((item: any) => ({
            ...item,
            status: item.status === 'in_progress' ? 'in-progress' : item.status,
          }))
          
          // IMPORTANT: Update expectedTotal from scraping:status if available
          // This ensures we get the correct total even if batch:initialized was missed
          // Only update if we have a valid value (> 0), otherwise preserve existing
          // Use expected_total (standardized field name), fallback to total_processes (deprecated) for backward compatibility
          const expectedTotalFromStatus = data.expected_total || data.total_processes || null
          
          const statusUpdate: any = {
            total: data.total || 0,  // Keep for backward compatibility (started processes)
            completed: data.completed || 0,
            failed: data.failed || 0,
            inProgress: data.inProgress || 0,
            items: normalizedItems,
            // Use completion rate and flags from backend (calculated against expected_total)
            completionRate: data.completion_rate ?? 0.0,
            is100Percent: data.is_100_percent ?? false,
            canProceedToResearch: data.can_proceed_to_research ?? false,
          }
          
          // Only include expectedTotal if we have a valid value (> 0)
          // Backend sends expected_total (snake_case), we map to expectedTotal (camelCase)
          if (expectedTotalFromStatus && expectedTotalFromStatus > 0) {
            statusUpdate.expectedTotal = expectedTotalFromStatus  // Map snake_case to camelCase
            console.log('✅ Updating expectedTotal (camelCase) from expected_total (snake_case):', expectedTotalFromStatus)
          } else {
            console.warn('⚠️ scraping:status message missing expected_total or value is 0:', {
              expected_total: data.expected_total,
              total_processes: data.total_processes,
              calculated: expectedTotalFromStatus,
              will_not_update: true,
            })
          }
          
          updateScrapingStatus(statusUpdate)
          console.log('🔵 Received scraping:status:', {
            total: data.total,
            expected_total: data.expected_total,  // Backend field (snake_case)
            total_processes: data.total_processes,
            expectedTotalFromStatus,
            will_update_expectedTotal: expectedTotalFromStatus && expectedTotalFromStatus > 0,
            completed: data.completed,
            completion_rate: data.completion_rate,
            is_100_percent: data.is_100_percent,
          })
          break

        case 'scraping:all_complete_confirmed': {
          // Determine the most reliable expected total value available
          const completionCandidates = [
            data.expected_total,
            data.total_final,
            data.registered_count,
            (data.completed_count ?? 0) + (data.failed_count ?? 0),
          ].filter((value) => typeof value === 'number' && value > 0)
          const resolvedExpectedTotal = completionCandidates.length > 0 ? completionCandidates[0] : 0
          const totalFinal = data.total_final ?? ((data.completed_count ?? 0) + (data.failed_count ?? 0))
          const pendingCount = data.pending_count ?? 0
          const inProgressCount = data.in_progress_count ?? 0
          const completionRateFromMessage = data.completion_rate ?? (resolvedExpectedTotal > 0 ? totalFinal / resolvedExpectedTotal : 0)
          const isFullyComplete = (data.is_100_percent ?? false) || (
            resolvedExpectedTotal > 0 &&
            totalFinal >= resolvedExpectedTotal &&
            pendingCount === 0 &&
            inProgressCount === 0
          )

          updateScrapingStatus({
            expectedTotal: resolvedExpectedTotal,
            total: resolvedExpectedTotal || totalFinal,
            completed: data.completed_count ?? 0,
            failed: data.failed_count ?? 0,
            inProgress: inProgressCount,
            completionRate: completionRateFromMessage,
            is100Percent: isFullyComplete,
            canProceedToResearch: Boolean(data.confirmed && isFullyComplete),
          })

          console.log('✅ Received scraping:all_complete_confirmed:', {
            confirmed: data.confirmed,
            expected_total: data.expected_total,
            resolvedExpectedTotal,
            total_final: totalFinal,
            completion_rate: completionRateFromMessage,
            isFullyComplete,
          })

          if (data.confirmed && isFullyComplete) {
            addNotification('抓取任务全部完成，可以进入研究阶段', 'success')
          } else {
            console.warn('⚠️ Scraping completion confirmation received but not fully confirmed:', data)
          }

          break
        }

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

        case 'research:stream_start': {
          const streamId = data.stream_id || `stream:${Date.now()}`
          startStream(streamId, {
            phase: data.phase ?? null,
            metadata: data.metadata ?? null,
            startedAt: data.timestamp,
          })
          if (data.active === false) {
            setActiveStream(null)
          } else {
            setActiveStream(streamId)
          }
          break
        }

        case 'research:stream_token':
          if (data.stream_id) {
            appendStreamToken(data.stream_id, data.token || '')
          } else {
            console.warn('Received stream token without stream_id, ignoring')
          }
          break

        case 'research:stream_end': {
          if (data.stream_id) {
            completeStream(data.stream_id, {
              metadata: data.metadata,
              endedAt: data.timestamp,
            })
          }
          break
        }

        case 'research:stream_error': {
          if (data.stream_id) {
            setStreamError(data.stream_id, data.error || 'unknown error')
          }
          break
        }

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


