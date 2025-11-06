import React, { useEffect, useState } from 'react'
import { useWorkflowStore } from '../stores/workflowStore'
import { apiService } from '../services/api'
import ReactMarkdown from 'react-markdown'

const FinalReportPage: React.FC = () => {
  const { batchId, finalReport, setFinalReport } = useWorkflowStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // If we already have the report in store, don't fetch again
    if (finalReport?.content) {
      return
    }

    // If no batchId, can't fetch report
    if (!batchId) {
      setError('还没有开始研究工作，请先添加链接并开始研究')
      return
    }

    // Fetch report from API
    const fetchReport = async () => {
      setLoading(true)
      setError(null)
      try {
        const reportData = await apiService.getFinalReport(batchId)
        setFinalReport({
          content: reportData.content,
          generatedAt: reportData.metadata.generatedAt,
          status: reportData.status as 'generating' | 'ready' | 'error',
        })
      } catch (err: any) {
        console.error('Failed to fetch report:', err)
        if (err.response?.status === 404) {
          setError('报告正在生成中，请稍候...')
        } else {
          setError(err.response?.data?.detail || err.message || '无法加载报告，请刷新页面重试')
        }
      } finally {
        setLoading(false)
      }
    }

    fetchReport()
  }, [batchId, finalReport, setFinalReport])

  return (
    <div className="max-w-6xl mx-auto h-full flex flex-col">
      <div className="card h-full flex flex-col p-0">
        {/* Report Header */}
        <div className="sticky top-0 bg-neutral-white pb-4 border-b border-neutral-300 mb-4 z-10 px-6 pt-6 rounded-t-lg">
          <h2 className="text-xl font-bold text-neutral-black">研究报告</h2>
          {finalReport?.generatedAt && (
            <p className="text-sm text-neutral-500 mt-1">
              撰写于: {new Date(finalReport.generatedAt).toLocaleString('zh-CN')}
            </p>
          )}
        </div>

        {/* Report Content */}
        <div className="flex-1 overflow-y-auto px-6 pb-6">
          {loading && (
            <div className="flex items-center justify-center h-full">
              <p className="text-neutral-400">正在加载报告...</p>
            </div>
          )}

          {error && !loading && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <p className="text-red-500 mb-2">{error}</p>
                <p className="text-sm text-neutral-500">
                  研究可能还在进行中，请稍后再查看报告
                </p>
              </div>
            </div>
          )}

          {!loading && !error && finalReport?.content && (
            <div className="prose prose-lg max-w-none prose-headings:text-neutral-black prose-headings:font-bold prose-p:text-neutral-black prose-p:leading-relaxed prose-strong:text-neutral-black prose-ul:text-neutral-black prose-ol:text-neutral-black prose-li:text-neutral-black prose-hr:border-neutral-300">
              <ReactMarkdown>{finalReport.content}</ReactMarkdown>
            </div>
          )}

          {!loading && !error && !finalReport?.content && (
            <div className="flex items-center justify-center h-full">
              <p className="text-neutral-400">报告生成中...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default FinalReportPage


