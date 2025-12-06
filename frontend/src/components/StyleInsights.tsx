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
      setData(result)
    } catch (error) {
      console.error('Error loading style data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="p-12 text-center">
        <div className="w-16 h-16 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-gray-400">Analyzing code style patterns...</p>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="p-6 space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
          <div className="text-sm text-gray-400 mb-1">Files Analyzed</div>
          <div className="text-3xl font-bold text-white">
            {data.summary?.total_files_analyzed || 0}
          </div>
        </div>

        <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
          <div className="text-sm text-gray-400 mb-1">Functions</div>
          <div className="text-3xl font-bold text-blue-400">
            {data.summary?.total_functions || 0}
          </div>
        </div>

        <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
          <div className="text-sm text-gray-400 mb-1">Async Adoption</div>
          <div className="text-3xl font-bold text-green-400">
            {data.summary?.async_adoption || '0%'}
          </div>
        </div>

        <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
          <div className="text-sm text-gray-400 mb-1">Type Hints</div>
          <div className="text-3xl font-bold text-purple-400">
            {data.summary?.type_hints_usage || '0%'}
          </div>
        </div>
      </div>

      {/* Naming Conventions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
          <h3 className="text-base font-semibold mb-4 text-white">Function Naming</h3>
          <div className="space-y-3">
            {data.naming_conventions?.functions && 
              Object.entries(data.naming_conventions.functions).map(([convention, info]: any) => (
                <div key={convention} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <code className="text-sm bg-white/5 px-2 py-1 rounded text-gray-300 border border-white/5">
                      {convention}
                    </code>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-500">{info.count}</span>
                    <span className="text-sm font-semibold text-blue-400 min-w-[50px] text-right">
                      {info.percentage}
                    </span>
                  </div>
                </div>
              ))
            }
          </div>
        </div>

        <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
          <h3 className="text-base font-semibold mb-4 text-white">Class Naming</h3>
          <div className="space-y-3">
            {data.naming_conventions?.classes && 
              Object.entries(data.naming_conventions.classes).map(([convention, info]: any) => (
                <div key={convention} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <code className="text-sm bg-white/5 px-2 py-1 rounded text-gray-300 border border-white/5">
                      {convention}
                    </code>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-500">{info.count}</span>
                    <span className="text-sm font-semibold text-blue-400 min-w-[50px] text-right">
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
      <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
        <h3 className="text-base font-semibold mb-4 text-white">Most Common Imports</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {data.top_imports?.slice(0, 10).map((item: any, idx: number) => (
            <div key={idx} className="flex items-center justify-between text-sm">
              <code className="text-gray-300 bg-white/5 border border-white/5 px-2 py-1 rounded truncate flex-1">
                {item.module}
              </code>
              <span className="ml-3 text-gray-500 font-mono">{item.count}×</span>
            </div>
          ))}
        </div>
      </div>

      {/* Patterns */}
      <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
        <h3 className="text-base font-semibold mb-4 text-white">Code Patterns</h3>
        <div className="space-y-3 text-sm">
          <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/5">
            <span className="text-gray-300">Async/Await Usage</span>
            <div className="flex items-center gap-2">
              <span className="text-gray-500">{data.patterns?.async_usage}</span>
              <span className="px-2 py-0.5 text-xs bg-green-500/10 text-green-400 border border-green-500/20 rounded">
                {data.patterns?.async_percentage?.toFixed(0)}%
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/5">
            <span className="text-gray-300">Type Annotations</span>
            <div className="flex items-center gap-2">
              <span className="text-gray-500">{data.patterns?.type_annotations}</span>
              <span className="px-2 py-0.5 text-xs bg-green-500/10 text-green-400 border border-green-500/20 rounded">
                {data.patterns?.typed_percentage?.toFixed(0)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Language Distribution */}
      <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
        <h3 className="text-base font-semibold mb-4 text-white">Language Distribution</h3>
        <div className="space-y-3">
          {data.language_distribution && 
            Object.entries(data.language_distribution).map(([lang, info]: any) => (
              <div key={lang} className="flex items-center gap-3">
                <span className="text-sm text-gray-300 w-24 capitalize">{lang}</span>
                <div className="flex-1 bg-white/5 rounded-full h-2">
                  <div 
                    className="bg-gradient-to-r from-blue-500 to-blue-600 h-2 rounded-full transition-all"
                    style={{ width: info.percentage }}
                  />
                </div>
                <span className="text-sm text-gray-400 w-16 text-right">{info.percentage}</span>
              </div>
            ))
          }
        </div>
      </div>
    </div>
  )
}
