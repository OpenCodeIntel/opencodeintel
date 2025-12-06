import { Link } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { useState } from 'react'

interface TopNavProps {
  onToggleSidebar: () => void
  sidebarCollapsed: boolean
  onOpenCommandPalette?: () => void
}

// Icons
const MenuIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
  </svg>
)

const SearchIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
)

const GitHubIcon = () => (
  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
    <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
  </svg>
)

const CodeIntelLogo = () => (
  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
    <span className="text-white font-bold text-sm">CI</span>
  </div>
)

export function TopNav({ onToggleSidebar, sidebarCollapsed, onOpenCommandPalette }: TopNavProps) {
  const { session, signOut } = useAuth()
  const [showUserMenu, setShowUserMenu] = useState(false)

  const userEmail = session?.user?.email || 'User'
  const userInitial = userEmail.charAt(0).toUpperCase()

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-14 border-b border-white/5 bg-[#09090b]/80 backdrop-blur-xl">
      <div className="h-full px-4 flex items-center justify-between">
        {/* Left Section */}
        <div className="flex items-center gap-4">
          <button
            onClick={onToggleSidebar}
            className="p-2 text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors lg:hidden"
          >
            <MenuIcon />
          </button>

          <Link to="/dashboard" className="flex items-center gap-3">
            <CodeIntelLogo />
            <span className="font-semibold text-white hidden sm:block">CodeIntel</span>
            <span className="text-xs text-gray-500 hidden md:block">MCP Server</span>
          </Link>
        </div>

        {/* Center - Command Palette Trigger */}
        <button 
          className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-all max-w-xs"
          onClick={onOpenCommandPalette}
        >
          <SearchIcon />
          <span className="text-sm">Search...</span>
          <kbd className="ml-auto text-xs bg-white/10 px-1.5 py-0.5 rounded">⌘K</kbd>
        </button>

        {/* Right Section */}
        <div className="flex items-center gap-3">
          {/* GitHub Link */}
          <a
            href="https://github.com/opencodeintel/opencodeintel"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 text-gray-400 hover:text-white transition-colors"
          >
            <GitHubIcon />
          </a>

          {/* User Menu */}
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-2 p-1 rounded-lg hover:bg-white/5 transition-colors"
            >
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <span className="text-white text-sm font-medium">{userInitial}</span>
              </div>
            </button>

            {/* Dropdown */}
            {showUserMenu && (
              <>
                <div 
                  className="fixed inset-0 z-40" 
                  onClick={() => setShowUserMenu(false)}
                />
                <div className="absolute right-0 top-full mt-2 w-56 bg-[#111113] border border-white/10 rounded-xl shadow-xl z-50 py-2">
                  <div className="px-4 py-2 border-b border-white/5">
                    <p className="text-sm text-white font-medium truncate">{userEmail}</p>
                    <p className="text-xs text-gray-500">Free Plan</p>
                  </div>
                  <div className="py-1">
                    <Link
                      to="/dashboard/settings"
                      className="block px-4 py-2 text-sm text-gray-300 hover:bg-white/5 transition-colors"
                      onClick={() => setShowUserMenu(false)}
                    >
                      Settings
                    </Link>
                    <Link
                      to="/docs"
                      className="block px-4 py-2 text-sm text-gray-300 hover:bg-white/5 transition-colors"
                      onClick={() => setShowUserMenu(false)}
                    >
                      Documentation
                    </Link>
                  </div>
                  <div className="border-t border-white/5 py-1">
                    <button
                      onClick={() => {
                        signOut()
                        setShowUserMenu(false)
                      }}
                      className="block w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-white/5 transition-colors"
                    >
                      Sign out
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
