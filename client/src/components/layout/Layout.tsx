import React from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import WorkflowStepper from '../workflow/WorkflowStepper'

interface LayoutProps {
  children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="flex h-screen bg-neutral-light-bg">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <WorkflowStepper />
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}

export default Layout


