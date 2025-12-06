/**
 * LocalStorage Cache Utility
 * 
 * Provides persistent caching with expiration support.
 * Used alongside React Query for dual-layer caching strategy.
 */

interface CacheEntry<T> {
  data: T
  timestamp: number
  version: string
}

// Cache version - bump this when data structure changes
const CACHE_VERSION = '1.0.0'

// Default TTL: 30 minutes
const DEFAULT_TTL = 30 * 60 * 1000

/**
 * Generate cache key for a specific resource
 */
export function getCacheKey(resource: string, repoId: string): string {
  return `codeintel:${resource}:${repoId}`
}

/**
 * Get data from localStorage cache
 * Returns null if expired or not found
 */
export function getFromCache<T>(
  resource: string, 
  repoId: string, 
  ttl: number = DEFAULT_TTL
): T | null {
  try {
    const key = getCacheKey(resource, repoId)
    const cached = localStorage.getItem(key)
    
    if (!cached) return null
    
    const entry: CacheEntry<T> = JSON.parse(cached)
    
    // Check version
    if (entry.version !== CACHE_VERSION) {
      localStorage.removeItem(key)
      return null
    }
    
    // Check expiration
    const isExpired = Date.now() - entry.timestamp > ttl
    if (isExpired) {
      localStorage.removeItem(key)
      return null
    }
    
    return entry.data
  } catch (error) {
    console.warn('Cache read error:', error)
    return null
  }
}

/**
 * Save data to localStorage cache
 */
export function saveToCache<T>(
  resource: string, 
  repoId: string, 
  data: T
): void {
  try {
    const key = getCacheKey(resource, repoId)
    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      version: CACHE_VERSION
    }
    localStorage.setItem(key, JSON.stringify(entry))
  } catch (error) {
    // localStorage might be full or disabled
    console.warn('Cache write error:', error)
  }
}

/**
 * Invalidate cache for a specific repo
 * Call this after re-indexing
 */
export function invalidateRepoCache(repoId: string): void {
  const resources = ['dependencies', 'style-analysis', 'search-results']
  resources.forEach(resource => {
    const key = getCacheKey(resource, repoId)
    localStorage.removeItem(key)
  })
}

/**
 * Invalidate all CodeIntel caches
 */
export function invalidateAllCache(): void {
  const keysToRemove: string[] = []
  
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key?.startsWith('codeintel:')) {
      keysToRemove.push(key)
    }
  }
  
  keysToRemove.forEach(key => localStorage.removeItem(key))
}

/**
 * Get cache stats for debugging
 */
export function getCacheStats(): { count: number; totalSize: number } {
  let count = 0
  let totalSize = 0
  
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key?.startsWith('codeintel:')) {
      count++
      totalSize += localStorage.getItem(key)?.length || 0
    }
  }
  
  return { count, totalSize }
}
