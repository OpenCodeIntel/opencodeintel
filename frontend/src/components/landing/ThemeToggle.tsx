import { useTheme } from 'next-themes'
import { Sun, Moon } from 'lucide-react'
import { useEffect, useState } from 'react'

/**
 * Render a hydration-safe theme toggle button for switching between light and dark modes.
 *
 * Renders a placeholder element until mounted to avoid hydration mismatch. When mounted, displays a button that toggles the application's theme and updates its icon and ARIA label: Sun icon when the current theme is dark, Moon icon when the current theme is light.
 *
 * @returns The theme toggle button element.
 */
export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  // avoid hydration mismatch
  useEffect(() => setMounted(true), [])
  if (!mounted) return <div className="w-9 h-9" />

  const isDark = theme === 'dark'

  return (
    <button
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      className="p-2 rounded-lg text-zinc-400 hover:text-foreground hover:bg-white/5 dark:hover:bg-white/5 light:hover:bg-black/5 transition-colors"
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
    >
      {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
    </button>
  )
}