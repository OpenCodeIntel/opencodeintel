import { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { API_URL } from '../../config/api'

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

interface Repository {
  id: string
  name: string
  branch: string
  status: string
}

interface CommandItem {
  id: string
  type: 'repo' | 'action' | 'navigation'
  title: string
  subtitle?: string
  icon: string
  shortcut?: string
  action: () => void
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [repos, setRepos] = useState<Repository[]>([])
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const { session, signOut } = useAuth()

  // Fetch repos for search
  useEffect(() => {
    if (isOpen && session?.access_token) {
      fetchRepos()
    }
  }, [isOpen, session])

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
      setTimeout(() => inputRef.current?.focus(), 10)
    }
  }, [isOpen])

  // Handle keyboard navigation
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex(i => Math.min(i + 1, filteredItems.length - 1))
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex(i => Math.max(i - 1, 0))
          break
        case 'Enter':
          e.preventDefault()
          if (filteredItems[selectedIndex]) {
            filteredItems[selectedIndex].action()
            onClose()
          }
          break
        case 'Escape':
          e.preventDefault()
          onClose()
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, selectedIndex, query])

  const fetchRepos = async () => {
    try {
      const response = await fetch(`${API_URL}/api/repos`, {
        headers: { 'Authorization': `Bearer ${session?.access_token}` }
      })
      const data = await response.json()
      setRepos(data.repositories || [])
    } catch (error) {
      console.error('Error fetching repos:', error)
    }
  }

  // Build command items
  const allItems: CommandItem[] = useMemo(() => {
    const items: CommandItem[] = []

    // Repositories
    repos.forEach(repo => {
      items.push({
        id: `repo-${repo.id}`,
        type: 'repo',
        title: repo.name,
        subtitle: `${repo.branch} • ${repo.status}`,
        icon: '📦',
        action: () => navigate(`/dashboard/repo/${repo.id}`)
      })
    })

    // Actions
    items.push({
      id: 'action-add-repo',
      type: 'action',
      title: 'Add Repository',
      subtitle: 'Clone and index a new repository',
      icon: '➕',
      action: () => {
        // Trigger add repo modal - dispatch custom event
        window.dispatchEvent(new CustomEvent('openAddRepo'))
        navigate('/dashboard')
      }
    })

    items.push({
      id: 'action-refresh',
      type: 'action',
      title: 'Refresh Repositories',
      subtitle: 'Reload the repository list',
      icon: '🔄',
      action: () => {
        window.location.reload()
      }
    })

    // Navigation
    items.push({
      id: 'nav-dashboard',
      type: 'navigation',
      title: 'Go to Dashboard',
      subtitle: 'View all repositories',
      icon: '🏠',
      action: () => navigate('/dashboard')
    })

    items.push({
      id: 'nav-settings',
      type: 'navigation',
      title: 'Settings',
      subtitle: 'Account and preferences',
      icon: '⚙️',
      action: () => navigate('/dashboard/settings')
    })

    items.push({
      id: 'nav-docs',
      type: 'navigation',
      title: 'Documentation',
      subtitle: 'Learn how to use CodeIntel',
      icon: '📚',
      action: () => window.open('/docs', '_blank')
    })

    items.push({
      id: 'action-signout',
      type: 'action',
      title: 'Sign Out',
      subtitle: 'Log out of your account',
      icon: '🚪',
      action: () => signOut()
    })

    return items
  }, [repos, navigate, signOut])

  // Filter items based on query
  const filteredItems = useMemo(() => {
    if (!query.trim()) return allItems

    const lowerQuery = query.toLowerCase()
    return allItems.filter(item =>
      item.title.toLowerCase().includes(lowerQuery) ||
      item.subtitle?.toLowerCase().includes(lowerQuery)
    )
  }, [allItems, query])

  // Reset selection when filter changes
  useEffect(() => {
    setSelectedIndex(0)
  }, [query])

  // Group items by type
  const groupedItems = useMemo(() => {
    const groups: { [key: string]: CommandItem[] } = {
      repo: [],
      action: [],
      navigation: []
    }

    filteredItems.forEach(item => {
      groups[item.type].push(item)
    })

    return groups
  }, [filteredItems])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-xl mx-4 bg-[#111113] border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-white/5">
          <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search commands, repos, actions..."
            className="flex-1 bg-transparent text-white placeholder:text-gray-500 outline-none text-base"
          />
          <kbd className="px-2 py-1 text-xs text-gray-500 bg-white/5 border border-white/10 rounded">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-[400px] overflow-y-auto py-2">
          {filteredItems.length === 0 ? (
            <div className="px-4 py-8 text-center text-gray-500">
              No results found for "{query}"
            </div>
          ) : (
            <>
              {/* Repositories */}
              {groupedItems.repo.length > 0 && (
                <div>
                  <div className="px-4 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">
                    Repositories
                  </div>
                  {groupedItems.repo.map((item, idx) => {
                    const globalIndex = filteredItems.indexOf(item)
                    return (
                      <CommandItem
                        key={item.id}
                        item={item}
                        isSelected={selectedIndex === globalIndex}
                        onClick={() => {
                          item.action()
                          onClose()
                        }}
                        onMouseEnter={() => setSelectedIndex(globalIndex)}
                      />
                    )
                  })}
                </div>
              )}

              {/* Actions */}
              {groupedItems.action.length > 0 && (
                <div>
                  <div className="px-4 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">
                    Actions
                  </div>
                  {groupedItems.action.map((item) => {
                    const globalIndex = filteredItems.indexOf(item)
                    return (
                      <CommandItem
                        key={item.id}
                        item={item}
                        isSelected={selectedIndex === globalIndex}
                        onClick={() => {
                          item.action()
                          onClose()
                        }}
                        onMouseEnter={() => setSelectedIndex(globalIndex)}
                      />
                    )
                  })}
                </div>
              )}

              {/* Navigation */}
              {groupedItems.navigation.length > 0 && (
                <div>
                  <div className="px-4 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">
                    Navigation
                  </div>
                  {groupedItems.navigation.map((item) => {
                    const globalIndex = filteredItems.indexOf(item)
                    return (
                      <CommandItem
                        key={item.id}
                        item={item}
                        isSelected={selectedIndex === globalIndex}
                        onClick={() => {
                          item.action()
                          onClose()
                        }}
                        onMouseEnter={() => setSelectedIndex(globalIndex)}
                      />
                    )
                  })}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-white/5 flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-white/5 border border-white/10 rounded">↑↓</kbd>
              navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-white/5 border border-white/10 rounded">↵</kbd>
              select
            </span>
          </div>
          <span className="text-gray-600">CodeIntel</span>
        </div>
      </div>
    </div>
  )
}

// Individual command item component
function CommandItem({ 
  item, 
  isSelected, 
  onClick, 
  onMouseEnter 
}: { 
  item: CommandItem
  isSelected: boolean
  onClick: () => void
  onMouseEnter: () => void
}) {
  return (
    <button
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
        isSelected ? 'bg-blue-500/10' : 'hover:bg-white/5'
      }`}
    >
      <span className="text-lg">{item.icon}</span>
      <div className="flex-1 min-w-0">
        <div className={`text-sm font-medium ${isSelected ? 'text-blue-400' : 'text-white'}`}>
          {item.title}
        </div>
        {item.subtitle && (
          <div className="text-xs text-gray-500 truncate">{item.subtitle}</div>
        )}
      </div>
      {item.shortcut && (
        <kbd className="px-2 py-1 text-xs text-gray-500 bg-white/5 border border-white/10 rounded">
          {item.shortcut}
        </kbd>
      )}
    </button>
  )
}
