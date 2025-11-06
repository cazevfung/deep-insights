// Utility functions for sorting and grouping progress items

export interface ScrapingItem {
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

export type ItemStatus = ScrapingItem['status']

export interface GroupedItems {
  status: ItemStatus
  items: ScrapingItem[]
  label: string
  icon: string
  defaultCollapsed: boolean
}

/**
 * Normalize status format (handle both snake_case and kebab-case from backend)
 */
const normalizeStatus = (status: string): ItemStatus => {
  // Convert snake_case to kebab-case
  if (status === 'in_progress') {
    return 'in-progress'
  }
  // Ensure valid status
  if (['pending', 'in-progress', 'completed', 'failed'].includes(status)) {
    return status as ItemStatus
  }
  // Default to pending for unknown statuses
  return 'pending'
}

/**
 * Sort items by status priority, then by newest first
 */
export const sortItems = (items: ScrapingItem[]): ScrapingItem[] => {
  const statusPriority: Record<ItemStatus, number> = {
    'in-progress': 1,
    'pending': 2,
    'completed': 3,
    'failed': 4,
  }

  return [...items].sort((a, b) => {
    // Normalize statuses before comparison
    const aStatus = normalizeStatus(a.status)
    const bStatus = normalizeStatus(b.status)
    
    // First sort by status priority
    const statusDiff = statusPriority[aStatus] - statusPriority[bStatus]
    if (statusDiff !== 0) return statusDiff

    // Then by newest first (most recent started_at first)
    const aTime = a.started_at ? new Date(a.started_at).getTime() : 0
    const bTime = b.started_at ? new Date(b.started_at).getTime() : 0
    return bTime - aTime // Descending (newest first)
  })
}

/**
 * Group items by status
 */
export const groupItemsByStatus = (items: ScrapingItem[]): GroupedItems[] => {
  const sorted = sortItems(items)

  const groups: Record<ItemStatus, ScrapingItem[]> = {
    'in-progress': [],
    'pending': [],
    'completed': [],
    'failed': [],
  }

  sorted.forEach((item) => {
    // Normalize status before grouping
    const normalizedStatus = normalizeStatus(item.status)
    // Create a copy with normalized status
    const normalizedItem = { ...item, status: normalizedStatus }
    groups[normalizedStatus].push(normalizedItem)
  })

  const groupConfig: Array<{
    status: ItemStatus
    label: string
    icon: string
    defaultCollapsed: boolean
  }> = [
    {
      status: 'in-progress',
      label: '处理中',
      icon: 'refresh',
      defaultCollapsed: false,
    },
    {
      status: 'pending',
      label: '等待中',
      icon: 'clock',
      defaultCollapsed: false,
    },
    {
      status: 'completed',
      label: '已完成',
      icon: 'check-circle',
      defaultCollapsed: groups.completed.length > 10, // Auto-collapse if > 10
    },
    {
      status: 'failed',
      label: '失败',
      icon: 'x-circle',
      defaultCollapsed: false,
    },
  ]

  return groupConfig
    .map((config) => ({
      ...config,
      items: groups[config.status],
    }))
    .filter((group) => group.items.length > 0) // Only show groups with items
}

/**
 * Get item unique identifier
 */
export const getItemId = (item: ScrapingItem): string => {
  return item.link_id || item.url || ''
}

