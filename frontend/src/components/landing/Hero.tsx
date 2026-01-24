import { useRef, useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2, Sparkles } from 'lucide-react'
import { HeroSearch, type HeroSearchHandle } from './HeroSearch'
import { useDemoSearch, DEMO_REPOS, type DemoRepo } from '@/hooks/useDemoSearch'
import type { SearchResult } from '@/types'

interface Props {
  onResultsReady?: (results: SearchResult[], query: string, repoId: string, time: number | null) => void
}

const PYTHON_REPOS = DEMO_REPOS.filter(r => ['flask', 'fastapi'].includes(r.id))

const TYPING_QUERIES = [
  'authentication middleware',
  'database connection pool',
  'error handling patterns',
  'caching implementation',
  'request validation',
]

// staggered text animation variants
const headlineVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.2 }
  }
}

const wordVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { 
    opacity: 1, 
    y: 0, 
    transition: { duration: 0.4, ease: [0.25, 0.4, 0.25, 1] }
  }
}

/**
 * Render the page hero with an animated headline, demo search input, repo switcher, and a preview result card.
 *
 * The component runs a simulated typing/demo search workflow until the user interacts, exposes a '/' keyboard
 * shortcut to focus the search input, and invokes the optional `onResultsReady` callback whenever search results become available.
 *
 * @param onResultsReady - Optional callback invoked when results are ready with `(results, query, repoId, time)`
 * @returns The hero section UI as a React element
 */
