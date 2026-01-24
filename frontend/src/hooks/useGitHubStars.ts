import { useState, useEffect } from 'react'

const REPO = 'OpenCodeIntel/opencodeintel'
const CACHE_KEY = 'github-stars-cache'
const CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

interface CacheData {
  stars: number
  timestamp: number
}

/**
 * Provides the GitHub star count for the configured repository with client-side caching.
 *
 * Uses a short-lived localStorage cache and falls back to any cached value if a network request fails.
 *
 * @returns An object with `stars` set to the repository star count (or `null` if unknown) and `loading` set to `true` while the value is being resolved, `false` otherwise.
 */
export function useGitHubStars() {
  const [stars, setStars] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStars = async () => {
      // check cache first
      const cached = localStorage.getItem(CACHE_KEY)
      if (cached) {
        const data: CacheData = JSON.parse(cached)
        if (Date.now() - data.timestamp < CACHE_DURATION) {
          setStars(data.stars)
          setLoading(false)
          return
        }
      }

      try {
        const res = await fetch(`https://api.github.com/repos/${REPO}`)
        if (!res.ok) throw new Error('Failed to fetch')
        const data = await res.json()
        const starCount = data.stargazers_count || 0
        
        // cache it
        localStorage.setItem(CACHE_KEY, JSON.stringify({
          stars: starCount,
          timestamp: Date.now()
        }))
        
        setStars(starCount)
      } catch {
        // fallback to cached even if expired
        if (cached) {
          setStars(JSON.parse(cached).stars)
        }
      } finally {
        setLoading(false)
      }
    }

    fetchStars()
  }, [])

  return { stars, loading }
}