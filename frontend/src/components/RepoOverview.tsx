import { useState, useEffect, useRef } from 'react'
import { toast } from 'sonner'
import { Progress } from '@/components/ui/progress'
import type { Repository } from '../types'
import { WS_URL } from '../config/api'

interface RepoOverviewProps {
  repo: Repository
  onReindex: () => void
  apiUrl: string
  apiKey: string
}

interface IndexProgress {
  files_processed: number
  functions_indexed: number
  total_files: number
  progress_pct: number
}

export function RepoOverview({ repo, onReindex, apiUrl, apiKey }: RepoOverviewProps) {
  const [indexing, setIndexing] = useState(false)
  const [progress, setProgress] = useState<IndexProgress | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const completedRef = useRef(false)

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const handleReindex = async () => {
    setIndexing(true)
    setProgress({ files_processed: 0, functions_indexed: 0, total_files: 0, progress_pct: 0 })
    completedRef.current = false
    
    const wsUrl = `${WS_URL}/ws/index/${repo.id}?token=${apiKey}`
    
    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        toast.loading('Indexing started...', { id: 'reindex' })
      }

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        
        if (data.type === 'progress') {
          setProgress({
            files_processed: data.files_processed,
            functions_indexed: data.functions_indexed,
            total_files: data.total_files,
            progress_pct: data.progress_pct
          })
        } else if (data.type === 'complete') {
          completedRef.current = true
          toast.success(`Indexing complete! ${data.total_functions} functions indexed.`, { id: 'reindex' })
          setIndexing(false)
          setProgress(null)
          onReindex()
        } else if (data.type === 'error') {
          completedRef.current = true
          toast.error(`Indexing failed: ${data.message}`, { id: 'reindex' })
          setIndexing(false)
          setProgress(null)
        }
      }

      ws.onerror = () => {
        if (!completedRef.current) {
          toast.dismiss('reindex')
          fallbackToHttp()
        }
      }

      ws.onclose = () => {
        if (!completedRef.current) {
          fallbackToHttp()
        }
      }

    } catch {
      fallbackToHttp()
    }
  }

  const fallbackToHttp = async () => {
    if (completedRef.current) return
    
    toast.loading('Using fallback indexing...', { id: 'reindex' })
    
    try {
      await onReindex()
      toast.success('Re-indexing started!', { id: 'reindex' })
      
      let pct = 10
      const interval = setInterval(() => {
        pct = Math.min(pct + 10, 90)
        setProgress(prev => prev ? { ...prev, progress_pct: pct } : null)
      }, 1000)
      
      setTimeout(() => {
        clearInterval(interval)
        setProgress(null)
        setIndexing(false)
        completedRef.current = true
      }, 8000)
      
    } catch {
      setIndexing(false)
      setProgress(null)
      toast.error('Failed to start re-indexing', { id: 'reindex' })
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
          <div className="text-sm text-gray-400 mb-2">Status</div>
          <div className="flex items-center gap-2">
            {repo.status === 'indexed' && (
              <span className="px-2.5 py-1 text-sm font-medium bg-green-500/10 text-green-400 border border-green-500/20 rounded-full">
                ✓ Indexed
              </span>
            )}
            {repo.status === 'cloned' && (
              <span className="px-2.5 py-1 text-sm font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-full">
                ✓ Ready
              </span>
            )}
            {repo.status === 'indexing' && (
              <span className="px-2.5 py-1 text-sm font-medium bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 rounded-full animate-pulse">
                🔄 Indexing
              </span>
            )}
          </div>
        </div>

        <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
          <div className="text-sm text-gray-400 mb-2">Functions Indexed</div>
          <div className="text-3xl font-bold text-blue-400">
            {repo.file_count?.toLocaleString() || 0}
          </div>
        </div>

        <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
          <div className="text-sm text-gray-400 mb-2">Branch</div>
          <div className="text-lg font-mono text-white">
            {repo.branch}
          </div>
        </div>
      </div>

      {/* Indexing Progress */}
      {indexing && progress && (
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-base font-semibold text-white">🔄 Indexing in Progress</h3>
            <span className="text-sm font-mono text-blue-400">{progress.progress_pct}%</span>
          </div>
          <Progress value={progress.progress_pct} className="h-2" />
          <div className="flex justify-between text-xs text-gray-400 mt-2">
            <span>Files: {progress.files_processed}/{progress.total_files || '?'}</span>
            <span>Functions: {progress.functions_indexed}</span>
          </div>
        </div>
      )}

      {/* Repository Info */}
      <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5 space-y-4">
        <h3 className="text-base font-semibold text-white">Repository Details</h3>
        
        <div className="space-y-3 text-sm">
          <div className="flex items-start gap-3">
            <span className="text-gray-500 w-24">Name:</span>
            <span className="text-white font-medium">{repo.name}</span>
          </div>

          <div className="flex items-start gap-3">
            <span className="text-gray-500 w-24">Git URL:</span>
            <a 
              href={repo.git_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-blue-400 hover:text-blue-300 font-mono text-xs break-all transition-colors"
            >
              {repo.git_url}
            </a>
          </div>

          <div className="flex items-start gap-3">
            <span className="text-gray-500 w-24">Local Path:</span>
            <span className="text-gray-300 font-mono text-xs">{repo.local_path}</span>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
        <h3 className="text-base font-semibold text-white mb-3">Actions</h3>
        <p className="text-sm text-gray-400 mb-4">
          Re-indexing uses <span className="text-white font-medium">incremental mode</span> - only processes changed files for 100x faster updates!
        </p>
        <div className="flex gap-3">
          <button
            onClick={handleReindex}
            disabled={indexing}
            className="px-4 py-2.5 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white text-sm font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {indexing ? '🔄 Indexing...' : '🔄 Re-index Repository'}
          </button>
          <button
            className="px-4 py-2.5 bg-white/5 border border-white/10 text-gray-300 text-sm font-medium rounded-lg hover:bg-white/10 transition-colors"
            onClick={() => toast.info('Delete functionality coming soon')}
          >
            🗑️ Remove
          </button>
        </div>
      </div>

      {/* Quick Guide */}
      <div className="bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-blue-500/20 rounded-xl p-5">
        <h3 className="text-base font-semibold text-white mb-3">💡 Quick Guide</h3>
        <ul className="text-sm text-gray-300 space-y-2">
          <li>• <span className="text-white font-medium">Search</span> tab - Find code by meaning, not keywords</li>
          <li>• <span className="text-white font-medium">Dependencies</span> tab - Visualize code architecture</li>
          <li>• <span className="text-white font-medium">Code Style</span> tab - Analyze team coding patterns</li>
          <li>• <span className="text-white font-medium">Impact</span> tab - See what breaks when you change a file</li>
          <li>• Use with Claude Desktop via MCP for AI-powered code understanding</li>
        </ul>
      </div>
    </div>
  )
}
