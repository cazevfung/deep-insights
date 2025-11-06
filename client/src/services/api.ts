import axios from 'axios'

const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
})

export interface FormatLinksResponse {
  batch_id: string
  items: Array<{
    url: string
    source: string
    link_id: string
  }>
  total: number
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

export const apiService = {
  /**
   * Format links and create batch
   */
  formatLinks: async (urls: string[]): Promise<FormatLinksResponse> => {
    const response = await api.post('/links/format', { urls })
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
   */
  getHistorySession: async (batchId: string): Promise<any> => {
    const response = await api.get(`/history/${batchId}`)
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
   * Delete a session
   */
  deleteSession: async (batchId: string): Promise<any> => {
    const response = await api.delete(`/history/${batchId}`)
    return response.data
  },
}

export default api


