import React, { useState, useMemo } from 'react'
import Card from '../components/common/Card'
import { useWorkflowStore } from '../stores/workflowStore'
import { useWebSocket } from '../hooks/useWebSocket'
import { Icon } from '../components/common/Icon'

// Local interface matching the store's SessionStep structure
interface SessionStep {
  step_id: number
  findings: {
    summary?: string
    points_of_interest?: {
      key_claims?: Array<{
        claim: string
        supporting_evidence: string
      }>
      notable_evidence?: Array<{
        evidence_type: string
        description: string
      }>
    }
    analysis_details?: {
      five_whys?: string[]
      assumptions?: string[]
      uncertainties?: string[]
    }
  }
  insights: string
  confidence: number
  timestamp: string
}

const Phase3SessionPage: React.FC = () => {
  const { phase3Steps, researchAgentStatus, batchId } = useWorkflowStore()
  // Establish WebSocket connection to receive real-time step updates
  useWebSocket(batchId || '')
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set())
  const [showRawData, setShowRawData] = useState<Record<number, boolean>>({})

  // Get plan to determine expected step count
  const plan = researchAgentStatus.plan || []
  const expectedStepIds = useMemo(() => {
    return plan.map((step: any) => step.step_id).sort((a: number, b: number) => a - b)
  }, [plan])

  // Get all step IDs (both received and expected)
  const allStepIds = useMemo(() => {
    const receivedIds = phase3Steps.map((s) => s.step_id)
    const allIds = new Set([...expectedStepIds, ...receivedIds])
    return Array.from(allIds).sort((a, b) => a - b)
  }, [expectedStepIds, phase3Steps])

  // Create a map of received steps
  const stepsMap = useMemo(() => {
    const map = new Map<number, SessionStep>()
    phase3Steps.forEach((step) => {
      map.set(step.step_id, step as SessionStep)
    })
    return map
  }, [phase3Steps])

  const toggleStep = (stepId: number) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev)
      if (next.has(stepId)) {
        next.delete(stepId)
      } else {
        next.add(stepId)
      }
      return next
    })
  }

  const toggleRawData = (stepId: number) => {
    setShowRawData((prev) => ({
      ...prev,
      [stepId]: !prev[stepId],
    }))
  }

  const getStepStatus = (stepId: number): 'completed' | 'in-progress' | 'not-started' => {
    const step = stepsMap.get(stepId)
    if (step) {
      return 'completed'
    }
    // Check if it's the current step
    const currentStepId = expectedStepIds.find((id: number) => id === stepId)
    if (currentStepId && expectedStepIds.indexOf(currentStepId) <= phase3Steps.length) {
      return 'in-progress'
    }
    return 'not-started'
  }

  const renderStepContent = (step: SessionStep) => {
    // Handle nested findings structure (findings.findings) if present
    const findings = (step.findings as any)?.findings || step.findings || {}
    const pointsOfInterest = findings.points_of_interest || {}
    const analysisDetails = findings.analysis_details || {}

    return (
      <div className="space-y-6">
        {/* Summary Section */}
        {findings.summary && (
          <div className="bg-neutral-50 rounded-lg p-4">
            <h4 className="font-semibold text-neutral-800 mb-2 flex items-center">
              <Icon name="edit" size={18} strokeWidth={2} className="mr-2" />
              摘要
            </h4>
            <p className="text-neutral-700 whitespace-pre-wrap">{findings.summary}</p>
          </div>
        )}

        {/* Key Claims Section */}
        {pointsOfInterest.key_claims && pointsOfInterest.key_claims.length > 0 && (
          <div>
            <h4 className="font-semibold text-neutral-800 mb-3 flex items-center">
              <Icon name="key" size={18} strokeWidth={2} className="mr-2" />
              主要观点
            </h4>
            <div className="space-y-3">
              {pointsOfInterest.key_claims.map((claim, index) => (
                <div key={index} className="bg-neutral-50 rounded-lg p-4 border-l-4 border-yellow-500">
                  <div className="font-medium text-neutral-800 mb-2">{claim.claim}</div>
                  {claim.supporting_evidence && (
                    <div className="text-sm text-neutral-600 mt-2">
                      <span className="font-medium">证据支持：</span>
                      <span className="whitespace-pre-wrap">{claim.supporting_evidence}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Notable Evidence Section */}
        {pointsOfInterest.notable_evidence && pointsOfInterest.notable_evidence.length > 0 && (
          <div>
            <h4 className="font-semibold text-neutral-800 mb-3 flex items-center">
              <Icon name="chart" size={18} strokeWidth={2} className="mr-2" />
              重要发现
            </h4>
            <div className="space-y-3">
              {pointsOfInterest.notable_evidence.map((evidence, index) => (
                <div key={index} className="bg-neutral-50 rounded-lg p-4">
                  <div className="flex items-start">
                    <span className="inline-block bg-yellow-100 text-yellow-800 text-xs font-medium px-2.5 py-0.5 rounded mr-3 mt-1">
                      {evidence.evidence_type}
                    </span>
                    <p className="text-neutral-700 flex-1 whitespace-pre-wrap">{evidence.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Analysis Details Section */}
        {(analysisDetails.five_whys ||
          analysisDetails.assumptions ||
          analysisDetails.uncertainties) && (
          <div>
            <h4 className="font-semibold text-neutral-800 mb-3 flex items-center">
              <Icon name="search" size={18} strokeWidth={2} className="mr-2" />
              深入分析
            </h4>
            <div className="space-y-4">
              {/* Five Whys */}
              {analysisDetails.five_whys && analysisDetails.five_whys.length > 0 && (
                <div className="bg-neutral-50 rounded-lg p-4">
                  <h5 className="font-medium text-neutral-800 mb-2">五个为什么</h5>
                  <ul className="list-disc list-inside space-y-1 text-neutral-700">
                    {analysisDetails.five_whys.map((why, index) => (
                      <li key={index} className="whitespace-pre-wrap">
                        {why}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Assumptions */}
              {analysisDetails.assumptions && analysisDetails.assumptions.length > 0 && (
                <div className="bg-neutral-50 rounded-lg p-4">
                  <h5 className="font-medium text-neutral-800 mb-2">假设分析</h5>
                  <ul className="list-disc list-inside space-y-1 text-neutral-700">
                    {analysisDetails.assumptions.map((assumption, index) => (
                      <li key={index} className="whitespace-pre-wrap">
                        {assumption}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Uncertainties */}
              {analysisDetails.uncertainties && analysisDetails.uncertainties.length > 0 && (
                <div className="bg-neutral-50 rounded-lg p-4">
                  <h5 className="font-medium text-neutral-800 mb-2">不确定性分析</h5>
                  <ul className="list-disc list-inside space-y-1 text-neutral-700">
                    {analysisDetails.uncertainties.map((uncertainty, index) => (
                      <li key={index} className="whitespace-pre-wrap">
                        {uncertainty}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Insights Section */}
        {step.insights && (
          <div className="bg-yellow-50 rounded-lg p-4 border-l-4 border-yellow-500">
            <h4 className="font-semibold text-neutral-800 mb-2 flex items-center">
              <Icon name="lightbulb" size={18} strokeWidth={2} className="mr-2" />
              洞察
            </h4>
            <p className="text-neutral-700 whitespace-pre-wrap">{step.insights}</p>
          </div>
        )}

        {/* Confidence Section */}
        {step.confidence !== undefined && step.confidence !== null && (
          <div className="flex items-center space-x-4">
            <span className="font-medium text-neutral-700">可信度：</span>
            <div className="flex-1 bg-neutral-200 rounded-full h-2.5">
              <div
                className={`h-2.5 rounded-full ${
                  step.confidence >= 0.8
                    ? 'bg-green-500'
                    : step.confidence >= 0.6
                    ? 'bg-yellow-500'
                    : 'bg-red-500'
                }`}
                style={{ width: `${step.confidence * 100}%` }}
              ></div>
            </div>
            <span className="text-sm font-medium text-neutral-700">
              {(step.confidence * 100).toFixed(1)}%
            </span>
          </div>
        )}

        {/* Raw Data Toggle */}
        <div className="border-t pt-4">
          <button
            onClick={() => toggleRawData(step.step_id)}
            className="text-sm text-neutral-500 hover:text-neutral-700 flex items-center"
          >
            <span className="mr-2">{showRawData[step.step_id] ? '▼' : '▶'}</span>
            {showRawData[step.step_id] ? '收起原始数据' : '查看原始数据'}
          </button>
          {showRawData[step.step_id] && (
            <pre className="mt-2 text-xs bg-neutral-100 p-4 rounded overflow-auto max-h-96 border">
              {JSON.stringify(step, null, 2)}
            </pre>
          )}
        </div>
      </div>
    )
  }

  const renderStepCard = (stepId: number) => {
    const step = stepsMap.get(stepId)
    const status = getStepStatus(stepId)
    const isExpanded = expandedSteps.has(stepId)

    if (!step) {
      // Step not received yet
      return (
        <div
          key={stepId}
          className="bg-neutral-100 border border-neutral-300 rounded-lg p-4 opacity-60"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-full bg-neutral-300 flex items-center justify-center text-sm font-medium text-neutral-600">
                {stepId}
              </div>
              <div>
                <h3 className="font-semibold text-neutral-600">分析步骤 {stepId}</h3>
                <p className="text-sm text-neutral-500">
                  {status === 'in-progress' ? '某种努力中...' : '待启动'}
                </p>
              </div>
            </div>
            <span className="text-xs px-2 py-1 bg-neutral-300 text-neutral-600 rounded">
              {status === 'in-progress' ? '某种努力中' : '准备中'}
            </span>
          </div>
        </div>
      )
    }

    return (
      <div key={stepId} className="bg-neutral-white border border-neutral-300 rounded-lg">
        {/* Step Header */}
        <button
          onClick={() => toggleStep(stepId)}
          className="w-full p-4 flex items-center justify-between hover:bg-neutral-50 transition-colors"
        >
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-full bg-yellow-500 flex items-center justify-center text-sm font-medium text-white">
              {stepId}
            </div>
            <div className="text-left">
              <h3 className="font-semibold text-neutral-800">分析步骤 {stepId}</h3>
              {(() => {
                const findings = (step.findings as any)?.findings || step.findings || {}
                const summary = findings.summary || ''
                return summary ? (
                  <p className="text-sm text-neutral-500 line-clamp-1 mt-1">
                    {summary.substring(0, 100)}
                    {summary.length > 100 ? '...' : ''}
                  </p>
                ) : null
              })()}
            </div>
          </div>
          <div className="flex items-center space-x-3">
            {step.confidence !== undefined && step.confidence !== null && (
              <span className="text-xs px-2 py-1 bg-yellow-100 text-yellow-800 rounded">
                {(step.confidence * 100).toFixed(0)}%
              </span>
            )}
            <span className="text-neutral-400">{isExpanded ? '▼' : '▶'}</span>
          </div>
        </button>

        {/* Step Content */}
        {isExpanded && (
          <div className="px-4 pb-4 border-t bg-neutral-50">
            <div className="pt-4">{renderStepContent(step)}</div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto">
      <Card title="深度研究 - 分析步骤">
        {phase3Steps.length === 0 && allStepIds.length === 0 ? (
          <p className="text-neutral-400 py-8 text-center">还没有分析步骤，研究完成后将显示在这里</p>
        ) : (
          <div className="space-y-4">
            {allStepIds.map((stepId) => renderStepCard(stepId))}
          </div>
        )}
      </Card>
    </div>
  )
}

export default Phase3SessionPage
