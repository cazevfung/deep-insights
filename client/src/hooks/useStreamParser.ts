import { useEffect, useRef, useState } from 'react'
import { useWorkflowStore } from '../stores/workflowStore'
import { incrementalParseJSON } from '../utils/streaming/jsonIncrementalParser'

export type ParserStatus = 'idle' | 'parsing' | 'valid' | 'error'

interface UseStreamParserOptions {
  enableRepair?: boolean
  debounceMs?: number
  streamId?: string
}

interface ParserState {
  root: any | null
  status: ParserStatus
  error?: string
}

const defaultState: ParserState = {
  root: null,
  status: 'idle',
}

export const useStreamParser = (options: UseStreamParserOptions = {}): ParserState => {
  const { enableRepair = true, debounceMs = 200, streamId } = options
  const researchAgentStatus = useWorkflowStore((state) => state.researchAgentStatus)
  const setGoals = useWorkflowStore((state) => state.setGoals)
  const setPlan = useWorkflowStore((state) => state.setPlan)
  const setSynthesizedGoal = useWorkflowStore((state) => state.setSynthesizedGoal)
  const updateLiveGoal = useWorkflowStore((state) => state.updateLiveGoal)
  const updateLivePlanStep = useWorkflowStore((state) => state.updateLivePlanStep)
  const updateLiveInsight = useWorkflowStore((state) => state.updateLiveInsight)
  const updateLiveAction = useWorkflowStore((state) => state.updateLiveAction)
  const updateLiveReportSection = useWorkflowStore((state) => state.updateLiveReportSection)
  const [parserState, setParserState] = useState<ParserState>(defaultState)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastParsedHashRef = useRef<string | null>(null)
  const lastStreamIdRef = useRef<string | null>(null)
  const resolvedStreamId = streamId ?? researchAgentStatus.streams.activeStreamId ?? researchAgentStatus.streams.order[0] ?? null
  const streamBuffer = resolvedStreamId
    ? researchAgentStatus.streams.buffers[resolvedStreamId]?.raw ?? ''
    : researchAgentStatus.streamBuffer

  useEffect(() => {
    if (resolvedStreamId !== lastStreamIdRef.current) {
      lastStreamIdRef.current = resolvedStreamId
      lastParsedHashRef.current = null
    }
  }, [resolvedStreamId])

  useEffect(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }

    if (!streamBuffer) {
      setParserState(defaultState)
      lastParsedHashRef.current = null
      return
    }

    setParserState((prev) => ({
      root: prev.root,
      status: 'parsing',
    }))

    timeoutRef.current = setTimeout(() => {
      try {
        const parsed = incrementalParseJSON(streamBuffer, { enableRepair })
        const parsedHash = JSON.stringify(parsed)
        const isDuplicate = parsedHash === lastParsedHashRef.current
        lastParsedHashRef.current = parsedHash

        setParserState({
          root: parsed,
          status: 'valid',
        })

        if (!isDuplicate && parsed) {
          if (Array.isArray(parsed.suggested_goals)) {
            // Update goal list (will sync liveGoals internally)
            setGoals(parsed.suggested_goals)
            parsed.suggested_goals.forEach((goal: any) => {
              if (goal && typeof goal.id === 'number') {
                updateLiveGoal({ id: goal.id, goal_text: goal.goal_text, rationale: goal.rationale, uses: goal.uses, sources: goal.sources, status: 'ready' })
              }
            })
          }

          if (Array.isArray(parsed.goals)) {
            setGoals(parsed.goals)
            parsed.goals.forEach((goal: any, index: number) => {
              const id = typeof goal.id === 'number' ? goal.id : index + 1
              updateLiveGoal({ id, goal_text: goal.goal_text, rationale: goal.rationale, uses: goal.uses, sources: goal.sources, status: 'ready' })
            })
          }

          const planSteps = parsed.plan?.steps || parsed.research_plan?.steps
          if (Array.isArray(planSteps)) {
            setPlan(planSteps)
            planSteps.forEach((step: any) => {
              if (!step) return
              const id = step.step_id ?? step.id
              if (typeof id === 'number') {
                updateLivePlanStep({
                  step_id: id,
                  goal: step.goal,
                  required_data: step.required_data,
                  chunk_strategy: step.chunk_strategy,
                  notes: step.notes,
                  status: 'ready',
                })
              }
            })
          }

          if (parsed.synthesized_goal) {
            setSynthesizedGoal(parsed.synthesized_goal)
          }

          const findings = parsed.findings || parsed.phase2_findings || parsed.insights
          if (Array.isArray(findings)) {
            findings.forEach((finding: any, index: number) => {
              if (!finding) return
              const id = String(finding.id ?? index + 1)
              updateLiveInsight({
                id,
                title: finding.title || finding.name || `洞察 ${index + 1}`,
                summary: finding.summary || finding.content || finding.description || '',
                sources: finding.sources || finding.citations || finding.references,
                status: 'ready',
              })
            })
          }

          const actions = parsed.actions || parsed.execution_steps || parsed.phase3_actions
          if (Array.isArray(actions)) {
            actions.forEach((action: any, index: number) => {
              if (!action) return
              const id = String(action.id ?? index + 1)
              updateLiveAction({
                id,
                description: action.description || action.goal || action.title || `执行步骤 ${index + 1}`,
                result: action.result || action.outcome || action.summary,
                status: 'ready',
              })
            })
          }

          const reportSections =
            parsed.report?.sections || parsed.report_sections || parsed.sections || parsed.final_sections
          if (Array.isArray(reportSections)) {
            reportSections.forEach((section: any, index: number) => {
              if (!section) return
              const id = String(section.id ?? index + 1)
              updateLiveReportSection({
                id,
                heading: section.heading || section.title || `段落 ${index + 1}`,
                content: section.content || section.body || section.summary,
                status: 'ready',
              })
            })
          }

          // Phase 0 summarization support
          // Handle transcript summaries
          if (parsed.key_facts || parsed.key_opinions || parsed.key_datapoints || parsed.topic_areas) {
            console.log('[Phase 0] Transcript summary parsed:', {
              key_facts: parsed.key_facts?.length,
              key_opinions: parsed.key_opinions?.length,
              key_datapoints: parsed.key_datapoints?.length,
              topic_areas: parsed.topic_areas?.length
            })
          }

          // Handle comment summaries
          if (parsed.key_facts_from_comments || parsed.key_opinions_from_comments || parsed.major_themes) {
            console.log('[Phase 0] Comments summary parsed:', {
              key_facts: parsed.key_facts_from_comments?.length,
              key_opinions: parsed.key_opinions_from_comments?.length,
              major_themes: parsed.major_themes?.length,
              sentiment: parsed.sentiment_overview
            })
          }
        }
      } catch (error: any) {
        const message = error?.message || '解析失败'
        const isIncomplete = /not completed/i.test(message) || /Unexpected end of JSON input/i.test(message)
        if (isIncomplete) {
          setParserState((prev) => ({
            root: prev.root,
            status: prev.root ? 'valid' : 'parsing',
            error: prev.root ? undefined : message,
          }))
        } else {
          setParserState({
            root: null,
            status: 'error',
            error: message,
          })
        }
      }
    }, debounceMs)

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
    }
  }, [streamBuffer, enableRepair, debounceMs, setGoals, setPlan, setSynthesizedGoal, updateLiveGoal, updateLivePlanStep, updateLiveInsight, updateLiveAction, updateLiveReportSection])

  return parserState
}
