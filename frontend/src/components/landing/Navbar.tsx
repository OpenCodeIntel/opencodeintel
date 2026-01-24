import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ThemeToggle } from './ThemeToggle'
import { GitHubStars } from './GitHubStars'
import { MobileMenu } from './MobileMenu'

interface NavbarProps {
  minimal?: boolean
}

const NAV_LINKS = [
  { label: 'Features', href: '#features' },
  { label: 'Pricing', href: '#pricing' },
  { label: 'Docs', href: '/docs' },
]

/**
 * Renders the top navigation bar with logo, responsive navigation links, and action controls.
 *
 * The bar updates its background and border when the page is scrolled beyond 20px, and it cleans up the scroll listener on unmount. When `minimal` is true, desktop navigation links and right-side controls are hidden. Sign in and Get Started buttons navigate to '/login' and '/signup' respectively; the mobile menu receives a navigation handler.
 *
 * @param minimal - When true, hide desktop navigation links and right-side controls
 * @returns The rendered navbar element
 */
export function Navbar({ minimal }: NavbarProps) {
  const navigate = useNavigate()
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <nav className={`
      fixed top-0 left-0 right-0 z-50 transition-all duration-300
      ${scrolled 
        ? 'bg-background/80 backdrop-blur-xl border-b border-white/[0.06] dark:border-white/[0.06] light:border-black/[0.06]' 
        : 'bg-transparent'
      }
    `}>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
        {/* Logo */}
        <a href="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent to-blue-600 flex items-center justify-center shadow-lg shadow-accent/20">
            <span className="text-white font-bold text-sm">CI</span>
          </div>
          <span className="font-semibold text-foreground">CodeIntel</span>
        </a>

        {/* Desktop nav */}
        {!minimal && (
          <>
            <div className="hidden md:flex items-center gap-1">
              {NAV_LINKS.map(link => (
                <a
                  key={link.href}
                  href={link.href}
                  className="px-3 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-white/5 dark:hover:bg-white/5 light:hover:bg-black/5"
                >
                  {link.label}
                </a>
              ))}
            </div>

            <div className="hidden md:flex items-center gap-3">
              <GitHubStars />
              <ThemeToggle />
              <div className="w-px h-6 bg-white/10 dark:bg-white/10 light:bg-black/10" />
              <button
                onClick={() => navigate('/login')}
                className="px-3 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                Sign in
              </button>
              <button
                onClick={() => navigate('/signup')}
                className="px-4 py-2 text-sm font-medium text-white rounded-lg bg-accent hover:bg-accent/90 transition-colors shadow-lg shadow-accent/20"
              >
                Get Started
              </button>
            </div>

            {/* Mobile */}
            <div className="flex md:hidden items-center gap-2">
              <ThemeToggle />
              <MobileMenu onNavigate={navigate} />
            </div>
          </>
        )}
      </div>
    </nav>
  )
}