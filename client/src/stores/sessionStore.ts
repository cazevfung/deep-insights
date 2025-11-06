import { create } from 'zustand'

interface QualityAssessment {
  quality_flags: Array<{
    type: string
    message: string
    severity: string
  }>
  quality_score: number
  summary: string
  statistics: {
    total_items: number
    total_words: number
    avg_words_per_item: number
    items_with_comments: number
    comment_coverage: number
    unique_sources: number
    sources: string[]
  }
}

interface ResearchRole {
  role: string
  rationale: string
}

interface SynthesizedGoal {
  comprehensive_topic: string
  component_questions: string[]
  unifying_theme: string
  research_scope: string
}

interface ComponentGoal {
  id: number
  goal_text: string
  rationale: string
  uses: string[]
  sources: string[]
}

interface StepData {
  step_id: number
  findings: any
  insights: string
  confidence: number
  timestamp: string
}

interface SessionState {
  sessionId: string | null
  sessionData: any | null
  
  // Session metadata
  metadata: {
    created_at: string
    batch_id: string
    selected_goal: string | null
    research_plan: any
    status: string
  } | null
  
  // Quality assessment
  qualityAssessment: QualityAssessment | null
  
  // Research role
  researchRole: ResearchRole | null
  
  // Synthesized goal
  synthesizedGoal: SynthesizedGoal | null
  
  // Component goals
  componentGoals: ComponentGoal[]
  
  // Scratchpad (step data)
  scratchpad: Record<string, StepData>
  
  // Final report
  finalReport: string | null
  
  // Actions
  loadSession: (sessionId: string) => Promise<void>
  updateSessionData: (data: any) => void
  updateStep: (stepId: string, stepData: StepData) => void
}

export const useSessionStore = create<SessionState>((set) => ({
  sessionId: null,
  sessionData: null,
  metadata: null,
  qualityAssessment: null,
  researchRole: null,
  synthesizedGoal: null,
  componentGoals: [],
  scratchpad: {},
  finalReport: null,
  
  loadSession: async (sessionId) => {
    try {
      // TODO: Fetch session data from API
      // const response = await fetch(`/api/sessions/${sessionId}`)
      // const data = await response.json()
      
      // For now, just set the session ID
      set({ sessionId })
    } catch (error) {
      console.error('Failed to load session:', error)
    }
  },
  
  updateSessionData: (data) => set({ sessionData: data }),
  
  updateStep: (stepId, stepData) =>
    set((state) => ({
      scratchpad: {
        ...state.scratchpad,
        [stepId]: stepData,
      },
    })),
}))



