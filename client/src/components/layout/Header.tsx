import React from 'react'
import { useUiStore } from '../../stores/uiStore'

const Header: React.FC = () => {
  const { sidebarOpen, toggleSidebar } = useUiStore()

  return (
    <header className="bg-neutral-white border-b border-neutral-300 px-6 py-4">
      <div className="flex items-center justify-between">
        {/* Mobile menu button */}
        <button
          onClick={toggleSidebar}
          className="lg:hidden p-2 rounded-lg hover:bg-neutral-300 transition-colors"
          aria-label="Toggle sidebar"
        >
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6h16M4 12h16M4 18h16"
            />
          </svg>
        </button>

        {/* Page title - will be set dynamically based on route */}
        <div className="flex-1">
          <h2 className="text-lg font-semibold text-neutral-black">
            研究工具
          </h2>
        </div>

        {/* Right side actions */}
        <div className="flex items-center space-x-4">
          <p className="text-xs text-neutral-400">
            Research Tool v0.1.0
          </p>
        </div>
      </div>
    </header>
  )
}

export default Header


