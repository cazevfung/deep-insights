import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiService } from '../services/api'
import { useUiStore } from '../stores/uiStore'
import { useWorkflowStore } from '../stores/workflowStore'

export type Phase3StepStatus = 'completed' | 'in-progress' | 'not-started'

export interface Phase3StepKeyClaim {
  claim: string
  supportingEvidence?: string
}

export interface FiveWhyItem {
  level: number
  question: string
  answer: string
}

export interface Phase3StepAnalysisDetails {
  fiveWhys: FiveWhyItem[]
  assumptions: string[]
  uncertainties: string[]
}

export interface Phase3StepContentModel {
  summary?: string
  article?: string
  keyClaims: Phase3StepKeyClaim[]
  analysis: Phase3StepAnalysisDetails
  insights?: string
}

export interface Phase3StepViewModel {
  id: number
  title: string
  status: Phase3StepStatus
  summaryPreview?: string
  confidence?: number | null
  content: Phase3StepContentModel
  rawStep?: SessionStep
  isExpanded: boolean
  showRawData: boolean
  canExpand: boolean
  isActive: boolean
  rerunSpinner: {
    active: boolean
    regenerateReport: boolean
  }
}

export interface UsePhase3StepsResult {
  steps: Phase3StepViewModel[]
  reportStale: boolean
  rerunState: StepRerunState
  hasAnySteps: boolean
  activeStepId: number | null
  handleToggleStep: (stepId: number) => void
  handleToggleRawData: (stepId: number) => void
  handleRerunStep: (stepId: number, regenerateReport: boolean) => Promise<void>
  batchId?: string | null
}

interface SessionStep {
  step_id: number
  findings: any
  insights?: string
  confidence?: number
  timestamp?: string
}

export interface StepRerunState {
  inProgress: boolean
  stepId?: number | null
  regenerateReport: boolean
}

interface PlanStep {
  step_id: number
  goal?: string
}

const SUMMARY_PREVIEW_LIMIT = 140

const emptyContent: Phase3StepContentModel = {
  summary: undefined,
  article: undefined,
  keyClaims: [],
  analysis: { fiveWhys: [], assumptions: [], uncertainties: [] },
  insights: undefined,
}

const normalizeFiveWhys = (value: unknown): FiveWhyItem[] => {
  if (!Array.isArray(value)) {
    return []
  }

  return value
    .map((item, index) => {
      // Handle new object format
      if (item && typeof item === 'object') {
        const level = typeof (item as any).level === 'number' ? (item as any).level : index + 1
        const question = typeof (item as any).question === 'string' ? (item as any).question : ''
        const answer = typeof (item as any).answer === 'string' ? (item as any).answer : ''

        if (!question && !answer) {
          return null
        }

        return { level, question, answer }
      }
      
      // Handle legacy string format for backward compatibility
      if (typeof item === 'string') {
        return {
          level: index + 1,
          question: `为什么 ${index + 1}`,
          answer: item,
        }
      }

      return null
    })
    .filter((item): item is FiveWhyItem => Boolean(item))
}

const toArray = (value: unknown): string[] => {
  if (Array.isArray(value)) {
    return value.filter((item): item is string => typeof item === 'string')
  }
  return []
}

const normalizeKeyClaims = (value: unknown): Phase3StepKeyClaim[] => {
  if (!Array.isArray(value)) {
    return []
  }

  return value
    .map((item) => {
      if (!item || typeof item !== 'object') {
        return null
      }
      const claim = typeof (item as any).claim === 'string' ? (item as any).claim : ''
      const supportingEvidence =
        typeof (item as any).supporting_evidence === 'string'
          ? (item as any).supporting_evidence
          : undefined

      if (!claim) {
        return null
      }

      return {
        claim,
        supportingEvidence,
      }
    })
    .filter((claim): claim is Phase3StepKeyClaim => Boolean(claim))
}

const normalizeContent = (step?: SessionStep | null): Phase3StepContentModel => {
  if (!step) {
    return emptyContent
  }

  const findingsRoot = step.findings && typeof step.findings === 'object' ? step.findings : {}
  const findings =
    findingsRoot && typeof (findingsRoot as any).findings === 'object'
      ? (findingsRoot as any).findings
      : findingsRoot

  const summary = typeof findings.summary === 'string' ? findings.summary : undefined
  const article = typeof findings.article === 'string' ? findings.article : undefined

  const pointsOfInterest =
    findings && typeof findings.points_of_interest === 'object'
      ? findings.points_of_interest
      : {}

  const analysisDetails =
    findings && typeof findings.analysis_details === 'object'
      ? findings.analysis_details
      : {}

  return {
    summary,
    article,
    keyClaims: normalizeKeyClaims(pointsOfInterest?.key_claims),
    analysis: {
      fiveWhys: normalizeFiveWhys(analysisDetails?.five_whys),
      assumptions: toArray(analysisDetails?.assumptions),
      uncertainties: toArray(analysisDetails?.uncertainties),
    },
    insights: typeof step.insights === 'string' ? step.insights : undefined,
  }
}

const createSummaryPreview = (summary?: string): string | undefined => {
  if (!summary) {
    return undefined
  }

  if (summary.length <= SUMMARY_PREVIEW_LIMIT) {
    return summary
  }

  return `${summary.slice(0, SUMMARY_PREVIEW_LIMIT)}...`
}

const computeStepStatus = (
  stepId: number,
  hasStep: boolean,
  expectedStepIds: number[],
  completedCount: number
): Phase3StepStatus => {
  if (hasStep) {
    return 'completed'
  }

  const index = expectedStepIds.indexOf(stepId)
  if (index !== -1 && index <= completedCount) {
    return 'in-progress'
  }

  return 'not-started'
}

