import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { API_URL } from '../config/api'
import type { SearchResult } from '../types'

// Icons
const SearchIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
)

const ZapIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
  </svg>
)

const GitHubIcon = () => (
  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
    <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
  </svg>
)

const SparklesIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
  </svg>
)

const ArrowRightIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
  </svg>
)

const CheckIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
)

// Demo repos
const DEMO_REPOS = [
  { id: 'flask', name: 'Flask', icon: '🐍', color: 'from-green-500/20 to-green-600/20 border-green-500/30' },
  { id: 'fastapi', name: 'FastAPI', icon: '⚡', color: 'from-teal-500/20 to-teal-600/20 border-teal-500/30' },
  { id: 'express', name: 'Express', icon: '🟢', color: 'from-yellow-500/20 to-yellow-600/20 border-yellow-500/30' },
]

const EXAMPLE_QUERIES = [
  'authentication middleware',
  'error handling',
  'database connection',
]

// Scroll animation hook
function useScrollAnimation() {
  const ref = useRef<HTMLDivElement>(null)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true)
        }
      },
      { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
    )

    if (ref.current) {
      observer.observe(ref.current)
    }

    return () => observer.disconnect()
  }, [])

  return { ref, isVisible }
}

// Animated section wrapper
function AnimatedSection({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  const { ref, isVisible } = useScrollAnimation()
  
  return (
    <div
      ref={ref}
      className={`transition-all duration-700 ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
      } ${className}`}
    >
      {children}
    </div>
  )
}

export function LandingPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [selectedRepo, setSelectedRepo] = useState(DEMO_REPOS[0].id)
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searchTime, setSearchTime] = useState<number | null>(null)
  const [searchCount, setSearchCount] = useState(0)
  const [hasSearched, setHasSearched] = useState(false)
  const [availableRepos, setAvailableRepos] = useState<string[]>([])

  const FREE_LIMIT = 5
  const remaining = FREE_LIMIT - searchCount

  useEffect(() => {
    fetch(`${API_URL}/api/playground/repos`)
      .then(res => res.json())
      .then(data => {
        const available = data.repos?.filter((r: any) => r.available).map((r: any) => r.id) || []
        setAvailableRepos(available)
      })
      .catch(console.error)
  }, [])

  const handleSearch = async (searchQuery?: string) => {
    const q = searchQuery || query
    if (!q.trim() || loading || searchCount >= FREE_LIMIT) return

    setLoading(true)
    setHasSearched(true)
    const startTime = Date.now()

    try {
      const response = await fetch(`${API_URL}/api/playground/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, demo_repo: selectedRepo, max_results: 10 })
      })
      const data = await response.json()
      if (response.ok) {
        setResults(data.results || [])
        setSearchTime(Date.now() - startTime)
        setSearchCount(prev => prev + 1)
      }
    } catch (error) {
      console.error('Search error:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#09090b] text-white">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-[#09090b]/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">CI</span>
            </div>
            <span className="font-semibold">CodeIntel</span>
            <Badge variant="glow" className="text-[10px]">BETA</Badge>
          </div>
          <div className="flex items-center gap-4">
            <a href="https://github.com/opencodeintel/opencodeintel" target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-white transition-colors">
              <GitHubIcon />
            </a>
            <Button variant="ghost" className="text-gray-400 hover:text-white" onClick={() => navigate('/login')}>
              Sign in
            </Button>
            <Button className="bg-white text-black hover:bg-gray-100" onClick={() => navigate('/signup')}>
              Get started
            </Button>
          </div>
        </div>
      </nav>

      {/* ============ HERO SECTION ============ */}
      <section className="min-h-screen flex flex-col justify-center pt-16 pb-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 mb-8">
            <SparklesIcon />
            <span className="text-sm text-blue-400">AI-powered code search</span>
          </div>

          <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-6">
            <span className="text-gray-400">grep returned </span>
            <span className="text-white">847 results.</span>
            <br />
            <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              Find the one that matters.
            </span>
          </h1>

          <p className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto">
            Search any codebase by meaning, not keywords.
          </p>

          {/* Repo Selector */}
          <div className="flex justify-center gap-3 mb-6">
            {DEMO_REPOS.map(repo => {
              const isAvailable = availableRepos.includes(repo.id)
              const isSelected = selectedRepo === repo.id
              return (
                <button
                  key={repo.id}
                  onClick={() => isAvailable && setSelectedRepo(repo.id)}
                  disabled={!isAvailable}
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition-all border
                    ${isSelected ? `bg-gradient-to-r ${repo.color} text-white` : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10'}
                    ${!isAvailable && 'opacity-40 cursor-not-allowed'}`}
                >
                  <span className="mr-2">{repo.icon}</span>
                  {repo.name}
                  {!isAvailable && <span className="ml-1 text-[10px]">(soon)</span>}
                </button>
              )
            })}
          </div>

          {/* Search Box */}
          <div className="relative max-w-2xl mx-auto mb-6">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-cyan-500/20 rounded-2xl blur-xl opacity-50" />
            <div className="relative bg-[#111113] rounded-2xl border border-white/10 p-3">
              <form onSubmit={(e) => { e.preventDefault(); handleSearch(); }} className="flex items-center gap-3">
                <div className="flex-1 flex items-center gap-3">
                  <div className="text-gray-500 ml-2"><SearchIcon /></div>
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search for authentication, error handling..."
                    className="flex-1 bg-transparent text-white placeholder:text-gray-500 focus:outline-none text-base py-3"
                    autoFocus
                  />
                </div>
                <Button
                  type="submit"
                  disabled={loading || !query.trim() || searchCount >= FREE_LIMIT}
                  className="px-6 py-3 h-auto bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 rounded-xl disabled:opacity-50 shrink-0"
                >
                  {loading ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : 'Search'}
                </Button>
              </form>
            </div>
          </div>

          {/* Trust Indicators */}
          <div className="flex items-center justify-center gap-6 text-sm text-gray-500 mb-8">
            <div className="flex items-center gap-2"><ZapIcon /><span>~100ms</span></div>
            <div className="w-1 h-1 rounded-full bg-gray-700" />
            <span>No signup required</span>
            <div className="w-1 h-1 rounded-full bg-gray-700" />
            <span>{remaining} free searches</span>
          </div>

          {/* Example Queries */}
          {!hasSearched && (
            <div className="flex flex-wrap justify-center gap-2">
              <span className="text-sm text-gray-600">Try:</span>
              {EXAMPLE_QUERIES.map(q => (
                <button key={q} onClick={() => { setQuery(q); handleSearch(q); }} className="text-sm text-gray-400 hover:text-blue-400 transition-colors">
                  "{q}"
                </button>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ============ RESULTS SECTION (if searched) ============ */}
      {hasSearched && (
        <section className="pb-20 px-6">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-4 text-sm">
                <span className="text-gray-400"><span className="text-white font-semibold">{results.length}</span> results</span>
                {searchTime && <><span className="text-gray-700">•</span><span className="font-mono text-green-400">{searchTime}ms</span></>}
              </div>
              {remaining > 0 && remaining < FREE_LIMIT && (
                <div className="text-sm text-gray-500">{remaining} remaining</div>
              )}
            </div>

            {searchCount >= FREE_LIMIT && (
              <Card className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 border-blue-500/30 p-6 mb-6">
                <h3 className="text-lg font-semibold mb-2">You've used all free searches</h3>
                <p className="text-gray-300 mb-4">Sign up to get unlimited searches and index your own repos.</p>
                <Button onClick={() => navigate('/signup')} className="bg-white text-black hover:bg-gray-100">Get started — it's free</Button>
              </Card>
            )}

            <div className="space-y-4">
              {results.map((result, idx) => (
                <Card key={idx} className="bg-[#111113] border-white/5 overflow-hidden hover:border-white/10 transition-all">
                  <div className="px-5 py-4 border-b border-white/5 flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-3">
                        <h3 className="font-mono font-semibold">{result.name}</h3>
                        <Badge variant="outline" className="text-[10px] text-gray-400 border-gray-700">{result.type.replace('_', ' ')}</Badge>
                      </div>
                      <p className="text-sm text-gray-500 font-mono mt-1">{result.file_path.split('/').slice(-2).join('/')}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-blue-400">{(result.score * 100).toFixed(0)}%</div>
                      <div className="text-[10px] text-gray-500 uppercase tracking-wider">match</div>
                    </div>
                  </div>
                  <SyntaxHighlighter language={result.language || 'python'} style={oneDark} customStyle={{ margin: 0, borderRadius: 0, fontSize: '0.8rem', background: '#0d0d0f' }} showLineNumbers startingLineNumber={result.line_start || 1}>
                    {result.code}
                  </SyntaxHighlighter>
                </Card>
              ))}
            </div>

            {results.length === 0 && !loading && (
              <div className="text-center py-16">
                <div className="text-5xl mb-4">🔍</div>
                <h3 className="text-lg font-semibold mb-2">No results found</h3>
                <p className="text-gray-500">Try a different query</p>
              </div>
            )}
          </div>
        </section>
      )}

      {/* ============ STORY SECTIONS (only before search) ============ */}
      {!hasSearched && (
        <>
          {/* THE PROBLEM */}
          <section className="py-32 px-6 border-t border-white/5">
            <AnimatedSection>
              <div className="max-w-4xl mx-auto">
                <div className="text-center mb-16">
                  <span className="text-red-400 text-sm font-medium uppercase tracking-wider">The Problem</span>
                  <h2 className="text-4xl font-bold mt-4 mb-6">You've been here before</h2>
                  <p className="text-xl text-gray-400 max-w-2xl mx-auto">
                    New codebase. 50,000 lines. You need to find where authentication happens.
                  </p>
                </div>

                {/* Terminal visualization */}
                <div className="bg-[#0d0d0f] rounded-xl border border-white/10 overflow-hidden">
                  <div className="flex items-center gap-2 px-4 py-3 border-b border-white/10 bg-white/5">
                    <div className="w-3 h-3 rounded-full bg-red-500/80" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                    <div className="w-3 h-3 rounded-full bg-green-500/80" />
                    <span className="ml-2 text-xs text-gray-500 font-mono">terminal</span>
                  </div>
                  <div className="p-6 font-mono text-sm">
                    <div className="text-gray-400">$ grep -r "auth" ./src</div>
                    <div className="mt-4 text-gray-500 space-y-1">
                      <div>src/components/AuthButton.tsx: <span className="text-gray-400">// auth button component</span></div>
                      <div>src/utils/auth.ts: <span className="text-gray-400">export const authConfig = ...</span></div>
                      <div>src/pages/auth/login.tsx: <span className="text-gray-400">function AuthLogin() ...</span></div>
                      <div>src/middleware/auth.ts: <span className="text-gray-400">// TODO: add auth</span></div>
                      <div>src/api/auth/callback.ts: <span className="text-gray-400">const authCallback = ...</span></div>
                      <div className="text-gray-600">... 842 more results</div>
                    </div>
                    <div className="mt-6 text-red-400">
                      847 results. Which one handles the actual authentication logic?
                    </div>
                  </div>
                </div>
              </div>
            </AnimatedSection>
          </section>

          {/* THE SOLUTION */}
          <section className="py-32 px-6">
            <AnimatedSection>
              <div className="max-w-4xl mx-auto">
                <div className="text-center mb-16">
                  <span className="text-green-400 text-sm font-medium uppercase tracking-wider">The Solution</span>
                  <h2 className="text-4xl font-bold mt-4 mb-6">Search by meaning, not keywords</h2>
                  <p className="text-xl text-gray-400 max-w-2xl mx-auto">
                    Ask for "authentication logic" and get the function that actually handles it.
                  </p>
                </div>

                {/* CodeIntel visualization */}
                <div className="bg-[#0d0d0f] rounded-xl border border-green-500/20 overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-green-500/5">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
                        <span className="text-white font-bold text-[10px]">CI</span>
                      </div>
                      <span className="text-xs text-gray-400 font-mono">CodeIntel</span>
                    </div>
                    <span className="text-xs text-green-400 font-mono">1 result • 89ms</span>
                  </div>
                  <div className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <div className="flex items-center gap-3">
                          <span className="font-mono font-semibold text-white">authenticate_user</span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-green-500/10 text-green-400 border border-green-500/20">function</span>
                        </div>
                        <span className="text-sm text-gray-500 font-mono">src/auth/handlers.py</span>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-green-400">94%</div>
                        <div className="text-[10px] text-gray-500">match</div>
                      </div>
                    </div>
                    <pre className="text-sm text-gray-300 bg-black/30 rounded-lg p-4 overflow-x-auto"><code>{`def authenticate_user(credentials: dict) -> User:
    """Main authentication logic - validates credentials
    and returns authenticated user or raises AuthError."""
    user = db.get_user(credentials['email'])
    if not verify_password(credentials['password'], user.hash):
        raise AuthError("Invalid credentials")
    return create_session(user)`}</code></pre>
                  </div>
                </div>
              </div>
            </AnimatedSection>
          </section>

          {/* HOW IT WORKS */}
          <section className="py-32 px-6 border-t border-white/5">
            <AnimatedSection>
              <div className="max-w-5xl mx-auto">
                <div className="text-center mb-16">
                  <span className="text-blue-400 text-sm font-medium uppercase tracking-wider">How It Works</span>
                  <h2 className="text-4xl font-bold mt-4">Three steps to code clarity</h2>
                </div>

                <div className="grid md:grid-cols-3 gap-8">
                  <div className="text-center p-8 rounded-2xl bg-white/[0.02] border border-white/5">
                    <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mx-auto mb-6">
                      <span className="text-xl font-bold text-blue-400">1</span>
                    </div>
                    <h3 className="font-semibold text-lg mb-3">Index your repo</h3>
                    <p className="text-gray-500 text-sm">Connect your GitHub repo. We analyze and embed every function, class, and module.</p>
                  </div>

                  <div className="text-center p-8 rounded-2xl bg-white/[0.02] border border-white/5">
                    <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mx-auto mb-6">
                      <span className="text-xl font-bold text-blue-400">2</span>
                    </div>
                    <h3 className="font-semibold text-lg mb-3">Search by meaning</h3>
                    <p className="text-gray-500 text-sm">Ask natural questions. "Where is payment handled?" "Show me error boundaries."</p>
                  </div>

                  <div className="text-center p-8 rounded-2xl bg-white/[0.02] border border-white/5">
                    <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mx-auto mb-6">
                      <span className="text-xl font-bold text-blue-400">3</span>
                    </div>
                    <h3 className="font-semibold text-lg mb-3">Get precise results</h3>
                    <p className="text-gray-500 text-sm">Not 847 matches. The exact functions you need, ranked by relevance.</p>
                  </div>
                </div>
              </div>
            </AnimatedSection>
          </section>

          {/* FEATURES */}
          <section className="py-32 px-6">
            <AnimatedSection>
              <div className="max-w-5xl mx-auto">
                <div className="text-center mb-16">
                  <h2 className="text-4xl font-bold">Built for developers</h2>
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                  <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/5">
                    <div className="flex items-start gap-4">
                      <div className="w-10 h-10 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center shrink-0">
                        <span className="text-lg">🔌</span>
                      </div>
                      <div>
                        <h3 className="font-semibold mb-2">MCP Integration</h3>
                        <p className="text-sm text-gray-500">Works with Claude, Cursor, and any MCP-compatible AI. Search code directly from your assistant.</p>
                      </div>
                    </div>
                  </div>

                  <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/5">
                    <div className="flex items-start gap-4">
                      <div className="w-10 h-10 rounded-lg bg-green-500/10 border border-green-500/20 flex items-center justify-center shrink-0">
                        <span className="text-lg">⚡</span>
                      </div>
                      <div>
                        <h3 className="font-semibold mb-2">Lightning Fast</h3>
                        <p className="text-sm text-gray-500">Sub-100ms responses with Redis caching. Semantic search shouldn't slow you down.</p>
                      </div>
                    </div>
                  </div>

                  <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/5">
                    <div className="flex items-start gap-4">
                      <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center shrink-0">
                        <span className="text-lg">📊</span>
                      </div>
                      <div>
                        <h3 className="font-semibold mb-2">Code Intelligence</h3>
                        <p className="text-sm text-gray-500">Understand dependencies, analyze coding patterns, and see impact before you change.</p>
                      </div>
                    </div>
                  </div>

                  <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/5">
                    <div className="flex items-start gap-4">
                      <div className="w-10 h-10 rounded-lg bg-orange-500/10 border border-orange-500/20 flex items-center justify-center shrink-0">
                        <span className="text-lg">🔓</span>
                      </div>
                      <div>
                        <h3 className="font-semibold mb-2">Open Source</h3>
                        <p className="text-sm text-gray-500">Self-host for private repos. Inspect the code. Contribute improvements. No vendor lock-in.</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </AnimatedSection>
          </section>

          {/* FINAL CTA */}
          <section className="py-32 px-6 border-t border-white/5">
            <AnimatedSection>
              <div className="max-w-3xl mx-auto text-center">
                <h2 className="text-4xl font-bold mb-6">Ready to understand your codebase?</h2>
                <p className="text-xl text-gray-400 mb-10">Start searching for free. No credit card required.</p>
                <div className="flex items-center justify-center gap-4">
                  <Button onClick={() => navigate('/signup')} className="px-8 py-4 h-auto bg-white text-black hover:bg-gray-100 text-lg">
                    Get started free
                  </Button>
                  <a
                    href="https://github.com/opencodeintel/opencodeintel"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-6 py-4 rounded-xl border border-white/10 text-gray-300 hover:bg-white/5 hover:text-white transition-all"
                  >
                    <GitHubIcon />
                    <span>Star on GitHub</span>
                  </a>
                </div>
              </div>
            </AnimatedSection>
          </section>
        </>
      )}

      {/* FOOTER */}
      <footer className="py-8 px-6 border-t border-white/5">
        <div className="max-w-6xl mx-auto flex items-center justify-between text-sm text-gray-500">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
              <span className="text-white font-bold text-[10px]">CI</span>
            </div>
            <span>CodeIntel</span>
          </div>
          <div className="flex items-center gap-6">
            <a href="https://github.com/opencodeintel/opencodeintel" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">GitHub</a>
            <span className="text-gray-700">•</span>
            <span>Open Source</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
