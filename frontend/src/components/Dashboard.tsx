import { useState, useEffect } from 'react'
import { Toaster } from '@/components/ui/sonner'
import { toast } from 'sonner'
import { RepoList } from './RepoList'
import { AddRepoForm } from './AddRepoForm'
import { SearchPanel } from './SearchPanel'
import { DependencyGraph } from './DependencyGraph'
import { RepoOverview } from './RepoOverview'
import { StyleInsights } from './StyleInsights'
import { ImpactAnalyzer } from './ImpactAnalyzer'
import { PerformanceDashboard } from './PerformanceDashboard'
import { UserNav } from './UserNav'
import type { Repository } from '../types'

const API_URL = 'http://localhost:8000'
const API_KEY = 'dev-secret-key'

type RepoTab = 'overview' | 'search' | 'dependencies' | 'insights' | 'impact'

export function Dashboard() {
  const [repos, setRepos] = useState<Repository[]>([])
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<RepoTab>('overview')
  const [loading, setLoading] = useState(false)
  const [showPerformance, setShowPerformance] = useState(false)

  const fetchRepos = async () => {
    try {
      const response = await fetch(`${API_URL}/api/repos`, {
        headers: { 'Authorization': `Bearer ${API_KEY}` }
      })
      const data = await response.json()
      setRepos(data.repositories || [])
    } catch (error) {
      console.error('Error fetching repos:', error)
    }
  }

  useEffect(() => {
    fetchRepos()
    const interval = setInterval(fetchRepos, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleAddRepo = async (gitUrl: string, branch: string) => {
    try {
      setLoading(true)
      const name = gitUrl.split('/').pop()?.replace('.git', '') || 'unknown'
      
      const response = await fetch(`${API_URL}/api/repos`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${API_KEY}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name, git_url: gitUrl, branch })
      })
      
      const data = await response.json()
      
      await fetch(`${API_URL}/api/repos/${data.repo_id}/index`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${API_KEY}` }
      })
      
      await fetchRepos()
      toast.success('Repository added!', {
        description: `${name} is now being indexed`
      })
    } catch (error) {
      console.error('Error adding repo:', error)
      toast.error('Failed to add repository', {
        description: 'Please check the Git URL and try again'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleReindex = async () => {
    if (!selectedRepo) return
    
    try {
      setLoading(true)
      await fetch(`${API_URL}/api/repos/${selectedRepo}/index`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${API_KEY}` }
      })
      await fetchRepos()
      // RepoOverview component will show the toast and progress
    } catch (error) {
      toast.error('Re-indexing failed', {
        description: 'Please check the console for details'
      })
    } finally {
      setLoading(false)
    }
  }

  const selectedRepoData = repos.find(r => r.id === selectedRepo)
  const isRepoView = selectedRepo && selectedRepoData

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
                <span className="text-white font-bold text-sm">CI</span>
              </div>
              <span className="font-semibold text-gray-900">CodeIntel</span>
              <span className="text-xs text-gray-400 ml-2">MCP Server</span>
            </div>

            <div className="flex items-center gap-4">
              <button
                onClick={() => setShowPerformance(!showPerformance)}
                className={`text-xs px-3 py-1.5 rounded-md transition-colors ${
                  showPerformance 
                    ? 'bg-blue-100 text-blue-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                📊 Performance
              </button>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <span>API Connected</span>
              </div>
              <div className="text-xs text-gray-400 border-l border-gray-200 pl-4">
                {repos.length} repos • {repos.filter(r => r.status === 'indexed').length} indexed
              </div>
              <div className="border-l border-gray-200 pl-4">
                <UserNav />
              </div>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Performance Dashboard Overlay */}
        {showPerformance && (
          <div className="mb-6">
            <PerformanceDashboard apiUrl={API_URL} apiKey={API_KEY} />
          </div>
        )}

        {!isRepoView && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-semibold text-gray-900">Repositories</h1>
                <p className="text-sm text-gray-600 mt-1">Manage and index your codebases</p>
              </div>
              <AddRepoForm onAdd={handleAddRepo} loading={loading} />
            </div>
            
            <RepoList 
              repos={repos} 
              selectedRepo={selectedRepo}
              onSelect={(id) => {
                setSelectedRepo(id)
                setActiveTab('overview')
              }}
            />
          </div>
        )}

        {isRepoView && (
          <div>
            <div className="mb-6">
              <button
                onClick={() => {
                  setSelectedRepo(null)
                  setActiveTab('overview')
                }}
                className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-4"
              >
                <span>←</span>
                <span>Back to Repositories</span>
              </button>

              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-2xl font-semibold text-gray-900">{selectedRepoData.name}</h1>
                  <p className="text-sm text-gray-600 mt-1 font-mono">{selectedRepoData.git_url}</p>
                </div>
                
                {selectedRepoData.status === 'indexed' && (
                  <span className="badge-success">✓ Indexed</span>
                )}
              </div>
            </div>

            <div className="border-b border-gray-200 mb-6">
              <div className="flex gap-6 overflow-x-auto">
                <button
                  onClick={() => setActiveTab('overview')}
                  className={`pb-3 border-b-2 transition-colors whitespace-nowrap ${
                    activeTab === 'overview'
                      ? 'border-blue-600 text-gray-900 font-medium'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Overview
                </button>
                <button
                  onClick={() => setActiveTab('search')}
                  className={`pb-3 border-b-2 transition-colors whitespace-nowrap ${
                    activeTab === 'search'
                      ? 'border-blue-600 text-gray-900 font-medium'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Search
                </button>
                <button
                  onClick={() => setActiveTab('dependencies')}
                  className={`pb-3 border-b-2 transition-colors whitespace-nowrap ${
                    activeTab === 'dependencies'
                      ? 'border-blue-600 text-gray-900 font-medium'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Dependencies
                </button>
                <button
                  onClick={() => setActiveTab('insights')}
                  className={`pb-3 border-b-2 transition-colors whitespace-nowrap ${
                    activeTab === 'insights'
                      ? 'border-blue-600 text-gray-900 font-medium'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Code Style
                </button>
                <button
                  onClick={() => setActiveTab('impact')}
                  className={`pb-3 border-b-2 transition-colors whitespace-nowrap ${
                    activeTab === 'impact'
                      ? 'border-blue-600 text-gray-900 font-medium'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Impact
                </button>
              </div>
            </div>

            {activeTab === 'overview' && (
              <RepoOverview 
                repo={selectedRepoData} 
                onReindex={handleReindex}
                apiUrl={API_URL}
                apiKey={API_KEY}
              />
            )}

            {activeTab === 'search' && (
              <SearchPanel repoId={selectedRepo} apiUrl={API_URL} apiKey={API_KEY} />
            )}

            {activeTab === 'dependencies' && (
              <DependencyGraph repoId={selectedRepo} apiUrl={API_URL} apiKey={API_KEY} />
            )}

            {activeTab === 'insights' && (
              <StyleInsights repoId={selectedRepo} apiUrl={API_URL} apiKey={API_KEY} />
            )}

            {activeTab === 'impact' && (
              <ImpactAnalyzer repoId={selectedRepo} apiUrl={API_URL} apiKey={API_KEY} />
            )}
          </div>
        )}
      </main>
      <Toaster />
    </div>
  )
}
