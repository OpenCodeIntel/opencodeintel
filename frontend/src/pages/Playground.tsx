import { useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { API_URL } from '../config/api'
import type { SearchResult } from '../types'

// Pre-indexed demo repos
const DEMO_REPOS = [
  { id: 'flask', name: 'Flask', description: 'Python web framework', icon: '🐍' },
  { id: 'fastapi', name: 'FastAPI', description: 'Modern Python API', icon: '⚡' },
  { id: 'express', name: 'Express', description: 'Node.js framework', icon: '🟢' },
]

const EXAMPLE_QUERIES = [
  'authentication middleware',
  'error handling',
  'database connection',
  'user validation',
  'route handlers',
]

interface PlaygroundProps {
  onSignupClick: () => void
}

export function Playground({ onSignupClick }: PlaygroundProps) {
  const [query, setQuery] = useState('')
  const [selectedRepo, setSelectedRepo] = useState(DEMO_REPOS[0].id)
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searchTime, setSearchTime] = useState<number | null>(null)
  const [searchCount, setSearchCount] = useState(0)
  const [hasSearched, setHasSearched] = useState(false)

  const FREE_SEARCH_LIMIT = 5

  const handleSearch = async (searchQuery?: string) => {
    const q = searchQuery || query
    if (!q.trim()) return

    if (searchCount >= FREE_SEARCH_LIMIT) {
      // Show signup prompt
      return
    }

    setLoading(true)
    setHasSearched(true)
    const startTime = Date.now()

    try {
      const response = await fetch(`${API_URL}/api/playground/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: q,
          demo_repo: selectedRepo,
          max_results: 10
        })
      })

      const data = await response.json()
      setResults(data.results || [])
      setSearchTime(Date.now() - startTime)
      setSearchCount(prev => prev + 1)
    } catch (error) {
      console.error('Search error:', error)
    } finally {
      setLoading(false)
    }
  }

  const remainingSearches = FREE_SEARCH_LIMIT - searchCount

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Minimal Nav */}
      <nav className="border-b border-gray-100 bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
              <span className="text-white font-bold text-xs">CI</span>
            </div>
            <span className="font-semibold text-gray-900">CodeIntel</span>
          </div>
          <div className="flex items-center gap-3">
            <a href="/login" className="text-sm text-gray-600 hover:text-gray-900">
              Sign in
            </a>
            <button 
              onClick={onSignupClick}
              className="text-sm bg-gray-900 text-white px-4 py-1.5 rounded-lg hover:bg-gray-800 transition-colors"
            >
              Get started
            </button>
          </div>
        </div>
      </nav>

      {/* Hero + Search */}
      <div className="max-w-4xl mx-auto px-6 pt-16 pb-8">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold text-gray-900 mb-3">
            Search code by meaning
          </h1>
          <p className="text-lg text-gray-600">
            Find functions, patterns, and logic across codebases — powered by AI
          </p>
        </div>

        {/* Repo Selector Pills */}
        <div className="flex justify-center gap-2 mb-6">
          {DEMO_REPOS.map(repo => (
            <button
              key={repo.id}
              onClick={() => setSelectedRepo(repo.id)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                selectedRepo === repo.id
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'bg-white text-gray-700 border border-gray-200 hover:border-gray-300'
              }`}
            >
              <span className="mr-1.5">{repo.icon}</span>
              {repo.name}
            </button>
          ))}
        </div>

        {/* Search Box */}
        <div className="relative">
          <form onSubmit={(e) => { e.preventDefault(); handleSearch(); }}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="What are you looking for? e.g., authentication, error handling..."
              className="w-full px-5 py-4 text-lg rounded-2xl border-2 border-gray-200 focus:border-blue-500 focus:ring-4 focus:ring-blue-100 outline-none transition-all shadow-sm"
              autoFocus
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600 text-white px-6 py-2.5 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Searching
                </span>
              ) : 'Search'}
            </button>
          </form>
        </div>

        {/* Example Queries */}
        {!hasSearched && (
          <div className="flex flex-wrap justify-center gap-2 mt-4">
            <span className="text-sm text-gray-500">Try:</span>
            {EXAMPLE_QUERIES.map(q => (
              <button
                key={q}
                onClick={() => { setQuery(q); handleSearch(q); }}
                className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Remaining searches indicator */}
        {searchCount > 0 && remainingSearches > 0 && (
          <div className="text-center mt-4 text-sm text-gray-500">
            {remainingSearches} free {remainingSearches === 1 ? 'search' : 'searches'} remaining •{' '}
            <button onClick={onSignupClick} className="text-blue-600 hover:underline">
              Sign up for unlimited
            </button>
          </div>
        )}
      </div>

      {/* Results */}
      {hasSearched && (
        <div className="max-w-4xl mx-auto px-6 pb-16">
          {/* Stats */}
          {searchTime !== null && (
            <div className="flex items-center gap-4 mb-6 text-sm text-gray-600">
              <span><strong className="text-gray-900">{results.length}</strong> results</span>
              <span className="text-gray-300">•</span>
              <span><strong className="font-mono text-gray-900">{searchTime}ms</strong></span>
            </div>
          )}

          {/* Limit Reached Banner */}
          {searchCount >= FREE_SEARCH_LIMIT && (
            <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl p-6 mb-6 text-white">
              <h3 className="text-lg font-semibold mb-2">You've used all free searches</h3>
              <p className="text-blue-100 mb-4">
                Sign up to get unlimited searches, index your own repos, and more.
              </p>
              <button
                onClick={onSignupClick}
                className="bg-white text-blue-600 px-6 py-2 rounded-lg font-medium hover:bg-blue-50 transition-colors"
              >
                Get started — it's free
              </button>
            </div>
          )}

          {/* Results List */}
          <div className="space-y-4">
            {results.map((result, idx) => (
              <div 
                key={idx} 
                className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow"
              >
                {/* Header */}
                <div className="px-5 py-4 border-b border-gray-100 flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-mono font-semibold text-gray-900">{result.name}</h3>
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded uppercase">
                        {result.type.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 font-mono mt-1">
                      {result.file_path}
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-blue-600">
                      {(result.score * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-gray-500">match</div>
                  </div>
                </div>

                {/* Code */}
                <SyntaxHighlighter
                  language={result.language}
                  style={oneDark}
                  customStyle={{
                    margin: 0,
                    borderRadius: 0,
                    fontSize: '0.8rem',
                  }}
                  showLineNumbers
                  startingLineNumber={result.line_start}
                >
                  {result.code}
                </SyntaxHighlighter>
              </div>
            ))}
          </div>

          {/* Empty State */}
          {results.length === 0 && !loading && (
            <div className="text-center py-16">
              <div className="text-5xl mb-4">🔍</div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No results found</h3>
              <p className="text-gray-600">Try a different query or select another repository</p>
            </div>
          )}
        </div>
      )}

      {/* Features Section (shown before first search) */}
      {!hasSearched && (
        <div className="max-w-4xl mx-auto px-6 py-16 border-t border-gray-100">
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="text-3xl mb-3">🧠</div>
              <h3 className="font-semibold text-gray-900 mb-2">Semantic Search</h3>
              <p className="text-sm text-gray-600">
                Find code by meaning, not just keywords. Ask for "auth logic" and get authentication functions.
              </p>
            </div>
            <div className="text-center">
              <div className="text-3xl mb-3">🔌</div>
              <h3 className="font-semibold text-gray-900 mb-2">MCP Integration</h3>
              <p className="text-sm text-gray-600">
                Connect to Claude, Cursor, or any MCP client. Search code from your AI assistant.
              </p>
            </div>
            <div className="text-center">
              <div className="text-3xl mb-3">📊</div>
              <h3 className="font-semibold text-gray-900 mb-2">Code Intelligence</h3>
              <p className="text-sm text-gray-600">
                Understand dependencies, coding patterns, and impact analysis for your codebase.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
