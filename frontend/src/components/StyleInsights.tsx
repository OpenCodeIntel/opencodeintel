import { useEffect, useState } from 'react'

interface StyleInsightsProps {
  repoId: string
  apiUrl: string
  apiKey: string
}

export function StyleInsights({ repoId, apiUrl, apiKey }: StyleInsightsProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStyleData()
  }, [repoId])

  const loadStyleData = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${apiUrl}/api/repos/${repoId}/style-analysis`, {
        headers: { 'Authorization': `Bearer ${apiKey}` }
      })
      const result = await response.json()
      console.log('Style data:', result)
      setData(result)
    } catch (error) {
      console.error('Error loading style data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="card p-12 text-center">
        <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-gray-600">Analyzing code style patterns...</p>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-5">
          <div className="text-sm text-gray-600 mb-1">Files Analyzed</div>
          <div className="text-3xl font-bold text-gray-900">
            {data.summary?.total_files_analyzed || 0}
          </div>
        </div>

        <div className="card p-5">
          <div className="text-sm text-gray-600 mb-1">Functions</div>
          <div className="text-3xl font-bold text-blue-600">
            {data.summary?.total_functions || 0}
          </div>
        </div>

        <div className="card p-5">
          <div className="text-sm text-gray-600 mb-1">Async Adoption</div>
          <div className="text-3xl font-bold text-green-600">
            {data.summary?.async_adoption || '0%'}
          </div>
        </div>

        <div className="card p-5">
          <div className="text-sm text-gray-600 mb-1">Type Hints</div>
          <div className="text-3xl font-bold text-purple-600">
            {data.summary?.type_hints_usage || '0%'}
          </div>
        </div>
      </div>

      {/* Naming Conventions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card p-6">
          <h3 className="text-base font-semibold mb-4 text-gray-900">Function Naming</h3>
          <div className="space-y-3">
            {data.naming_conventions?.functions && 
              Object.entries(data.naming_conventions.functions).map(([convention, info]: any) => (
                <div key={convention} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <code className="text-sm bg-gray-100 px-2 py-1 rounded text-gray-700">
                      {convention}
                    </code>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-600">{info.count}</span>
                    <span className="text-sm font-semibold text-blue-600 min-w-[50px] text-right">
                      {info.percentage}
                    </span>
                  </div>
                </div>
              ))
            }
          </div>
        </div>

        <div className="card p-6">
          <h3 className="text-base font-semibold mb-4 text-gray-900">Class Naming</h3>
          <div className="space-y-3">
            {data.naming_conventions?.classes && 
              Object.entries(data.naming_conventions.classes).map(([convention, info]: any) => (
                <div key={convention} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <code className="text-sm bg-gray-100 px-2 py-1 rounded text-gray-700">
                      {convention}
                    </code>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-600">{info.count}</span>
                    <span className="text-sm font-semibold text-blue-600 min-w-[50px] text-right">
                      {info.percentage}
                    </span>
                  </div>
                </div>
              ))
            }
          </div>
        </div>
      </div>

      {/* Top Imports */}
      <div className="card p-6">
        <h3 className="text-base font-semibold mb-4 text-gray-900">Most Common Imports</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {data.top_imports?.slice(0, 10).map((item: any, idx: number) => (
            <div key={idx} className="flex items-center justify-between text-sm">
              <code className="text-gray-700 bg-gray-50 px-2 py-1 rounded truncate flex-1">
                {item.module}
              </code>
              <span className="ml-3 text-gray-600 font-mono">{item.count}×</span>
            </div>
          ))}
        </div>
      </div>

      {/* Patterns */}
      <div className="card p-6">
        <h3 className="text-base font-semibold mb-4 text-gray-900">Code Patterns</h3>
        <div className="space-y-3 text-sm">
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
            <span className="text-gray-700">Async/Await Usage</span>
            <div className="flex items-center gap-2">
              <span className="text-gray-600">{data.patterns?.async_usage}</span>
              <span className="badge-success">
                {data.patterns?.async_percentage?.toFixed(0)}%
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
            <span className="text-gray-700">Type Annotations</span>
            <div className="flex items-center gap-2">
              <span className="text-gray-600">{data.patterns?.type_annotations}</span>
              <span className="badge-success">
                {data.patterns?.typed_percentage?.toFixed(0)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Language Distribution */}
      <div className="card p-6">
        <h3 className="text-base font-semibold mb-4 text-gray-900">Language Distribution</h3>
        <div className="space-y-2">
          {data.language_distribution && 
            Object.entries(data.language_distribution).map(([lang, info]: any) => (
              <div key={lang} className="flex items-center gap-3">
                <span className="text-sm text-gray-700 w-24 capitalize">{lang}</span>
                <div className="flex-1 bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{ width: info.percentage }}
                  />
                </div>
                <span className="text-sm text-gray-600 w-16 text-right">{info.percentage}</span>
              </div>
            ))
          }
        </div>
      </div>
    </div>
  )
}
