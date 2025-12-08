import { useState } from 'react'

interface ImpactAnalyzerProps {
  repoId: string
  apiUrl: string
  apiKey: string
}

interface ImpactResult {
  file: string
  direct_dependents: string[]
  all_dependents: string[]
  dependent_count: number
  direct_dependencies: string[]
  dependency_count: number
  risk_level: string
  test_files: string[]
  impact_summary: string
}

export function ImpactAnalyzer({ repoId, apiUrl, apiKey }: ImpactAnalyzerProps) {
  const [filePath, setFilePath] = useState('')
  const [result, setResult] = useState<ImpactResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const analyzeImpact = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!filePath.trim()) return

    setLoading(true)
    setError('')
    
    try {
      const response = await fetch(`${apiUrl}/repos/${repoId}/impact`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          repo_id: repoId,
          file_path: filePath
        })
      })

      if (!response.ok) {
        throw new Error('Failed to analyze impact')
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError('Failed to analyze impact. Check if the file path is correct.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'high': return 'text-red-400 bg-red-500/10 border-red-500/20'
      case 'medium': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20'
      case 'low': return 'text-green-400 bg-green-500/10 border-green-500/20'
      default: return 'text-gray-400 bg-white/5 border-white/10'
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Input Form */}
      <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
        <h3 className="text-base font-semibold mb-4 text-white">Analyze Change Impact</h3>
        <form onSubmit={analyzeImpact} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2 text-gray-300">
              File Path (relative to repository root)
            </label>
            <input
              type="text"
              value={filePath}
              onChange={(e) => setFilePath(e.target.value)}
              placeholder="e.g., src/auth/middleware.py or components/Button.tsx"
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder:text-gray-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-all"
              disabled={loading}
            />
            <p className="mt-2 text-xs text-gray-500">
              Enter the path of the file you want to modify to see its impact
            </p>
          </div>

          <button
            type="submit"
            className="px-4 py-2.5 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white font-medium rounded-lg transition-all disabled:opacity-50"
            disabled={loading}
          >
            {loading ? 'Analyzing...' : 'Analyze Impact'}
          </button>
        </form>

        {error && (
          <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
            {error}
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Risk Assessment */}
          <div className={`bg-[#0a0a0c] rounded-xl p-5 border-2 ${getRiskColor(result.risk_level)}`}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold text-white">Risk Assessment</h3>
              <span className={`px-4 py-1.5 rounded-lg font-semibold uppercase text-sm border ${getRiskColor(result.risk_level)}`}>
                {result.risk_level} Risk
              </span>
            </div>
            <p className="text-sm font-mono text-gray-300 mb-4">
              {result.file}
            </p>
            <p className="text-sm text-gray-400">
              {result.impact_summary}
            </p>
          </div>

          {/* Impact Overview */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
              <div className="text-sm text-gray-400 mb-1">Direct Dependencies</div>
              <div className="text-3xl font-bold text-blue-400">
                {result.dependency_count}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Files this imports
              </div>
            </div>

            <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
              <div className="text-sm text-gray-400 mb-1">Total Impact</div>
              <div className="text-3xl font-bold text-yellow-400">
                {result.dependent_count}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Files affected by changes
              </div>
            </div>

            <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
              <div className="text-sm text-gray-400 mb-1">Test Files</div>
              <div className="text-3xl font-bold text-green-400">
                {result.test_files?.length || 0}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Related test coverage
              </div>
            </div>
          </div>

          {/* Dependencies (What This File Needs) */}
          {result.direct_dependencies && result.direct_dependencies.length > 0 && (
            <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
              <h3 className="text-base font-semibold mb-4 text-white">
                Dependencies ({result.direct_dependencies.length})
              </h3>
              <p className="text-sm text-gray-400 mb-3">
                Files this file imports (upstream)
              </p>
              <div className="space-y-1.5">
                {result.direct_dependencies.map((dep, idx) => (
                  <div key={idx} className="text-sm font-mono text-gray-300 bg-blue-500/10 border border-blue-500/20 px-3 py-2 rounded-lg">
                    {dep}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Dependents (What Breaks If Changed) */}
          {result.all_dependents && result.all_dependents.length > 0 && (
            <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
              <h3 className="text-base font-semibold mb-4 text-white">
                Affected Files ({result.all_dependents.length})
              </h3>
              <p className="text-sm text-gray-400 mb-3">
                Files that would be impacted by changes to this file (downstream)
              </p>
              <div className="space-y-1.5 max-h-96 overflow-y-auto">
                {result.all_dependents.map((dep, idx) => (
                  <div key={idx} className="text-sm font-mono text-gray-300 bg-yellow-500/10 border border-yellow-500/20 px-3 py-2 rounded-lg">
                    {dep}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Test Files */}
          {result.test_files && result.test_files.length > 0 && (
            <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
              <h3 className="text-base font-semibold mb-4 text-white">
                Related Tests ({result.test_files.length})
              </h3>
              <p className="text-sm text-gray-400 mb-3">
                Test files that may need updates
              </p>
              <div className="space-y-1.5">
                {result.test_files.map((test, idx) => (
                  <div key={idx} className="text-sm font-mono text-gray-300 bg-green-500/10 border border-green-500/20 px-3 py-2 rounded-lg">
                    {test}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
