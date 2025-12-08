import { useState } from 'react'
import { toast } from 'sonner'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import type { SearchResult } from '../types'

interface SearchPanelProps {
  repoId: string
  apiUrl: string
  apiKey: string
}

export function SearchPanel({ repoId, apiUrl, apiKey }: SearchPanelProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searchTime, setSearchTime] = useState<number | null>(null)
  const [cached, setCached] = useState(false)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    const startTime = Date.now()

    try {
      const response = await fetch(`${apiUrl}/search`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query,
          repo_id: repoId,
          max_results: 10
        })
      })

      const data = await response.json()
      setResults(data.results || [])
      setSearchTime(Date.now() - startTime)
      setCached(data.cached || false)
    } catch (error) {
      console.error('Search error:', error)
      toast.error('Search failed', {
        description: 'Please check your query and try again'
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Search */}
      <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
        <form onSubmit={handleSearch}>
          <div className="flex gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., authentication middleware, React hooks, database queries..."
              className="flex-1 px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder:text-gray-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-all"
              disabled={loading}
              autoFocus
            />
            <button
              type="submit"
              className="px-6 py-3 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white font-medium rounded-xl transition-all disabled:opacity-50"
              disabled={loading}
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>
          <p className="mt-3 text-xs text-gray-500">
            Powered by semantic embeddings - finds code by meaning, not just keywords
          </p>
        </form>

        {searchTime !== null && (
          <div className="mt-4 pt-4 border-t border-white/5 flex items-center gap-4 text-sm text-gray-400">
            <span>
              <span className="font-semibold text-white">{results.length}</span> results
            </span>
            <span className="text-gray-600">•</span>
            <span>
              <span className="font-mono font-semibold text-white">{searchTime}ms</span>
            </span>
            {cached && (
              <>
                <span className="text-gray-600">•</span>
                <span className="text-xs bg-green-500/10 text-green-400 border border-green-500/20 px-2 py-0.5 rounded-md">
                  ⚡ Cached
                </span>
              </>
            )}
          </div>
        )}
      </div>

      {/* Results */}
      <div className="space-y-4">
        {results.map((result, idx) => (
          <div key={idx} className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5 hover:border-white/10 transition-all group">
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-mono font-semibold text-sm text-white">
                    {result.name}
                  </h3>
                  <span className="px-2 py-0.5 text-[10px] uppercase tracking-wide bg-white/5 text-gray-400 border border-white/10 rounded">
                    {result.type.replace('_', ' ')}
                  </span>
                </div>
                <p className="text-xs text-gray-500 font-mono">
                  {result.file_path.split('/').slice(-3).join('/')}
                </p>
              </div>
              
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <div className="text-xs font-mono text-gray-500">Match</div>
                  <div className="text-sm font-mono font-semibold text-blue-400">
                    {(result.score * 100).toFixed(0)}%
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    navigator.clipboard.writeText(result.code)
                    toast.success('Code copied!')
                  }}
                  className="px-3 py-1.5 text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                  title="Copy code"
                >
                  Copy
                </button>
              </div>
            </div>

            {/* Code with Syntax Highlighting */}
            <div className="relative rounded-lg overflow-hidden">
              <SyntaxHighlighter
                language={result.language}
                style={oneDark}
                customStyle={{
                  margin: 0,
                  borderRadius: '0.5rem',
                  fontSize: '0.75rem',
                  lineHeight: '1.5',
                  background: '#0d0d0f',
                }}
                showLineNumbers
                startingLineNumber={result.line_start}
              >
                {result.code}
              </SyntaxHighlighter>
              
              <div className="absolute top-3 right-3">
                <span className="px-2 py-0.5 text-[10px] font-mono uppercase bg-black/50 text-gray-400 backdrop-blur rounded">
                  {result.language}
                </span>
              </div>
            </div>

            {/* Metadata */}
            <div className="mt-3 flex items-center gap-3 text-xs text-gray-500">
              <span className="font-mono">
                Lines {result.line_start}–{result.line_end}
              </span>
              <span className="text-gray-600">•</span>
              <span className="text-gray-500 truncate">
                {result.file_path}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Empty State */}
      {results.length === 0 && query && !loading && (
        <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-16 text-center">
          <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-white/5 flex items-center justify-center">
            <span className="text-4xl">🔍</span>
          </div>
          <h3 className="text-base font-semibold mb-2 text-white">No results found</h3>
          <p className="text-sm text-gray-400">
            Try a different query or check if the repository is fully indexed
          </p>
        </div>
      )}
    </div>
  )
}
