import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Card from '../components/common/Card'
import Button from '../components/common/Button'
import { apiService } from '../services/api'
import { useWorkflowStore } from '../stores/workflowStore'
import { useUiStore } from '../stores/uiStore'

interface HistorySession {
  batch_id: string
  created_at: string
  status: 'completed' | 'in-progress' | 'failed' | 'cancelled'
  topic?: string
  url_count?: number
  current_phase?: string
}

const HistoryPage: React.FC = () => {
  const navigate = useNavigate()
  const { setBatchId, setCurrentPhase } = useWorkflowStore()
  const { addNotification } = useUiStore()
  const [sessions, setSessions] = useState<HistorySession[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    loadHistory()
  }, [filterStatus])

  const loadHistory = async () => {
    setLoading(true)
    setError(null)
    try {
      const params: any = {}
      if (filterStatus !== 'all') {
        params.status = filterStatus
      }
      const data = await apiService.getHistory(params)
      setSessions(data.sessions || data || [])
    } catch (err: any) {
      console.error('Failed to load history:', err)
      setError(err.response?.data?.detail || err.message || '无法加载历史记录，请刷新页面重试')
      addNotification('无法加载历史记录，请刷新页面重试', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleResume = async (batchId: string) => {
    try {
      // Load session data
      const sessionData = await apiService.getHistorySession(batchId)
      
      // Restore workflow state
      setBatchId(batchId)
      
      // Determine current phase from session data
      if (sessionData.current_phase) {
        setCurrentPhase(sessionData.current_phase as any)
      } else if (sessionData.status === 'completed') {
        setCurrentPhase('complete')
        navigate('/report')
        return
      } else {
        // Try to determine phase from progress
        if (sessionData.scraping_status?.completed === sessionData.scraping_status?.total) {
          setCurrentPhase('research')
          navigate('/research')
          return
        } else {
          setCurrentPhase('scraping')
          navigate('/scraping')
          return
        }
      }

      // Resume workflow
      await apiService.resumeSession(batchId)
      addNotification('已恢复会话', 'success')
      
      // Navigate based on current phase
      const phaseRoutes: Record<string, string> = {
        scraping: '/scraping',
        research: '/research',
        phase3: '/phase3',
        complete: '/report',
      }
      const route = phaseRoutes[sessionData.current_phase] || '/scraping'
      navigate(route)
    } catch (err: any) {
      console.error('Failed to resume session:', err)
      addNotification('无法恢复会话，请重试', 'error')
    }
  }

  const handleView = async (batchId: string) => {
    try {
      const sessionData = await apiService.getHistorySession(batchId)
      
      // Restore state
      setBatchId(batchId)
      setCurrentPhase('complete')
      
      // Navigate to report
      navigate('/report')
    } catch (err: any) {
      console.error('Failed to view session:', err)
      addNotification('无法查看会话详情，请重试', 'error')
    }
  }

  const handleDelete = async (batchId: string) => {
    if (!window.confirm('确定要删除这个会话吗？此操作无法撤销。')) {
      return
    }

    try {
      await apiService.deleteSession(batchId)
      addNotification('会话已删除', 'success')
      loadHistory() // Reload list
    } catch (err: any) {
      console.error('Failed to delete session:', err)
      addNotification('无法删除会话，请重试', 'error')
    }
  }

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      completed: { bg: 'bg-green-100', text: 'text-green-800', label: '已完成' },
      'in-progress': { bg: 'bg-yellow-100', text: 'text-yellow-800', label: '某种努力中' },
      failed: { bg: 'bg-red-100', text: 'text-red-800', label: 'OMG出错了' },
      cancelled: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: '已取消' },
    }

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig['in-progress']

    return (
      <span className={`px-2 py-1 rounded text-xs font-medium ${config.bg} ${config.text}`}>
        {config.label}
      </span>
    )
  }

  const filteredSessions = sessions.filter((session) => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      return (
        session.batch_id.toLowerCase().includes(query) ||
        (session.topic && session.topic.toLowerCase().includes(query))
      )
    }
    return true
  })

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <Card title="研究历史" subtitle="查看和管理之前的研究会话">
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex items-center gap-4 pb-4 border-b border-neutral-300">
            <div className="flex-1">
              <input
                type="text"
                placeholder="搜索批次ID或主题..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-4 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="all">全部状态</option>
              <option value="completed">已完成</option>
              <option value="in-progress">某种努力中</option>
              <option value="failed">OMG出错了</option>
              <option value="cancelled">已取消</option>
            </select>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="text-center py-8">
              <p className="text-neutral-400">正在加载历史记录...</p>
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div className="text-center py-8">
              <p className="text-red-500 mb-4">{error}</p>
              <Button onClick={loadHistory}>重试</Button>
            </div>
          )}

          {/* Sessions List */}
          {!loading && !error && (
            <>
              {filteredSessions.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-neutral-400">暂无历史记录</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredSessions.map((session) => (
                    <div
                      key={session.batch_id}
                      className="bg-neutral-white border border-neutral-300 rounded-lg p-4 hover:shadow-md transition-shadow"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="font-semibold text-neutral-800">
                              {session.topic || '未命名会话'}
                            </h3>
                            {getStatusBadge(session.status)}
                          </div>
                          <div className="text-sm text-neutral-600 space-y-1">
                            <p>
                              <span className="font-medium">批次ID:</span> {session.batch_id}
                            </p>
                            <p>
                              <span className="font-medium">创建时间:</span>{' '}
                              {new Date(session.created_at).toLocaleString('zh-CN')}
                            </p>
                            {session.url_count !== undefined && (
                              <p>
                                <span className="font-medium">链接数量:</span> {session.url_count}
                              </p>
                            )}
                            {session.current_phase && (
                              <p>
                                <span className="font-medium">当前阶段:</span> {session.current_phase}
                              </p>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2 ml-4">
                          {session.status === 'completed' && (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => handleView(session.batch_id)}
                            >
                              查看报告
                            </Button>
                          )}
                          {session.status === 'in-progress' && (
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => handleResume(session.batch_id)}
                            >
                              继续
                            </Button>
                          )}
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handleDelete(session.batch_id)}
                            className="text-red-600 hover:text-red-700"
                          >
                            删除
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </Card>
    </div>
  )
}

export default HistoryPage

