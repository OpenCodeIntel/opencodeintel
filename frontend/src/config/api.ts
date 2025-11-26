/**
 * API Configuration
 * 
 * Centralizes API URL configuration for all frontend components.
 * 
 * - Production: Set VITE_API_URL in Vercel dashboard to Railway backend URL
 * - Development: Defaults to localhost:8000 (Docker Compose)
 * - Local dev without Docker: Can override with .env.local
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export { API_URL }
