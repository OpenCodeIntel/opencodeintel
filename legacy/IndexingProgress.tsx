import { useEffect, useState } from 'react'

interface IndexingProgressProps {
  repoId: string
  apiUrl: string
  apiKey: string
  onComplete: () => void
}

export function IndexingProgress({ repoId, apiUrl, apiKey, onComplete }: IndexingProgressProps) {
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState('Starting...')
  const [stats, setStats] = useState({ processed: 0, total: 0, functions: 0 })

  useEffect(() => {
    let interval: any
    
    const checkProgress = async () => {
      try {
        const response = await fetch(`${apiUrl}/api/repos/${repoId}`, {
          headers: { 'Authorization': `Bearer ${apiKey}` }
        })
        const repo = await response.json()
        
        if (repo.status === 'indexed') {
          setProgress(100)
          setStatus('✅ Indexing complete!')
          clearInterval(interval)
          setTimeout(onComplete, 1500)
        } else if (repo.status === 'indexing') {
          // Estimate progress based on function count growth
          const estimatedProgress = Math.min(95, (repo.file_count / 100) * 100)
          setProgress(estimatedProgress)
          setStatus(`📊 Indexing... ${repo.file_count} functions processed`)
          setStats({
            processed: repo.file_count,
            total: 100,
            functions: repo.file_count
          })
        }
      } catch (error) {
        console.error('Error checking progress:', error)
      }
    }
    
    // Check immediately, then every 2 seconds
    checkProgress()
    interval = setInterval(checkProgress, 2000)
    
    return () => clearInterval(interval)
  }, [repoId])

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full mx-4">
        <h3 className="text-xl font-semibold mb-6 text-gray-900">
          Indexing Repository
        </h3>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-gray-600">{status}</span>
            <span className="font-semibold text-blue-600">{progress.toFixed(0)}%</span>
          </div>
          
          {/* Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          
          {/* Stats */}
          {stats.functions > 0 && (
            <div className="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-gray-200">
              <div>
                <div className="text-xs text-gray-500">Functions Found</div>
                <div className="text-2xl font-bold text-gray-900">{stats.functions}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Status</div>
                <div className="text-sm font-semibold text-blue-600">Processing...</div>
              </div>
            </div>
          )}
          
          <p className="text-xs text-gray-500 mt-4">
            Using batch processing for optimal performance
          </p>
        </div>
      </div>
    </div>
  )
}
