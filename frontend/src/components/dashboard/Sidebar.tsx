import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

// Icons
const RepoIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
  </svg>
)

const SearchIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
)

const SettingsIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
)

const ChevronIcon = ({ direction = 'left' }: { direction?: 'left' | 'right' }) => (
  <svg 
    className={`w-4 h-4 transition-transform ${direction === 'right' ? 'rotate-180' : ''}`} 
    fill="none" 
    stroke="currentColor" 
    viewBox="0 0 24 24"
  >
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
  </svg>
)

const DocsIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
  </svg>
)

interface NavItem {
  name: string
  href: string
  icon: React.ReactNode
}

const mainNavItems: NavItem[] = [
  { name: 'Repositories', href: '/dashboard', icon: <RepoIcon /> },
  { name: 'Global Search', href: '/dashboard/search', icon: <SearchIcon /> },
]

const bottomNavItems: NavItem[] = [
  { name: 'Documentation', href: '/docs', icon: <DocsIcon /> },
  { name: 'Settings', href: '/dashboard/settings', icon: <SettingsIcon /> },
]

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const location = useLocation()
  const { session } = useAuth()

  const isActive = (href: string) => {
    if (href === '/dashboard') {
      return location.pathname === '/dashboard' || location.pathname.startsWith('/dashboard/repo/')
    }
    return location.pathname === href
  }

  const NavLink = ({ item }: { item: NavItem }) => (
    <Link
      to={item.href}
      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all group ${
        isActive(item.href)
          ? 'bg-blue-500/10 text-blue-400'
          : 'text-gray-400 hover:text-white hover:bg-white/5'
      }`}
    >
      <span className={`${isActive(item.href) ? 'text-blue-400' : 'text-gray-500 group-hover:text-gray-300'}`}>
        {item.icon}
      </span>
      {!collapsed && (
        <span className="text-sm font-medium truncate">{item.name}</span>
      )}
    </Link>
  )

  return (
    <aside 
      className={`fixed left-0 top-14 bottom-0 z-40 flex flex-col border-r border-white/5 bg-[#09090b] transition-all duration-300 ${
        collapsed ? 'w-16' : 'w-60'
      }`}
    >
      {/* Main Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {mainNavItems.map((item) => (
          <NavLink key={item.href} item={item} />
        ))}
      </nav>

      {/* Bottom Navigation */}
      <div className="p-3 border-t border-white/5 space-y-1">
        {bottomNavItems.map((item) => (
          <NavLink key={item.href} item={item} />
        ))}

        {/* Collapse Toggle */}
        <button
          onClick={onToggle}
          className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-all"
        >
          <ChevronIcon direction={collapsed ? 'right' : 'left'} />
          {!collapsed && <span className="text-sm font-medium">Collapse</span>}
        </button>
      </div>
    </aside>
  )
}
