import React from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import PhaseInteractionPanel from '../phaseCommon/PhaseInteractionPanel'
import { useWorkflowStore } from '../../stores/workflowStore'
import { useWebSocket } from '../../hooks/useWebSocket'

interface LayoutProps {
  children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const batchId = useWorkflowStore((state) => state.batchId || '')
  const { sendMessage } = useWebSocket(batchId)

  return (
    <div className="flex h-screen bg-neutral-light-bg">
      {/* Sidebar: Always visible */}
      <Sidebar />
      
      {/* Main content area: Header only covers this area */}
      <main className="flex-1 flex flex-col min-h-0">
        <Header />
        <div className="flex-1 overflow-y-auto px-6 pt-6 pb-10">
          {children}
        </div>
      </main>
      
      {/* Right column: Full height, independent of Header */}
      <aside className="hidden lg:flex p-4 lg:w-[640px] flex-col h-full">
        <PhaseInteractionPanel onSendMessage={sendMessage} />
      </aside>
    </div>
  )
}

export default Layout


