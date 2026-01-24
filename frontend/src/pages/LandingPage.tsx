import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Navbar, Hero, ResultsView, Features, Pricing, FAQ, Footer } from '@/components/landing'
import { API_URL } from '@/config/api'
import { playgroundAPI } from '@/services/playground-api'
import type { SearchResult } from '@/types'

/**
 * Render the landing page and manage its search state and flows.
 *
 * Manages local state for search results, loading, timing, query inputs, repository selection,
 * and rate-limiting. On mount it fetches playground limits and updates remaining/limit.
 * Exposes behavior to perform searches (against a demo repo or a custom playground), handle
 * hero-initiated results, re-search the current query, and reset to the initial landing view.
 *
 * @returns The landing page React element containing a Navbar and either a ResultsView (after a search)
 * or the public landing sections (Hero, Features, Pricing, FAQ, Footer).
 */
export function LandingPage() {
  const navigate = useNavigate()
  
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searchTime, setSearchTime] = useState<number | null>(null)
  const [hasSearched, setHasSearched] = useState(false)
  const [searchedQuery, setSearchedQuery] = useState('')
  const [inputQuery, setInputQuery] = useState('')
  const [currentRepoId, setCurrentRepoId] = useState('')
  const [isCustomRepo, setIsCustomRepo] = useState(false)
  const [remaining, setRemaining] = useState(50)
  const [limit, setLimit] = useState(50)
  const [rateLimitError, setRateLimitError] = useState<string | null>(null)

  const isStale = hasSearched && !loading && inputQuery.trim() !== searchedQuery.trim() && inputQuery.trim() !== ''

  useEffect(() => {
    fetch(`${API_URL}/playground/limits`, { credentials: 'include' })
      .then(res => res.json())
      .then(data => {
        setRemaining(data.remaining ?? 50)
        setLimit(data.limit ?? 50)
      })
      .catch(console.error)
  }, [])

  const handleSearch = async (query: string, repoId: string, isCustom: boolean) => {
    if (!query.trim() || loading || remaining <= 0) return

    setLoading(true)
    setHasSearched(true)
    setSearchedQuery(query)
    setInputQuery(query)
    setCurrentRepoId(repoId)
    setIsCustomRepo(isCustom)
    setRateLimitError(null)
    const t0 = Date.now()

    try {
      const data = isCustom
        ? await playgroundAPI.search(query)
        : await fetch(`${API_URL}/playground/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ query, demo_repo: repoId, max_results: 10 })
          }).then(r => r.json())

      if (data.results) {
        setResults(data.results)
        setSearchTime(data.search_time_ms || Date.now() - t0)
        if (typeof data.remaining_searches === 'number') setRemaining(data.remaining_searches)
      } else if (data.status === 429) {
        setRateLimitError('Daily limit reached')
        setRemaining(0)
      }
    } catch (err) {
      console.error('Search failed:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleHeroResults = (heroResults: SearchResult[], query: string, repoId: string, time: number | null) => {
    setResults(heroResults)
    setSearchTime(time)
    setSearchedQuery(query)
    setInputQuery(query)
    setCurrentRepoId(repoId)
    setIsCustomRepo(false)
    setHasSearched(true)
  }

  const handleReSearch = () => {
    if (inputQuery.trim() && currentRepoId) handleSearch(inputQuery, currentRepoId, isCustomRepo)
  }

  const handleNewSearch = () => {
    setHasSearched(false)
    setResults([])
    setSearchTime(null)
    setSearchedQuery('')
    setInputQuery('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar minimal={hasSearched} />

      {hasSearched ? (
        <ResultsView
          results={results}
          loading={loading}
          searchTime={searchTime}
          inputQuery={inputQuery}
          searchedQuery={searchedQuery}
          isStale={isStale}
          remaining={remaining}
          limit={limit}
          rateLimitError={rateLimitError}
          onQueryChange={setInputQuery}
          onSearch={handleReSearch}
          onBack={handleNewSearch}
          onSignUp={() => navigate('/signup')}
        />
      ) : (
        <>
          <Hero onResultsReady={handleHeroResults} />
          <Features />
          <Pricing />
          <FAQ />
          <Footer />
        </>
      )}
    </div>
  )
}