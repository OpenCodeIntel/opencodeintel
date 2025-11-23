import { useEffect, useState } from 'react'

interface PerformanceProps {
  apiUrl: string
  apiKey: string
}

export function PerformanceDashboard({ apiUrl, apiKey }: PerformanceProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadMetrics()
    const interval = setInterval(loadMetrics, 5000) // Refresh every 5s
    return () => clearInterval(interval)
  }, [])

  const loadMetrics = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/metrics`, {
        headers: { 'Authorization': `Bearer ${apiKey}` }
      })
      const result = await response.json()
      setData(result)
      setLoading(false)
    } catch (error) {
      console.error('Error loading metrics:', error)
    }
  }

  if (loading) {
    return <div className="card p-12 text-center text-gray-600">Loading metrics...</div>
  }

  if (!data) return null

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Performance Metrics</h1>
        <p className="text-sm text-gray-600 mt-1">Real-time system performance monitoring</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-6">
          <div className="text-sm text-gray-600 mb-1">Cache Hit Rate</div>
          <div className="text-3xl font-bold text-green-600">
            {data.search?.cache_hit_rate || '0%'}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {data.search?.cache_hits || 0} / {data.search?.total_searches || 0} searches
          </div>
        </div>

        <div className="card p-6">
          <div className="text-sm text-gray-600 mb-1">Avg Search Time</div>
          <div className="text-3xl font-bold text-blue-600">
            {data.search?.avg_duration_ms?.toFixed(0) || 0}ms
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Response latency
          </div>
        </div>

        <div className="card p-6">
          <div className="text-sm text-gray-600 mb-1">Indexing Speed</div>
          <div className="text-3xl font-bold text-purple-600">
            {data.indexing?.avg_speed_functions_per_sec?.toFixed(1) || 0}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Functions per second
          </div>
        </div>

        <div className="card p-6">
          <div className="text-sm text-gray-600 mb-1">Total Searches</div>
          <div className="text-3xl font-bold text-gray-900">
            {data.search?.total_searches || 0}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Since server start
          </div>
        </div>
      </div>

      {/* Indexing Performance */}
      <div className="card p-6">
        <h3 className="text-base font-semibold mb-4 text-gray-900">Indexing Performance</h3>
        <div className="grid grid-cols-3 gap-6 mb-4">
          <div>
            <div className="text-xs text-gray-600 mb-1">Average Speed</div>
            <div className="text-lg font-semibold text-gray-900">
              {data.indexing?.avg_speed_functions_per_sec?.toFixed(1) || 0} func/sec
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-600 mb-1">Peak Speed</div>
            <div className="text-lg font-semibold text-green-600">
              {data.indexing?.max_speed?.toFixed(1) || 0} func/sec
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-600 mb-1">Total Operations</div>
            <div className="text-lg font-semibold text-gray-900">
              {data.indexing?.total_operations || 0}
            </div>
          </div>
        </div>

        {data.indexing?.recent_operations && data.indexing.recent_operations.length > 0 && (
          <>
            <h4 className="text-sm font-medium text-gray-700 mb-3">Recent Indexing Operations</h4>
            <div className="space-y-2">
              {data.indexing.recent_operations.slice(-5).reverse().map((op: any, idx: number) => (
                <div key={idx} className="flex items-center justify-between text-sm bg-gray-50 p-3 rounded">
                  <span className="text-gray-700 font-mono truncate flex-1">
                    Repo: {op.repo_id.substring(0, 8)}...
                  </span>
                  <span className="text-gray-600 ml-3">
                    {op.function_count} functions
                  </span>
                  <span className="text-blue-600 font-semibold ml-3">
                    {op.speed?.toFixed(1)} func/sec
                  </span>
                  <span className="text-gray-500 text-xs ml-3">
                    {op.duration?.toFixed(1)}s
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Search Performance */}
      <div className="card p-6">
        <h3 className="text-base font-semibold mb-4 text-gray-900">Search Performance</h3>
        
        <div className="grid grid-cols-2 gap-6 mb-4">
          <div>
            <div className="text-xs text-gray-600 mb-2">Cache Efficiency</div>
            <div className="flex items-center gap-4">
              <div className="flex-1 bg-gray-200 rounded-full h-3">
                <div 
                  className="bg-green-500 h-3 rounded-full transition-all"
                  style={{ 
                    width: `${parseFloat(data.search?.cache_hit_rate || '0%')}%` 
                  }}
                />
              </div>
              <span className="text-sm font-semibold text-green-600 w-16">
                {data.search?.cache_hit_rate || '0%'}
              </span>
            </div>
          </div>

          <div>
            <div className="text-xs text-gray-600 mb-2">Response Time</div>
            <div className="text-lg font-semibold text-blue-600">
              {data.search?.avg_duration_ms?.toFixed(0) || 0}ms average
            </div>
          </div>
        </div>

        {data.search?.recent_searches && data.search.recent_searches.length > 0 && (
          <>
            <h4 className="text-sm font-medium text-gray-700 mb-3">Recent Searches</h4>
            <div className="space-y-2">
              {data.search.recent_searches.slice(-5).reverse().map((search: any, idx: number) => (
                <div key={idx} className="flex items-center justify-between text-sm bg-gray-50 p-3 rounded">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    search.cached ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
                  }`}>
                    {search.cached ? '⚡ Cached' : '🔍 Fresh'}
                  </span>
                  <span className="text-gray-600 ml-auto font-mono">
                    {(search.duration * 1000).toFixed(0)}ms
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* System Health */}
      <div className="card p-6 bg-green-50 border-green-200">
        <h3 className="text-base font-semibold text-gray-900 mb-3">System Health</h3>
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-gray-700">
              Cache: <span className="font-semibold">{data.summary?.cache_working ? 'Active' : 'Inactive'}</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-gray-700">
              Indexing: <span className="font-semibold capitalize">{data.summary?.indexing_performance || 'Unknown'}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
