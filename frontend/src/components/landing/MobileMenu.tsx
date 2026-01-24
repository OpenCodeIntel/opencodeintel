import { Menu, X } from 'lucide-react'
import { Sheet, SheetContent, SheetTrigger, SheetClose } from '@/components/ui/sheet'
import { ThemeToggle } from './ThemeToggle'
import { GitHubStars } from './GitHubStars'

interface MobileMenuProps {
  onNavigate: (path: string) => void
}

const NAV_LINKS = [
  { label: 'Features', href: '#features' },
  { label: 'Pricing', href: '#pricing' },
  { label: 'Docs', href: '/docs' },
]

/**
 * Render a right-anchored slide-out mobile navigation menu with navigation links, authentication actions, and bottom utilities.
 *
 * @param onNavigate - Callback invoked with a path string when a navigation action is requested (called with '/login' for Sign in and '/signup' for Get Started).
 * @returns A JSX element that displays the mobile navigation sheet.
 */
export function MobileMenu({ onNavigate }: MobileMenuProps) {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <button className="p-2 rounded-lg text-zinc-400 hover:text-foreground hover:bg-white/5 transition-colors md:hidden">
          <Menu className="w-5 h-5" />
        </button>
      </SheetTrigger>
      <SheetContent side="right" className="w-[300px] bg-background border-l border-white/10">
        <div className="flex flex-col h-full pt-8">
          <nav className="flex flex-col gap-1">
            {NAV_LINKS.map(link => (
              <SheetClose asChild key={link.href}>
                <a
                  href={link.href}
                  className="px-4 py-3 text-zinc-300 hover:text-foreground hover:bg-white/5 rounded-lg transition-colors"
                >
                  {link.label}
                </a>
              </SheetClose>
            ))}
          </nav>

          <div className="border-t border-white/10 my-6" />

          <div className="flex flex-col gap-3 px-4">
            <SheetClose asChild>
              <button
                onClick={() => onNavigate('/login')}
                className="w-full py-2.5 text-sm text-zinc-300 hover:text-foreground transition-colors"
              >
                Sign in
              </button>
            </SheetClose>
            <SheetClose asChild>
              <button
                onClick={() => onNavigate('/signup')}
                className="w-full py-2.5 text-sm font-medium text-white rounded-lg bg-accent hover:bg-accent/90 transition-colors"
              >
                Get Started
              </button>
            </SheetClose>
          </div>

          <div className="mt-auto pb-8 px-4">
            <div className="flex items-center justify-between">
              <GitHubStars />
              <ThemeToggle />
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}