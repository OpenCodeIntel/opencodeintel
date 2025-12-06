import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TopNav } from './TopNav'
import { CommandPalette } from './CommandPalette'
import { Toaster } from '@/components/ui/sonner'
import { useKeyboardShortcut, SHORTCUTS } from '../../hooks/useKeyboardShortcut'

interface DashboardLayoutProps {
  children?: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false)

  // Keyboard shortcuts
  useKeyboardShortcut(SHORTCUTS.COMMAND_PALETTE, () => {
    setCommandPaletteOpen(true)
  })

  useKeyboardShortcut(SHORTCUTS.TOGGLE_SIDEBAR, () => {
    setSidebarCollapsed(prev => !prev)
  })

  return (
    <div className="min-h-screen bg-[#09090b]">
      {/* Top Navigation */}
      <TopNav 
        onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)}
        sidebarCollapsed={sidebarCollapsed}
        onOpenCommandPalette={() => setCommandPaletteOpen(true)}
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

      {/* Command Palette */}
      <CommandPalette 
        isOpen={commandPaletteOpen} 
        onClose={() => setCommandPaletteOpen(false)} 
      />

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