export const usePhase3Steps = (): UsePhase3StepsResult => {
  const {
    phase3Steps,
    researchAgentStatus,
    batchId,
    sessionId,
    stepRerunState,
    reportStale,
    currentStepId,
  } = useWorkflowStore((state) => ({
    phase3Steps: state.phase3Steps as SessionStep[],
    researchAgentStatus: state.researchAgentStatus,
    batchId: state.batchId,
    sessionId: state.sessionId,
    stepRerunState: state.stepRerunState as StepRerunState,
    reportStale: state.reportStale,
    currentStepId: state.currentStepId,
  }))
  const { addNotification } = useUiStore()

  const [expandedMap, setExpandedMap] = useState<Record<number, boolean>>({})
  const [rawDataMap, setRawDataMap] = useState<Record<number, boolean>>({})

  const plan: PlanStep[] = useMemo(() => {
    if (!researchAgentStatus?.plan || !Array.isArray(researchAgentStatus.plan)) {
      return []
    }
    return researchAgentStatus.plan as PlanStep[]
  }, [researchAgentStatus?.plan])

  const expectedStepIds = useMemo(
    () => plan.map((step) => step.step_id).sort((a, b) => a - b),
    [plan]
  )

  const stepsMap = useMemo(() => {
    const map = new Map<number, SessionStep>()
    phase3Steps.forEach((step) => {
      map.set(step.step_id, step)
    })
    return map
  }, [phase3Steps])

  const allStepIds = useMemo(() => {
    const ids = new Set<number>(expectedStepIds)
    phase3Steps.forEach((step) => ids.add(step.step_id))
    return Array.from(ids).sort((a, b) => a - b)
  }, [expectedStepIds, phase3Steps])

  const completedCount = phase3Steps.length
  const activeStreamStepId =
    typeof researchAgentStatus?.streamingState?.metadata?.step_id === 'number'
      ? (researchAgentStatus.streamingState.metadata.step_id as number)
      : null

  const steps = useMemo<Phase3StepViewModel[]>(() => {
    if (allStepIds.length === 0) {
      return []
    }

    return allStepIds.map((stepId) => {
      const rawStep = stepsMap.get(stepId)
      const planStep = plan.find((item) => item.step_id === stepId)
      const status = computeStepStatus(stepId, Boolean(rawStep), expectedStepIds, completedCount)
      const content = normalizeContent(rawStep)
      const isCurrent =
        (typeof currentStepId === 'number' && currentStepId === stepId) ||
        (typeof activeStreamStepId === 'number' && activeStreamStepId === stepId) ||
        status === 'in-progress'

      return {
        id: stepId,
        title: planStep?.goal ?? `分析步骤 ${stepId}`,
        status,
        summaryPreview: createSummaryPreview(content.summary),
        confidence:
          typeof rawStep?.confidence === 'number' ? rawStep.confidence : rawStep?.confidence ?? null,
        content,
        rawStep,
        isExpanded: Boolean(expandedMap[stepId]),
        showRawData: Boolean(rawDataMap[stepId]),
        canExpand: Boolean(rawStep),
        isActive: isCurrent,
        rerunSpinner: {
          active:
            Boolean(stepRerunState?.inProgress) &&
            stepRerunState?.stepId === stepId,
          regenerateReport: Boolean(stepRerunState?.regenerateReport),
        },
      }
    })
  }, [
    allStepIds,
    stepsMap,
    plan,
    expectedStepIds,
    completedCount,
    expandedMap,
    rawDataMap,
    currentStepId,
    activeStreamStepId,
    stepRerunState?.inProgress,
    stepRerunState?.regenerateReport,
    stepRerunState?.stepId,
  ])

  const hasAnySteps = steps.length > 0

  useEffect(() => {
    if (typeof currentStepId !== 'number') {
      return
    }
    setExpandedMap((prev) => {
      if (prev[currentStepId]) {
        return prev
      }
      return {
        ...prev,
        [currentStepId]: true,
      }
    })
  }, [currentStepId])

  useEffect(() => {
    if (typeof activeStreamStepId !== 'number') {
      return
    }
    setExpandedMap((prev) => {
      if (prev[activeStreamStepId]) {
        return prev
      }
      return {
        ...prev,
        [activeStreamStepId]: true,
      }
    })
  }, [activeStreamStepId])

  const handleToggleStep = useCallback((stepId: number) => {
    setExpandedMap((prev) => ({
      ...prev,
      [stepId]: !prev[stepId],
    }))
  }, [])

  const handleToggleRawData = useCallback((stepId: number) => {
    setRawDataMap((prev) => ({
      ...prev,
      [stepId]: !prev[stepId],
    }))
  }, [])

  const handleRerunStep = useCallback(
    async (stepId: number, regenerateReport: boolean) => {
      if (!batchId || !sessionId) {
        addNotification('缺少批次或会话信息，无法重新执行步骤', 'warning')
        return
      }

      try {
        await apiService.rerunPhase3Step({
          batch_id: batchId,
          session_id: sessionId,
          step_id: stepId,
          regenerate_report: regenerateReport,
        })
        addNotification('已提交步骤重新执行请求', 'info')
      } catch (error) {
        console.error('Failed to request step rerun', error)
        addNotification('提交步骤重新执行请求失败', 'error')
      }
    },
    [addNotification, batchId, sessionId]
  )

  return {
    steps,
    reportStale: Boolean(reportStale),
    rerunState: stepRerunState ?? {
      inProgress: false,
      regenerateReport: false,
      stepId: undefined,
    },
    hasAnySteps,
    activeStepId:
      typeof activeStreamStepId === 'number'
        ? activeStreamStepId
        : typeof currentStepId === 'number'
        ? currentStepId
        : null,
    handleToggleStep,
    handleToggleRawData,
    handleRerunStep,
    batchId,
  }
}


