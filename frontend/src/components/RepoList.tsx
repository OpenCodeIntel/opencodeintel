import type { Repository } from '../types'

interface RepoListProps {
  repos: Repository[]
  selectedRepo: string | null
  onSelect: (repoId: string) => void
}

export function RepoList({ repos, selectedRepo, onSelect }: RepoListProps) {
  if (repos.length === 0) {
    return (
      <div className="card p-16 text-center">
        <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
          <span className="text-4xl">📦</span>
        </div>
        <h3 className="text-base font-semibold mb-2 text-gray-900">No repositories yet</h3>
        <p className="text-sm text-gray-600">Add your first repository to start searching code semantically</p>
      </div>
    )
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'indexed':
        return <span className="badge-success">✓ Indexed</span>
      case 'cloned':
        return <span className="badge-success">✓ Ready</span>
      case 'indexing':
        return <span className="badge-warning">🔄 Indexing</span>
      case 'cloning':
        return <span className="badge-warning">⏳ Cloning</span>
      case 'error':
        return <span className="badge-danger">✗ Error</span>
      default:
        return <span className="badge-neutral">{status}</span>
    }
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {repos.map((repo) => {
        const isSelected = selectedRepo === repo.id

        return (
          <button
            key={repo.id}
            onClick={() => onSelect(repo.id)}
            className={`text-left card p-5 transition-all hover:shadow-md ${
              isSelected ? 'ring-2 ring-blue-500 shadow-md' : ''
            }`}
          >
            <div className="flex items-start justify-between mb-3">
              <h3 className="font-semibold text-base text-gray-900 truncate pr-2">
                {repo.name}
              </h3>
              {getStatusBadge(repo.status)}
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">Branch</span>
                <span className="font-mono text-gray-700">{repo.branch}</span>
              </div>

              {repo.file_count > 0 && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500">Functions</span>
                  <span className="font-mono font-semibold text-blue-600">
                    {repo.file_count.toLocaleString()}
                  </span>
                </div>
              )}
            </div>

            {isSelected && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <div className="flex items-center gap-2 text-xs text-blue-600 font-medium">
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                  Selected for search
                </div>
              </div>
            )}
          </button>
        )
      })}
    </div>
  )
}
