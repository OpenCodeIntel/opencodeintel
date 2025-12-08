/**
 * API Configuration - Single Source of Truth for API Versioning
 * 
 * Change API_VERSION here to update all API calls across the frontend.
 * Example: "v1" -> "v2" will change /api/v1/* to /api/v2/*
 */

// =============================================================================
// BASE CONFIGURATION
// =============================================================================

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// =============================================================================
// API VERSION CONFIGURATION
// =============================================================================

export const API_VERSION = 'v1'

// =============================================================================
// DERIVED URLs (auto-calculated from version)
// =============================================================================

// API prefix: /api/v1
export const API_PREFIX = `/api/${API_VERSION}`

// Full API URL: http://localhost:8000/api/v1
export const API_URL = `${BASE_URL}${API_PREFIX}`

// WebSocket URL: ws://localhost:8000/api/v1
const WS_BASE = BASE_URL.replace(/^http/, 'ws')
export const WS_URL = `${WS_BASE}${API_PREFIX}`

// Legacy URL (for backward compatibility if needed)
export const LEGACY_API_URL = `${BASE_URL}/api`

// =============================================================================
// ENDPOINT HELPERS
// =============================================================================

/**
 * Build a full API endpoint URL
 * @param path - Endpoint path (e.g., '/repos', '/search')
 * @returns Full URL (e.g., 'http://localhost:8000/api/v1/repos')
 */
export const buildApiUrl = (path: string): string => {
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  return `${API_URL}${cleanPath}`
}

/**
 * Build a WebSocket endpoint URL
 * @param path - WebSocket path (e.g., '/ws/index/repo-123')
 * @returns Full WS URL (e.g., 'ws://localhost:8000/api/v1/ws/index/repo-123')
 */
export const buildWsUrl = (path: string): string => {
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  return `${WS_URL}${cleanPath}`
}
