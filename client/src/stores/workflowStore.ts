import { create } from 'zustand'

interface ScrapingItem {
  link_id?: string
  url: string
  status: 'pending' | 'in-progress' | 'completed' | 'failed'
  error?: string
  current_stage?: string
  stage_progress?: number
  overall_progress?: number
  status_message?: string
  started_at?: string
  completed_at?: string
  source?: string
  word_count?: number
  bytes_downloaded?: number
  total_bytes?: number
}

interface SessionStep {
  step_id: number
  findings: {
    summary: string
    points_of_interest: {
      key_claims: Array<{
        claim: string
        supporting_evidence: string
      }>
      notable_evidence: Array<{
        evidence_type: string
        description: string
      }>
    }
    analysis_details: {
      five_whys: string[]
      assumptions: string[]
      uncertainties: string[]
    }
  }
  insights: string
  confidence: number
  timestamp: string
}

interface WorkflowState {
  currentPhase: 'input' | 'scraping' | 'research' | 'phase3' | 'phase4' | 'complete'
  batchId: string | null
  workflowId: string | null
  workflowStarted: boolean  // Track if workflow has been started for current batchId
  
  // Progress tracking
  overallProgress: number
  currentStep: string | null
  stepProgress: number
  
  // Scraping phase
  scrapingStatus: {
    total: number
    completed: number
    failed: number
    inProgress: number
    items: ScrapingItem[]
  }
  
  // Cancellation state
  cancelled: boolean
  cancellationInfo: {
    cancelled_at?: string
    reason?: string
    state_at_cancellation?: any
  } | null
  
  // Research agent phase
  researchAgentStatus: {
    phase: '0.5' | '1' | '2'
    currentAction: string | null
    waitingForUser: boolean
    userInputRequired: {
      type: 'goal_selection' | 'plan_confirmation' | 'custom_input'
      prompt_id?: string
      prompt?: string
      data?: any
    } | null
    streamBuffer: string
    goals: Array<{
      id: number
      goal_text: string
      uses?: string[]
    }> | null
    plan: Array<{
      step_id: number
      goal: string
      required_data?: string
      chunk_strategy?: string
      notes?: string
    }> | null
    synthesizedGoal: {
      comprehensive_topic: string
      component_questions: string[]
      unifying_theme?: string
    } | null
  }
  
  // Phase 3
  phase3Steps: SessionStep[]
  currentStepId: number | null
  
  // Phase 4
  finalReport: {
    content: string
    generatedAt: string
    status: 'generating' | 'ready' | 'error'
  } | null
  
  // Error handling
  errors: Array<{
    phase: string
    message: string
    timestamp: string
  }>
  
  // Actions
  setBatchId: (batchId: string) => void
  setWorkflowStarted: (started: boolean) => void
  setCurrentPhase: (phase: WorkflowState['currentPhase']) => void
  updateProgress: (progress: number) => void
  updateScrapingStatus: (status: Partial<WorkflowState['scrapingStatus']>) => void
  updateScrapingItem: (url: string, status: ScrapingItem['status'], error?: string) => void
  updateScrapingItemProgress: (link_id: string | undefined, url: string, progress: Partial<ScrapingItem>) => void
  setCancelled: (cancelled: boolean, cancellationInfo?: WorkflowState['cancellationInfo']) => void
  updateResearchAgentStatus: (status: Partial<WorkflowState['researchAgentStatus']>) => void
  setGoals: (goals: WorkflowState['researchAgentStatus']['goals']) => void
  setPlan: (plan: WorkflowState['researchAgentStatus']['plan']) => void
  setSynthesizedGoal: (goal: WorkflowState['researchAgentStatus']['synthesizedGoal']) => void
  appendStreamToken: (token: string) => void
  clearStreamBuffer: () => void
  addPhase3Step: (step: SessionStep) => void
  setFinalReport: (report: WorkflowState['finalReport']) => void
  addError: (phase: string, message: string) => void
  reset: () => void
  validateState: () => { isValid: boolean; errors: string[] }
}

