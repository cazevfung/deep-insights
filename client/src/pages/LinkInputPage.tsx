import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight } from 'react-feather'
import { useWorkflowStore } from '../stores/workflowStore'
import { useUiStore } from '../stores/uiStore'
import { apiService } from '../services/api'

interface TextEntry {
  id: string
  label: string
  content: string
}

const LinkInputPage: React.FC = () => {
  const navigate = useNavigate()
  const [urls, setUrls] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasExistingSession, setHasExistingSession] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [textEntries, setTextEntries] = useState<TextEntry[]>([])
  const [textDraft, setTextDraft] = useState('')
  const [textLabel, setTextLabel] = useState('')
  const { 
    batchId, 
    setBatchId, 
    setCurrentPhase, 
    reset,
    validateState,
    scrapingStatus,
    researchAgentStatus,
    phase3Steps,
    finalReport,
    sessionId,  // Get session_id from store
    setSessionId  // Set session_id if returned from backend
  } = useWorkflowStore()
  const { addNotification } = useUiStore()

  // Check if there's an existing session when component mounts
  useEffect(() => {
    const validation = validateState()
    if (!validation.isValid) {
      console.warn('State validation errors detected:', validation.errors)
    }
    
    const hasActiveSession = batchId !== null && (
      scrapingStatus.total > 0 ||
      researchAgentStatus.goals !== null ||
      phase3Steps.length > 0 ||
      finalReport !== null
    )
    setHasExistingSession(hasActiveSession)
  }, [batchId, scrapingStatus, researchAgentStatus, phase3Steps, finalReport, validateState])

  const handleStartNewSession = () => {
    if (window.confirm('确定要开始新会话吗？当前会话的数据将被清除。')) {
      reset()
      setHasExistingSession(false)
      setUrls('')
      setUploadedFiles([])
      setTextEntries([])
      setTextDraft('')
      setTextLabel('')
      setError(null)
      addNotification('会话已清除，可以开始新的研究', 'info')
    }
  }

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files) return
    const files = Array.from(event.target.files)
    setUploadedFiles((prev) => [...prev, ...files])
    event.target.value = ''
  }

  const handleRemoveFile = (index: number) => {
    setUploadedFiles((prev) => prev.filter((_, idx) => idx !== index))
  }

  const handleAddTextEntry = () => {
    if (!textDraft.trim()) {
      addNotification('请输入要添加的文本内容', 'warning')
      return
    }
    const entry: TextEntry = {
      id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}`,
      label: textLabel.trim() || `手动文本 ${textEntries.length + 1}`,
      content: textDraft.trim(),
    }
    setTextEntries((prev) => [...prev, entry])
    setTextDraft('')
    setTextLabel('')
  }

  const handleRemoveTextEntry = (id: string) => {
    setTextEntries((prev) => prev.filter((entry) => entry.id !== id))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    
    // Check if there's an existing session
    if (hasExistingSession) {
      const confirmed = window.confirm(
        '检测到现有会话。开始新会话将清除当前会话的所有数据。\n\n是否继续？'
      )
      if (!confirmed) {
        return
      }
      // Reset state before starting new session
      reset()
      setHasExistingSession(false)
    }
    
    const urlList = urls
      .split('\n')
      .map((url) => url.trim())
      .filter((url) => url.length > 0)

    const hasSources = urlList.length > 0 || uploadedFiles.length > 0 || textEntries.length > 0

    if (!hasSources) {
      setError('请至少添加一个来源（链接、文件或文本）')
      return
    }

    setIsLoading(true)

    try {
      // Validate URLs
      if (urlList.length > 0) {
        const urlPattern = /^https?:\/\/.+/i
        const invalidUrls = urlList.filter((url) => !urlPattern.test(url))
        if (invalidUrls.length > 0) {
          setError(`无效的URL格式: ${invalidUrls.join(', ')}`)
          setIsLoading(false)
          return
        }
      }

      console.log('Formatting links:', urlList)
      console.log('API base URL:', '/api')
      console.log('Making request to:', '/api/links/format')
      
      // First, test if backend is reachable - use /api/health endpoint (proxied)
      try {
        console.log('Testing backend connectivity...')
        // Use /api/health which is guaranteed to be proxied correctly
        const healthCheck = await fetch('/api/health', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          signal: AbortSignal.timeout(5000), // 5 second timeout for health check
        })
        
        // Check if response is actually JSON (not HTML)
        const contentType = healthCheck.headers.get('content-type')
        if (!contentType || !contentType.includes('application/json')) {
          console.warn('Backend health check returned non-JSON response:', contentType)
          setError(`后端服务器返回了非JSON响应。请确保后端正在运行在端口 3001。\n\n启动后端: python backend/run_server.py`)
          addNotification('后端服务器响应格式错误', 'error')
          setIsLoading(false)
          return
        }
        
        if (healthCheck.ok) {
          const healthData = await healthCheck.json()
          console.log('Backend health check passed:', healthData)
        } else {
          console.warn('Backend health check returned non-OK status:', healthCheck.status)
          setError(`后端服务器返回错误状态: ${healthCheck.status}`)
          addNotification(`后端服务器错误: ${healthCheck.status}`, 'error')
          setIsLoading(false)
          return
        }
      } catch (healthError: any) {
        console.error('Backend health check failed:', healthError)
        // Check if it's a JSON parsing error (means we got HTML instead)
        const isJsonError = healthError.message && healthError.message.includes('JSON')
        const errorMessage = isJsonError
          ? '后端服务器返回了HTML而不是JSON。请确保后端正在运行在端口 3001，并且Vite代理配置正确。\n\n启动后端: python backend/run_server.py'
          : healthError.name === 'TimeoutError' 
          ? '后端服务器无响应（超时）。请确保后端正在运行在端口 3001。\n\n启动后端: python backend/run_server.py\n\n或者从项目根目录运行:\ncd backend\npython run_server.py'
          : `无法连接到后端服务器: ${healthError.message}\n\n请确保后端正在运行在端口 3001。\n\n启动后端: python backend/run_server.py`
        setError(errorMessage)
        addNotification('无法连接到后端服务器，请检查后端是否运行', 'error')
        setIsLoading(false)
        return
      }
      
      // Format links and create batch (using existing session_id)
      const startTime = Date.now()
      try {
        const formData = new FormData()
        formData.append('links', JSON.stringify(urlList))
        formData.append(
          'text_entries',
          JSON.stringify(
            textEntries.map((entry) => ({
              label: entry.label,
              content: entry.content,
            }))
          )
        )
        if (sessionId) {
          formData.append('session_id', sessionId)
        }
        uploadedFiles.forEach((file) => formData.append('files', file))

        const response = await apiService.ingestSources(formData)
        const duration = Date.now() - startTime
        console.log(`Format links response received in ${duration}ms:`, response)
        
        if (response.session_id) {
          setSessionId(response.session_id)
        }

        if (response.batch_id) {
          console.log('Setting batchId:', response.batch_id)
          setBatchId(response.batch_id)
          setCurrentPhase('scraping')
          setUrls('')
          setUploadedFiles([])
          setTextEntries([])
          setTextDraft('')
          setTextLabel('')
          addNotification('已准备所有来源，开始抓取...', 'success')
          console.log('Navigating to /scraping')
          navigate('/scraping')
        } else {
          throw new Error('未返回批次ID')
        }
      } catch (error: any) {
        const duration = Date.now() - startTime
        console.error(`Format links failed after ${duration}ms:`, error)
        console.error('Error details:', {
          message: error.message,
          response: error.response?.data,
          status: error.response?.status,
          code: error.code,
        })
        
        // Provide more helpful error messages
        if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
          setError('请求超时。请检查后端服务器是否正在运行。')
          addNotification('请求超时，请确保后端服务器正在运行', 'error')
        } else if (error.code === 'ERR_NETWORK' || error.message.includes('Network Error')) {
          setError('网络错误。无法连接到后端服务器。')
          addNotification('网络错误，请检查后端服务器是否运行', 'error')
        } else {
          const errorMsg = error.response?.data?.detail || error.message || '格式化链接时出错'
          setError(errorMsg)
          addNotification(`来源配置有误，请检查后重试`, 'error')
        }
        setIsLoading(false)
        return
      }
    } catch (err: any) {
      console.error('Error formatting links:', err)
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || err.message || '格式化链接时出错'
      setError(errorMessage)
      addNotification(`来源配置有误，请检查后重试`, 'error')
      setIsLoading(false)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Question Section */}
      <div className="pt-8 pb-8">
        <h1 className="text-2xl md:text-3xl font-semibold text-center text-gray-900 leading-relaxed max-w-3xl mx-auto">
          你想研究哪些内容？
        </h1>
      </div>

      {/* Existing Session Warning */}
      {hasExistingSession && (
        <div className="max-w-2xl mx-auto mb-6">
          <div className="bg-yellow-50 border border-yellow-300 rounded-2xl p-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h4 className="font-semibold text-yellow-800 mb-2">检测到现有会话</h4>
                <p className="text-sm text-yellow-700 mb-2">
                  当前存在一个活跃的研究会话。开始新会话将清除所有现有数据。
                </p>
                {batchId && (
                  <p className="text-xs text-yellow-600 mt-2">
                    当前批次ID: {batchId}
                  </p>
                )}
              </div>
              <button
                onClick={handleStartNewSession}
                className="ml-4 px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-white rounded-lg text-sm font-medium transition-colors"
              >
                清除会话
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Input Section - Dialog Bubble */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="max-w-2xl mx-auto mb-8">
          <div className="bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
            {error && (
              <div className="mb-4 text-sm text-red-600">
                {error}
              </div>
            )}
            <textarea
              value={urls}
              onChange={(e) => setUrls(e.target.value)}
              placeholder={`例如：\nhttps://www.youtube.com/watch?v=...\nhttps://www.bilibili.com/video/...\nhttps://example.com/article`}
              className="w-full min-h-[200px] p-4 border-0 bg-transparent text-base leading-relaxed placeholder:text-gray-400 focus:outline-none focus:ring-0 resize-none"
              rows={10}
              disabled={isLoading}
              onKeyDown={(e) => {
                // Allow Ctrl/Cmd + Enter to submit
                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                  handleSubmit(e as any)
                }
              }}
            />
          </div>
          <p className="text-xs text-gray-500 text-center mt-2">
            支持 YouTube、Bilibili、Reddit、Tieba 和文章链接
          </p>
        </div>

        <div className="max-w-2xl mx-auto mb-8">
          <div className="bg-white rounded-2xl shadow-lg p-6 border border-gray-100 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">上传文件</h3>
                <p className="text-sm text-gray-500 mt-1">支持 PDF、Word、PowerPoint、Excel、Markdown、TXT</p>
              </div>
              <span className="text-sm text-gray-500">{uploadedFiles.length} 个文件</span>
            </div>
            <label
              htmlFor="file-upload"
              className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-200 rounded-xl cursor-pointer hover:border-gray-400 transition-colors"
            >
              <span className="text-sm text-gray-600">拖拽文件到此处，或点击选择</span>
              <span className="text-xs text-gray-400 mt-1">单个 25MB，合计 100MB</span>
            </label>
            <input
              id="file-upload"
              type="file"
              multiple
              accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.markdown"
              className="hidden"
              onChange={handleFileSelect}
            />
            {uploadedFiles.length > 0 && (
              <ul className="divide-y divide-gray-100 text-sm">
                {uploadedFiles.map((file, index) => (
                  <li key={`${file.name}-${index}`} className="flex items-center justify-between py-2">
                    <div className="text-gray-700 truncate pr-4">
                      {file.name} <span className="text-xs text-gray-400">({(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveFile(index)}
                      className="text-xs text-gray-500 hover:text-red-500"
                    >
                      移除
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="max-w-2xl mx-auto mb-8">
          <div className="bg-white rounded-2xl shadow-lg p-6 border border-gray-100 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">添加手动文本</h3>
                <p className="text-sm text-gray-500 mt-1">用于会议纪要、访谈记录或研究背景描述</p>
              </div>
              <span className="text-sm text-gray-500">{textEntries.length} 段文本</span>
            </div>
            <div className="space-y-3">
              <input
                type="text"
                value={textLabel}
                onChange={(e) => setTextLabel(e.target.value)}
                placeholder="可选标题，例如「访谈总结」"
                className="w-full border border-gray-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
              />
              <textarea
                value={textDraft}
                onChange={(e) => setTextDraft(e.target.value)}
                rows={4}
                placeholder="粘贴或输入文本内容..."
                className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
              />
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={handleAddTextEntry}
                  className="px-4 py-2 bg-gray-900 text-white rounded-xl text-sm hover:bg-gray-800 transition-colors"
                >
                  添加文本
                </button>
              </div>
            </div>
            {textEntries.length > 0 && (
              <ul className="divide-y divide-gray-100 text-sm">
                {textEntries.map((entry) => (
                  <li key={entry.id} className="flex items-center justify-between py-2">
                    <div className="text-gray-700 truncate pr-4">
                      {entry.label} <span className="text-xs text-gray-400">({entry.content.length} 字)</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveTextEntry(entry.id)}
                      className="text-xs text-gray-500 hover:text-red-500"
                    >
                      移除
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Action Button - Circular */}
        <div className="flex justify-center">
          <button
            type="submit"
            disabled={
              isLoading ||
              (!urls.trim() && uploadedFiles.length === 0 && textEntries.length === 0)
            }
            className="w-16 h-16 rounded-full text-white shadow-xl hover:scale-110 transition-all duration-200 flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
            style={{ backgroundColor: '#FEC74A' }}
            aria-label="开始研究"
          >
            {isLoading ? (
              <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <ArrowRight size={24} strokeWidth={2.5} />
            )}
          </button>
        </div>
      </form>
    </div>
  )
}

export default LinkInputPage


