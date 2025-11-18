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
      
      <div className="flex-1 flex flex-col min-h-0">
        <Header />
        
        {/* Main content area with right column */}
        <div className="flex flex-1 flex-col lg:flex-row min-h-0 overflow-hidden">
          <main className="flex-1 overflow-y-auto px-6 pt-6 pb-10 order-1">
            {children}
          </main>
          {/* Right column: Always visible */}
          <aside className="order-2 px-6 pt-6 pb-10 lg:flex-none lg:w-[520px] flex flex-col min-h-0">
            <PhaseInteractionPanel onSendMessage={sendMessage} />
          </aside>
        </div>
      </div>
    </div>
  )
}

export default Layout


