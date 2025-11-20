import axios from 'axios'

const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
})

export interface CreateSessionResponse {
  session_id: string
  created_at?: string | null
}

export interface FormatLinksResponse {
  batch_id: string
  items: Array<{
    url: string
    source: string
    link_id: string
  }>
  total: number
  session_id?: string | null
}

export interface StartWorkflowResponse {
  workflow_id: string
  batch_id: string
  status: string
}

export interface FinalReportResponse {
  content: string
  metadata: {
    batchId: string
    sessionId?: string | null
    generatedAt: string
    topic?: string | null
    originalTopic?: string | null
    componentQuestions?: string[]
    status?: string
  }
  editHistory: Array<{
    version: number
    editedAt: string
    editedBy: 'user' | 'ai'
    changes: string
    contentSnapshot?: string
  }>
  currentVersion: number
  status: 'ready' | 'generating' | 'error'
}

export interface ConversationMessageResponse {
  status: 'ok' | 'queued' | 'context_required'
  user_message_id: string
  assistant_message_id?: string | null
  reply?: string | null
  metadata?: Record<string, unknown> | null
  context_bundle?: Record<string, unknown> | null
  queued_reason?: string | null
  context_request_id?: string | null
  required_context?: Array<Record<string, unknown>> | null
}

export const apiService = {
  /**
   * Create a new research session with required user guidance
   */
  createSession: async (
    userGuidance: string,
    writingStyle?: string
  ): Promise<CreateSessionResponse> => {
    const response = await api.post('/sessions/create', {
      user_guidance: userGuidance,
      writing_style: writingStyle || 'professional'
    })
    return response.data
  },

  /**
   * Format links and create batch
   */
  formatLinks: async (
    urls: string[],
    sessionId?: string
  ): Promise<FormatLinksResponse> => {
    const response = await api.post('/links/format', {
      urls,
      session_id: sessionId || null
    })
    return response.data
  },

  ingestSources: async (formData: FormData): Promise<FormatLinksResponse> => {
    const response = await api.post('/ingestion/sources', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  },

  /**
   * Start workflow
   */
  startWorkflow: async (batchId: string): Promise<StartWorkflowResponse> => {
    const response = await api.post('/workflow/start', { batch_id: batchId })
    return response.data
  },

  /**
   * Get session data
   */
  getSession: async (sessionId: string): Promise<any> => {
    const response = await api.get(`/sessions/${sessionId}`)
    return response.data
  },

  /**
   * Get workflow status
   */
  getWorkflowStatus: async (workflowId: string): Promise<any> => {
    const response = await api.get(`/workflow/status/${workflowId}`)
    return response.data
  },

  /**
   * Cancel workflow
   */
  cancelWorkflow: async (batchId: string, reason?: string): Promise<any> => {
    const response = await api.post('/workflow/cancel', {
      batch_id: batchId,
      reason: reason || 'User cancelled',
    })
    return response.data
  },

  /**
   * Get batch total processes count
   */
  getBatchTotal: async (batchId: string): Promise<any> => {
    const response = await api.get(`/workflow/batch/${batchId}/total`)
    return response.data
  },

  /**
   * Get final report
   */
  getFinalReport: async (batchId: string): Promise<FinalReportResponse> => {
    const response = await api.get(`/reports/${batchId}`)
    return response.data
  },

  /**
   * Get research history list
   */
  getHistory: async (params?: {
    status?: string
    date_from?: string
    date_to?: string
    limit?: number
    offset?: number
  }): Promise<any> => {
    const response = await api.get('/history', { params })
    return response.data
  },

  /**
   * Get session details by batch_id
   * @param batchId - Batch ID to look up
   * @param sessionId - Optional session ID for precise lookup (fixes bug where wrong session is returned)
   */
  getHistorySession: async (batchId: string, sessionId?: string): Promise<any> => {
    const params = sessionId ? { session_id: sessionId } : {}
    const response = await api.get(`/history/${batchId}`, { params })
    return response.data
  },

  /**
   * Resume a session
   */
  resumeSession: async (batchId: string): Promise<any> => {
    const response = await api.post(`/history/${batchId}/resume`)
    return response.data
  },

  /**
   * Delete a session by session_id (preferred - more precise)
   */
  deleteSession: async (sessionId: string): Promise<any> => {
    const response = await api.delete(`/history/session/${sessionId}`)
    return response.data
  },

  /**
   * Export phase report PDF
   */
  exportPhaseReportPdf: async (sessionId: string): Promise<Blob> => {
    const response = await api.get(`/exports/phase-report/${sessionId}`, {
      responseType: 'blob',
    })
    return response.data
  },

  /**
   * Export session to HTML format
   */
  exportSessionHtml: async (
    sessionId: string,
    force?: boolean
  ): Promise<{
    file_path: string
    file_url: string
    cached: boolean
    filename: string
  }> => {
    const response = await api.post(`/exports/session-html/${sessionId}`, null, {
      params: { force: force || false },
    })
    return response.data
  },

  /**
   * Rerun specific phase(s)
   */
  rerunPhase: async (payload: {
    batch_id: string
    session_id: string
    phase: string
    rerun_downstream?: boolean
    user_topic?: string | null
  }): Promise<any> => {
    const response = await api.post('/workflow/restart/phase', payload)
    return response.data
  },

  /**
   * Rerun a single Phase 3 step
   */
  rerunPhase3Step: async (payload: {
    batch_id: string
    session_id: string
    step_id: number
    regenerate_report?: boolean
  }): Promise<any> => {
    const response = await api.post('/workflow/restart/phase3-step', payload)
    return response.data
  },

  /**
   * Send conversation message for right column feedback
   */
  sendConversationMessage: async (payload: {
    batch_id: string
    message: string
    session_id?: string | null
  }): Promise<ConversationMessageResponse> => {
    const response = await api.post('/research/conversation', payload)
    return response.data
  },

  supplyConversationContext: async (payload: {
    batch_id: string
    request_id: string
    items: Array<{
      slot_key?: string | null
      label?: string | null
      content: string
    }>
    provided_by?: string
  }): Promise<ConversationMessageResponse> => {
    const response = await api.post('/research/conversation/context-supply', payload)
    return response.data
  },

  /**
   * Get suggested questions for conversation
   */
  getSuggestedQuestions: async (
    payload: {
      batch_id: string
      session_id?: string | null
      conversation_context: Array<{
        role: 'user' | 'assistant'
        content: string
        timestamp: string
      }>
    },
    options?: { signal?: AbortSignal }
  ): Promise<{
    questions: string[]
    generated_at: string
    model_used: string
  }> => {
    const response = await api.post('/research/conversation/suggest-questions', payload, {
      signal: options?.signal,
    })
    return response.data
  },
}

export default api


