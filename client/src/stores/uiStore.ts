import { create } from 'zustand'

interface UIState {
  currentPage: string
  sidebarOpen: boolean
  theme: 'light' | 'dark'
  viewPreferences: {
    showRawJson: boolean
    columnWidth: number
    fontSize: number
  }
  notifications: Array<{
    id: string
    message: string
    type: 'success' | 'error' | 'warning' | 'info'
    timestamp: Date
  }>
  
  // Actions
  setCurrentPage: (page: string) => void
  toggleSidebar: () => void
  setTheme: (theme: 'light' | 'dark') => void
  setViewPreferences: (preferences: Partial<UIState['viewPreferences']>) => void
  addNotification: (message: string, type?: UIState['notifications'][0]['type']) => void
  removeNotification: (id: string) => void
}

export const useUiStore = create<UIState>((set) => ({
  currentPage: '/',
  sidebarOpen: false,
  theme: 'light',
  viewPreferences: {
    showRawJson: false,
    columnWidth: 400,
    fontSize: 16,
  },
  notifications: [],
  
  setCurrentPage: (page) => set({ currentPage: page }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setTheme: (theme) => set({ theme }),
  setViewPreferences: (preferences) =>
    set((state) => ({
      viewPreferences: { ...state.viewPreferences, ...preferences },
    })),
  addNotification: (message, type = 'info') => {
    const notification = {
      id: Date.now().toString(),
      message,
      type,
      timestamp: new Date(),
    }
    set((state) => ({
      notifications: [...state.notifications, notification],
    }))
    // Auto-remove after 5 seconds
    setTimeout(() => {
      set((state) => ({
        notifications: state.notifications.filter((n) => n.id !== notification.id),
      }))
    }, 5000)
  },
  removeNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),
}))





