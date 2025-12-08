/**
 * Cached API Hooks
 * 
 * Dual-layer caching strategy:
 * 1. React Query (memory) - Fast tab navigation, request deduplication
 * 2. localStorage (persist) - Survives refresh, instant initial load
 * 
 * Cache invalidation happens on re-index.
 */

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getFromCache, saveToCache, invalidateRepoCache } from '../lib/cache'
import { API_URL } from '../config/api'

// Stale time: 5 minutes (data considered fresh)
const STALE_TIME = 5 * 60 * 1000

// Cache time: 30 minutes (keep in memory)
const CACHE_TIME = 30 * 60 * 1000

interface UseCachedQueryOptions {
  repoId: string
  apiKey: string
  enabled?: boolean
}

/**
 * Fetch with authorization header
 */
async function fetchWithAuth(url: string, apiKey: string) {
  const response = await fetch(url, {
    headers: { 'Authorization': `Bearer ${apiKey}` }
  })
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }
  
  return response.json()
}

/**
 * Hook for fetching dependency graph with caching
 */
export function useDependencyGraph({ repoId, apiKey, enabled = true }: UseCachedQueryOptions) {
  const queryClient = useQueryClient()
  
  return useQuery({
    queryKey: ['dependencies', repoId],
    queryFn: async () => {
      const data = await fetchWithAuth(
        `${API_URL}/repos/${repoId}/dependencies`,
        apiKey
      )
      // Save to localStorage on successful fetch
      saveToCache('dependencies', repoId, data)
      return data
    },
    enabled: enabled && !!repoId && !!apiKey,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    // Use localStorage as initial data for instant load
    initialData: () => getFromCache('dependencies', repoId),
    // Don't refetch if we have fresh localStorage data
    initialDataUpdatedAt: () => {
      const cached = getFromCache('dependencies', repoId)
      return cached ? Date.now() - STALE_TIME + 1000 : 0
    }
  })
}

/**
 * Hook for fetching code style analysis with caching
 */
export function useStyleAnalysis({ repoId, apiKey, enabled = true }: UseCachedQueryOptions) {
  return useQuery({
    queryKey: ['style-analysis', repoId],
    queryFn: async () => {
      const data = await fetchWithAuth(
        `${API_URL}/repos/${repoId}/style-analysis`,
        apiKey
      )
      saveToCache('style-analysis', repoId, data)
      return data
    },
    enabled: enabled && !!repoId && !!apiKey,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    initialData: () => getFromCache('style-analysis', repoId),
    initialDataUpdatedAt: () => {
      const cached = getFromCache('style-analysis', repoId)
      return cached ? Date.now() - STALE_TIME + 1000 : 0
    }
  })
}

/**
 * Hook for fetching impact analysis with caching
 */
export function useImpactAnalysis({ 
  repoId, 
  apiKey, 
  filePath,
  enabled = true 
}: UseCachedQueryOptions & { filePath: string }) {
  const cacheKey = `impact:${filePath}`
  
  return useQuery({
    queryKey: ['impact', repoId, filePath],
    queryFn: async () => {
      const data = await fetchWithAuth(
        `${API_URL}/repos/${repoId}/impact?file_path=${encodeURIComponent(filePath)}`,
        apiKey
      )
      saveToCache(cacheKey, repoId, data)
      return data
    },
    enabled: enabled && !!repoId && !!apiKey && !!filePath,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    initialData: () => getFromCache(cacheKey, repoId),
  })
}

/**
 * Hook to invalidate all caches for a repo
 * Call this after re-indexing
 */
export function useInvalidateRepoCache() {
  const queryClient = useQueryClient()
  
  return (repoId: string) => {
    // Invalidate React Query cache
    queryClient.invalidateQueries({ queryKey: ['dependencies', repoId] })
    queryClient.invalidateQueries({ queryKey: ['style-analysis', repoId] })
    queryClient.invalidateQueries({ queryKey: ['impact', repoId] })
    
    // Invalidate localStorage cache
    invalidateRepoCache(repoId)
  }
}
