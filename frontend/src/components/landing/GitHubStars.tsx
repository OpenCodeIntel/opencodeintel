import { Star } from 'lucide-react'
import { useGitHubStars } from '@/hooks/useGitHubStars'

const REPO_URL = 'https://github.com/OpenCodeIntel/opencodeintel'

/**
 * Render a clickable GitHub repository badge that displays the repository's star count.
 *
 * The badge links to the repository, shows a GitHub icon, a star icon, and the star count;
 * while the count is loading it displays "—", and counts >= 1000 are formatted as `X.Xk`.
 *
 * @returns A JSX element representing the clickable GitHub stars badge
 */
export function GitHubStars() {
  const { stars, loading } = useGitHubStars()

  const formatStars = (count: number) => {
    if (count >= 1000) return `${(count / 1000).toFixed(1)}k`
    return count.toString()
  }

  return (
    <a
      href={REPO_URL}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/10 dark:border-white/10 light:border-black/10 hover:bg-white/5 dark:hover:bg-white/5 light:hover:bg-black/5 transition-colors group"
    >
      <svg viewBox="0 0 24 24" className="w-4 h-4 fill-current" aria-hidden="true">
        <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
      </svg>
      <div className="flex items-center gap-1 text-sm">
        <Star className="w-3.5 h-3.5 text-yellow-500 fill-yellow-500" />
        <span className="text-zinc-400 group-hover:text-foreground transition-colors">
          {loading ? '—' : formatStars(stars || 0)}
        </span>
      </div>
    </a>
  )
}