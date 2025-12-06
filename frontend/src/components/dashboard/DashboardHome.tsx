import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import { useAuth } from '../../contexts/AuthContext'
import { RepoList } from '../RepoList'
import { AddRepoForm } from '../AddRepoForm'
import { SearchPanel } from '../SearchPanel'
import { DependencyGraph } from '../DependencyGraph'
import { RepoOverview } from '../RepoOverview'
import { StyleInsights } from '../StyleInsights'
import { ImpactAnalyzer } from '../ImpactAnalyzer'
import { PerformanceDashboard } from '../PerformanceDashboard'
import type { Repository } from '../../types'
import { API_URL } from '../../config/api'

type RepoTab = 'overview' | 'search' | 'dependencies' | 'insights' | 'impact'

export function DashboardHome() {
  const { session } = useAuth()
  const [repos, setRepos] = useState<Repository[]>([])
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<RepoTab>('overview')
  const [loading, setLoading] = useState(false)
  const [showPerformance, setShowPerformance] = useState(false)

  const fetchRepos = async () => {
    if (!session?.access_token) return
    
    try {
      const response = await fetch(`${API_URL}/api/repos`, {
        headers: { 'Authorization': `Bearer ${session.access_token}` }
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
  }, [session])

  const handleAddRepo = async (gitUrl: string, branch: string) => {
    try {
      setLoading(true)
      const name = gitUrl.split('/').pop()?.replace('.git', '') || 'unknown'
      
      const response = await fetch(`${API_URL}/api/repos`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session?.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name, git_url: gitUrl, branch })
      })
      
      const data = await response.json()
      
      await fetch(`${API_URL}/api/repos/${data.repo_id}/index`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${session?.access_token}` }
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
        headers: { 'Authorization': `Bearer ${session?.access_token}` }
      })
      await fetchRepos()
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

  // Tab button component
  const TabButton = ({ tab, label }: { tab: RepoTab; label: string }) => (
    <button
      onClick={() => setActiveTab(tab)}
      className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
        activeTab === tab
          ? 'bg-blue-500/10 text-blue-400'
          : 'text-gray-400 hover:text-white hover:bg-white/5'
      }`}
    >
      {label}
    </button>
  )

  return (
    <div className="pt-14 min-h-screen">
      {/* Performance Dashboard Toggle */}
      {showPerformance && (
        <div className="mb-6">
          <PerformanceDashboard apiUrl={API_URL} apiKey={session?.access_token || ''} />
        </div>
      )}

      {/* Repository List View */}
      {!isRepoView && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-white">Repositories</h1>
              <p className="text-sm text-gray-400 mt-1">
                {repos.length} repositories • {repos.filter(r => r.status === 'indexed').length} indexed
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowPerformance(!showPerformance)}
                className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                  showPerformance 
                    ? 'bg-blue-500/10 border-blue-500/30 text-blue-400'
                    : 'border-white/10 text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                📊 Performance
              </button>
              <AddRepoForm onAdd={handleAddRepo} loading={loading} />
            </div>
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

      {/* Single Repo View */}
      {isRepoView && (
        <div>
          {/* Back Button & Header */}
          <div className="mb-6">
            <button
              onClick={() => {
                setSelectedRepo(null)
                setActiveTab('overview')
              }}
              className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors mb-4"
            >
              <span>←</span>
              <span>Back to Repositories</span>
            </button>

            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-semibold text-white">{selectedRepoData.name}</h1>
                <p className="text-sm text-gray-400 mt-1 font-mono">{selectedRepoData.git_url}</p>
              </div>
              
              {selectedRepoData.status === 'indexed' && (
                <span className="px-3 py-1 bg-green-500/10 border border-green-500/30 text-green-400 text-sm rounded-full">
                  ✓ Indexed
                </span>
              )}
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-2 mb-6 p-1 bg-white/5 rounded-xl w-fit">
            <TabButton tab="overview" label="Overview" />
            <TabButton tab="search" label="Search" />
            <TabButton tab="dependencies" label="Dependencies" />
            <TabButton tab="insights" label="Code Style" />
            <TabButton tab="impact" label="Impact" />
          </div>

          {/* Tab Content */}
          <div className="bg-[#111113] border border-white/5 rounded-xl">
            {activeTab === 'overview' && (
              <RepoOverview 
                repo={selectedRepoData} 
                onReindex={handleReindex}
                apiUrl={API_URL}
                apiKey={session?.access_token || ''}
              />
            )}

            {activeTab === 'search' && (
              <SearchPanel 
                repoId={selectedRepo} 
                apiUrl={API_URL} 
                apiKey={session?.access_token || ''} 
              />
            )}

            {activeTab === 'dependencies' && (
              <DependencyGraph 
                repoId={selectedRepo} 
                apiUrl={API_URL} 
                apiKey={session?.access_token || ''} 
              />
            )}

            {activeTab === 'insights' && (
              <StyleInsights 
                repoId={selectedRepo} 
                apiUrl={API_URL} 
                apiKey={session?.access_token || ''} 
              />
            )}

            {activeTab === 'impact' && (
              <ImpactAnalyzer 
                repoId={selectedRepo} 
                apiUrl={API_URL} 
                apiKey={session?.access_token || ''} 
              />
            )}
          </div>
        </div>
      )}
    </div>
  )
}