const initialState: Omit<WorkflowState, keyof {
  setBatchId: any
  setWorkflowStarted: any
  setCurrentPhase: any
  updateProgress: any
  updateScrapingStatus: any
  updateScrapingItem: any
  updateResearchAgentStatus: any
  appendStreamToken: any
  clearStreamBuffer: any
  addPhase3Step: any
  setFinalReport: any
  addError: any
  reset: any
  validateState: any
}> = {
  currentPhase: 'input',
  batchId: null,
  workflowId: null,
  workflowStarted: false,
  overallProgress: 0,
  currentStep: null,
  stepProgress: 0,
  scrapingStatus: {
    total: 0,
    completed: 0,
    failed: 0,
    inProgress: 0,
    items: [],
  },
  researchAgentStatus: {
    phase: '0.5',
    currentAction: null,
    waitingForUser: false,
    userInputRequired: null,
    streamBuffer: '',
    goals: null,
    plan: null,
    synthesizedGoal: null,
  },
  phase3Steps: [],
  currentStepId: null,
  finalReport: null,
  errors: [],
  cancelled: false,
  cancellationInfo: null,
}

export const useWorkflowStore = create<WorkflowState>((set) => ({
  ...initialState,
  
  setBatchId: (batchId) => {
    // Reset ALL workflow state when batchId changes (new session)
    set((state) => {
      // If batchId is the same, don't reset
      if (state.batchId === batchId) {
        return { batchId, workflowStarted: state.workflowStarted }
      }
      
      // If batchId changed, reset all workflow state to initial values
      return {
        batchId,
        workflowId: null,
        workflowStarted: false,
        currentPhase: 'input',
        overallProgress: 0,
        currentStep: null,
        stepProgress: 0,
        scrapingStatus: {
          total: 0,
          completed: 0,
          failed: 0,
          inProgress: 0,
          items: [],
        },
        cancelled: false,
        cancellationInfo: null,
        researchAgentStatus: {
          phase: '0.5',
          currentAction: null,
          waitingForUser: false,
          userInputRequired: null,
          streamBuffer: '',
          goals: null,
          plan: null,
          synthesizedGoal: null,
        },
        phase3Steps: [],
        currentStepId: null,
        finalReport: null,
        errors: [],
      }
    })
  },
  setWorkflowStarted: (started) => set({ workflowStarted: started }),
  setCurrentPhase: (phase) => set({ currentPhase: phase }),
  updateProgress: (progress) => set({ overallProgress: progress }),
  updateScrapingStatus: (status) =>
    set((state) => ({
      scrapingStatus: { ...state.scrapingStatus, ...status },
    })),
  updateScrapingItem: (url, status, error) =>
    set((state) => {
      const items = state.scrapingStatus.items.map((item) =>
        item.url === url ? { ...item, status, error } : item
      )
      const completed = items.filter((i) => i.status === 'completed').length
      const failed = items.filter((i) => i.status === 'failed').length
      const inProgress = items.filter((i) => i.status === 'in-progress').length
      
      return {
        scrapingStatus: {
          ...state.scrapingStatus,
          items,
          completed,
          failed,
          inProgress,
        },
      }
    }),
  updateScrapingItemProgress: (link_id, url, progress) =>
    set((state) => {
      const items = state.scrapingStatus.items.map((item) => {
        // Match by link_id if available, otherwise by url
        const matches = link_id ? item.link_id === link_id : item.url === url
        if (matches) {
          return { ...item, ...progress, status: progress.status || item.status || 'in-progress' }
        }
        return item
      })
      
      // If item doesn't exist, add it
      const exists = items.some((item) => 
        (link_id && item.link_id === link_id) || (!link_id && item.url === url)
      )
      if (!exists) {
        items.push({
          link_id,
          url,
          status: progress.status || 'in-progress',
          ...progress,
        })
      }
      
      const completed = items.filter((i) => i.status === 'completed').length
      const failed = items.filter((i) => i.status === 'failed').length
      const inProgress = items.filter((i) => i.status === 'in-progress' || i.status === 'pending').length
      
      return {
        scrapingStatus: {
          ...state.scrapingStatus,
          items,
          completed,
          failed,
          inProgress,
        },
      }
    }),
  updateResearchAgentStatus: (status) =>
    set((state) => ({
      researchAgentStatus: { ...state.researchAgentStatus, ...status },
    })),
  setGoals: (goals) =>
    set((state) => ({
      researchAgentStatus: { ...state.researchAgentStatus, goals },
    })),
  setPlan: (plan) =>
    set((state) => ({
      researchAgentStatus: { ...state.researchAgentStatus, plan },
    })),
  setSynthesizedGoal: (synthesizedGoal) =>
    set((state) => ({
      researchAgentStatus: { ...state.researchAgentStatus, synthesizedGoal },
    })),
  appendStreamToken: (token) =>
    set((state) => ({
      researchAgentStatus: {
        ...state.researchAgentStatus,
        streamBuffer: state.researchAgentStatus.streamBuffer + token,
      },
    })),
  clearStreamBuffer: () =>
    set((state) => ({
      researchAgentStatus: {
        ...state.researchAgentStatus,
        streamBuffer: '',
      },
    })),
  addPhase3Step: (step) =>
    set((state) => {
      // Use Set for O(1) lookup to check if step already exists
      // This prevents race conditions when multiple messages arrive quickly
      const stepIds = new Set(state.phase3Steps.map((s) => s.step_id))
      
      let updatedSteps: SessionStep[]
      if (stepIds.has(step.step_id)) {
        // Step already exists - update it and remove any duplicates
        // Use Map to ensure only one entry per step_id (keeps the latest)
        const stepsMap = new Map<number, SessionStep>()
        
        // First, add all existing steps (this will deduplicate if there are already duplicates)
        state.phase3Steps.forEach((s) => {
          if (s.step_id !== step.step_id) {
            stepsMap.set(s.step_id, s)
          }
        })
        
        // Then add/update the new step
        stepsMap.set(step.step_id, step)
        
        updatedSteps = Array.from(stepsMap.values())
      } else {
        // New step - add it
        updatedSteps = [...state.phase3Steps, step]
      }
      
      // Sort steps by step_id to ensure correct order
      updatedSteps.sort((a, b) => a.step_id - b.step_id)
      
      return {
        phase3Steps: updatedSteps,
        currentStepId: step.step_id,
      }
    }),
  setFinalReport: (report) => set({ finalReport: report }),
  addError: (phase, message) =>
    set((state) => ({
      errors: [
        ...state.errors,
        {
          phase,
          message,
          timestamp: new Date().toISOString(),
        },
      ],
    })),
  setCancelled: (cancelled, cancellationInfo) =>
    set({ cancelled, cancellationInfo: cancellationInfo || null }),
  reset: () => set({ ...initialState, workflowStarted: false }),
  validateState: () => {
    const state = useWorkflowStore.getState()
    const errors: string[] = []

    // Validate that if batchId exists, workflow state is consistent
    if (state.batchId) {
      // If scrapingStatus has items, they should belong to current batchId
      if (state.scrapingStatus.items.length > 0 && !state.batchId) {
        errors.push('Scraping items exist but no batchId set')
      }

      // If research goals exist, scraping should be completed
      if (state.researchAgentStatus.goals !== null && state.scrapingStatus.completed === 0) {
        errors.push('Research goals exist but scraping not completed')
      }

      // If phase3 steps exist, research plan should exist
      if (state.phase3Steps.length > 0 && state.researchAgentStatus.plan === null) {
        errors.push('Phase3 steps exist but no research plan found')
      }

      // If final report exists, phase3 should be completed
      if (state.finalReport !== null && state.researchAgentStatus.plan !== null) {
        const expectedSteps = state.researchAgentStatus.plan.length
        if (state.phase3Steps.length < expectedSteps) {
          errors.push(`Final report exists but phase3 incomplete (${state.phase3Steps.length}/${expectedSteps} steps)`)
        }
      }

      // Workflow started should be true if there's any progress
      if (state.workflowStarted === false && (
        state.scrapingStatus.total > 0 ||
        state.researchAgentStatus.goals !== null ||
        state.phase3Steps.length > 0
      )) {
        errors.push('Workflow has progress but workflowStarted is false')
      }
    } else {
      // If no batchId, all state should be reset
      if (state.scrapingStatus.total > 0 ||
          state.researchAgentStatus.goals !== null ||
          state.phase3Steps.length > 0 ||
          state.finalReport !== null) {
        errors.push('No batchId but workflow state exists (state should be reset)')
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
    }
  },
}))


