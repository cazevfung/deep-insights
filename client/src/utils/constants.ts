/**
 * Application constants
 */

export const API_BASE_URL = '/api'
export const WS_BASE_URL = 'ws://localhost:3000' // Will be proxied to localhost:3001 by Vite

export const PHASES = {
  INPUT: 'input',
  SCRAPING: 'scraping',
  RESEARCH: 'research',
  PHASE3: 'phase3',
  PHASE4: 'phase4',
  COMPLETE: 'complete',
} as const

export const RESEARCH_PHASES = {
  PHASE_0_5: '0.5',
  PHASE_1: '1',
  PHASE_2: '2',
} as const

export const STATUS_COLORS = {
  success: 'bg-supportive-green',
  error: 'bg-secondary-500',
  warning: 'bg-supportive-orange',
  info: 'bg-supportive-blue',
  pending: 'bg-neutral-400',
} as const