export function Hero({ onResultsReady }: Props) {
  const searchRef = useRef<HeroSearchHandle>(null)
  const cardRef = useRef<HTMLDivElement>(null)
  const { query, repo, results, loading, searchTime, setQuery, setRepo, search } = useDemoSearch(false)
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const [isTyping, setIsTyping] = useState(true)
  const [typingIndex, setTypingIndex] = useState(0)
  const typingTimeoutRef = useRef<ReturnType<typeof setTimeout>>()

  useEffect(() => {
    if (results.length) onResultsReady?.(results, query, repo.id, searchTime)
  }, [results, query, repo.id, searchTime, onResultsReady])

  // Typing animation
  useEffect(() => {
    if (!isTyping) return
    const currentQuery = TYPING_QUERIES[typingIndex]
    let charIndex = 0
    const typeChar = () => {
      if (charIndex <= currentQuery.length) {
        setQuery(currentQuery.slice(0, charIndex))
        charIndex++
        typingTimeoutRef.current = setTimeout(typeChar, 60 + Math.random() * 40)
      } else {
        typingTimeoutRef.current = setTimeout(() => {
          search()
          typingTimeoutRef.current = setTimeout(() => {
            setTypingIndex((i) => (i + 1) % TYPING_QUERIES.length)
          }, 4000)
        }, 500)
      }
    }
    typingTimeoutRef.current = setTimeout(typeChar, 1500)
    return () => { if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current) }
  }, [isTyping, typingIndex, setQuery, search])

  const handleUserInput = useCallback((val: string) => {
    setIsTyping(false)
    if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current)
    setQuery(val)
  }, [setQuery])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName
      if (e.key === '/' && tag !== 'INPUT' && tag !== 'TEXTAREA') {
        e.preventDefault()
        setIsTyping(false)
        searchRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!cardRef.current) return
    const rect = cardRef.current.getBoundingClientRect()
    setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top })
  }

  const topResult = results[0]
  const line1Words = ['Stop', 'feeling', 'lost', 'in']
  const line2Words = ['unfamiliar', 'codebases.']

  return (
    <section className="relative min-h-[90vh] flex flex-col justify-center pt-16 pb-8 px-6 overflow-hidden">
      {/* Grid pattern background */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px] [mask-image:radial-gradient(ellipse_50%_50%_at_50%_50%,black_40%,transparent_100%)]" />
      
      {/* Floating gradient orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          className="absolute top-1/4 left-1/4 w-[600px] h-[600px] rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(79,70,229,0.2) 0%, transparent 60%)' }}
          animate={{ x: [0, 30, 0], y: [0, -20, 0] }}
          transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute top-1/3 right-1/4 w-[500px] h-[500px] rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(139,92,246,0.15) 0%, transparent 60%)' }}
          animate={{ x: [0, -25, 0], y: [0, 25, 0] }}
          transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute bottom-1/4 left-1/3 w-[400px] h-[400px] rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(34,211,238,0.1) 0%, transparent 60%)' }}
          animate={{ x: [0, 20, 0], y: [0, -15, 0] }}
          transition={{ duration: 14, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>

      <div className="relative max-w-3xl mx-auto w-full">
        {/* Badge */}
        <motion.div
          className="flex justify-center mb-5"
          initial={{ opacity: 0, y: 20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.6, ease: [0.25, 0.4, 0.25, 1] }}
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-accent/30 bg-accent/5 text-sm backdrop-blur-sm">
            <Sparkles className="w-3.5 h-3.5 text-accent" />
            <span className="text-accent font-medium">Now in beta</span>
            <span className="text-muted-foreground">• Free for open source</span>
          </div>
        </motion.div>

        {/* Staggered Headline */}
        <div className="text-center mb-8">
          <motion.h1 
            className="text-4xl md:text-5xl lg:text-6xl font-bold text-foreground leading-[1.1] tracking-tight"
            variants={headlineVariants}
            initial="hidden"
            animate="visible"
          >
            <span className="block">
              {line1Words.map((word, i) => (
                <motion.span key={i} variants={wordVariants} className="inline-block mr-[0.3em]">
                  {word}
                </motion.span>
              ))}
            </span>
            <span className="block bg-gradient-to-r from-accent via-violet-400 to-cyan-400 bg-clip-text text-transparent">
              {line2Words.map((word, i) => (
                <motion.span key={i} variants={wordVariants} className="inline-block mr-[0.3em]">
                  {word}
                </motion.span>
              ))}
            </span>
          </motion.h1>
          <motion.p 
            className="mt-5 text-lg text-muted-foreground max-w-xl mx-auto leading-relaxed"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
          >
            Describe what you're looking for in plain English.
            <br className="hidden sm:block" />
            Get the exact function, class, or pattern. Instantly.
          </motion.p>
        </div>

        {/* Search with glow */}
        <motion.div
          className="relative"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.6 }}
        >
          {/* Animated glow behind search */}
          <div className="absolute -inset-1 bg-gradient-to-r from-accent/20 via-violet-500/20 to-cyan-500/20 rounded-2xl blur-xl opacity-60 animate-pulse" />
          <div className="relative">
            <HeroSearch
              ref={searchRef}
              value={query}
              onChange={handleUserInput}
              onSubmit={() => { setIsTyping(false); search() }}
              searching={loading}
              repoName={repo.name}
            />
          </div>
        </motion.div>

        {/* Repo switcher */}
        <motion.div
          className="mt-4 flex items-center justify-center gap-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.7 }}
        >
          <span className="text-xs text-muted-foreground/60">Try on:</span>
          {PYTHON_REPOS.map(r => (
            <motion.button
              key={r.id}
              onClick={() => setRepo(r)}
              disabled={loading}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.98 }}
              className={`px-3 py-1.5 text-xs rounded-lg transition-all font-medium ${
                repo.id === r.id 
                  ? 'bg-accent/10 text-accent border border-accent/20' 
                  : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
              }`}
            >
              {r.name}
            </motion.button>
          ))}
        </motion.div>

        {/* Result card */}
        <AnimatePresence>
          {(loading || topResult) && (
            <motion.div
              className="mt-6"
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            >
              <div ref={cardRef} onMouseMove={handleMouseMove} className="relative group">
                <div
                  className="absolute -inset-px rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
                  style={{ background: `radial-gradient(600px circle at ${mousePos.x}px ${mousePos.y}px, rgba(79,70,229,0.15), transparent 40%)` }}
                />
                <div className="relative rounded-xl border border-white/[0.08] bg-card/60 backdrop-blur-md overflow-hidden">
                  <AnimatePresence mode="wait">
                    {loading ? (
                      <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="p-6">
                        <div className="flex items-center gap-3 mb-4">
                          <Loader2 className="w-4 h-4 animate-spin text-accent" />
                          <span className="text-sm text-muted-foreground">Searching {repo.name}...</span>
                        </div>
                        <div className="space-y-3">
                          <motion.div className="h-5 w-48 bg-white/5 rounded" animate={{ opacity: [0.3, 0.6, 0.3] }} transition={{ duration: 1.5, repeat: Infinity }} />
                          <motion.div className="h-3 w-32 bg-white/5 rounded" animate={{ opacity: [0.3, 0.6, 0.3] }} transition={{ duration: 1.5, repeat: Infinity, delay: 0.2 }} />
                          <motion.div className="h-24 bg-white/[0.02] rounded-lg mt-3" animate={{ opacity: [0.3, 0.5, 0.3] }} transition={{ duration: 1.5, repeat: Infinity, delay: 0.4 }} />
                        </div>
                      </motion.div>
                    ) : topResult ? (
                      <motion.div key="result" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                        <div className="px-5 py-3 border-b border-white/[0.06] flex items-center justify-between bg-white/[0.02]">
                          <div className="flex items-center gap-3">
                            <div className="flex items-center gap-2">
                              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                              <span className="text-xs text-muted-foreground">Found in {searchTime}ms</span>
                            </div>
                            <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-medium">{Math.round(topResult.score * 100)}% match</span>
                          </div>
                          <span className="text-xs text-muted-foreground/60">{repo.name}</span>
                        </div>
                        <div className="p-5">
                          <div className="flex items-start gap-3 mb-4">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="font-mono text-sm font-semibold text-foreground">{topResult.name}</span>
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400 uppercase font-medium">{topResult.type}</span>
                              </div>
                              <div className="text-xs text-muted-foreground/60 font-mono mt-1">{topResult.file_path}</div>
                            </div>
                          </div>
                          <div className="relative rounded-lg overflow-hidden">
                            <div className="absolute inset-0 bg-gradient-to-br from-accent/5 to-violet-500/5" />
                            <pre className="relative text-xs text-zinc-300 bg-black/40 p-4 overflow-x-auto font-mono leading-relaxed">
                              <code>{topResult.content?.slice(0, 250)}...</code>
                            </pre>
                          </div>
                        </div>
                        {results.length > 1 && (
                          <div className="px-5 py-3 border-t border-white/[0.06] bg-white/[0.01]">
                            <span className="text-xs text-muted-foreground/60">+{results.length - 1} more results</span>
                          </div>
                        )}
                      </motion.div>
                    ) : null}
                  </AnimatePresence>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* CTA */}
        <motion.div
          className="mt-8 flex flex-col items-center gap-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
        >
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <motion.a
              href="/signup"
              whileHover={{ scale: 1.02, boxShadow: '0 20px 40px -10px rgba(79,70,229,0.3)' }}
              whileTap={{ scale: 0.98 }}
              className="inline-flex items-center gap-2 px-6 py-3 text-sm font-medium text-white rounded-lg bg-accent hover:bg-accent/90 transition-colors shadow-lg shadow-accent/20"
            >
              Index your first repo free
              <span className="text-white/60">→</span>
            </motion.a>
            <motion.a
              href="https://github.com/OpenCodeIntel/opencodeintel"
              target="_blank"
              rel="noopener noreferrer"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="inline-flex items-center gap-2 px-6 py-3 text-sm font-medium text-muted-foreground rounded-lg border border-white/10 hover:border-white/20 hover:text-foreground hover:bg-white/5 transition-all"
            >
              <svg viewBox="0 0 24 24" className="w-4 h-4 fill-current" aria-hidden="true">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
              </svg>
              View on GitHub
            </motion.a>
          </div>
          <p className="text-xs text-muted-foreground/60">Works with any Python repository • Self-host or cloud</p>
        </motion.div>
      </div>
    </section>
  )
}