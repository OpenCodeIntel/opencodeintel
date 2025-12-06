import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TopNav } from './TopNav'
import { Toaster } from '@/components/ui/sonner'

interface DashboardLayoutProps {
  children?: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <div className="min-h-screen bg-[#09090b]">
      {/* Top Navigation */}
      <TopNav 
        onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)}
        sidebarCollapsed={sidebarCollapsed}
      />

      <div className="flex">
        {/* Sidebar */}
        <Sidebar 
          collapsed={sidebarCollapsed} 
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />

        {/* Main Content */}
        <main 
          className={`flex-1 transition-all duration-300 ${
            sidebarCollapsed ? 'ml-16' : 'ml-60'
          }`}
        >
          <div className="p-6">
            {children || <Outlet />}
          </div>
        </main>
      </div>

      <Toaster 
        theme="dark" 
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#111113',
            border: '1px solid rgba(255,255,255,0.1)',
            color: '#fff',
          },
        }}
      />
    </div>
  )
}
