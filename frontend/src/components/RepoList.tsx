import type { Repository } from '../types'

interface RepoListProps {
  repos: Repository[]
  selectedRepo: string | null
  onSelect: (repoId: string) => void
}

// Status indicator with glow effect
const StatusIndicator = ({ status }: { status: string }) => {
  const config = {
    indexed: { color: 'green', label: 'Indexed', icon: '✓' },
    cloned: { color: 'blue', label: 'Ready', icon: '✓' },
    indexing: { color: 'yellow', label: 'Indexing', icon: '◌' },
    cloning: { color: 'yellow', label: 'Cloning', icon: '◌' },
    error: { color: 'red', label: 'Error', icon: '✗' },
  }[status] || { color: 'gray', label: status, icon: '•' }

  const colorClasses = {
    green: 'bg-green-500/10 text-green-400 border-green-500/20',
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    yellow: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20',
    gray: 'bg-white/5 text-gray-400 border-white/10',
  }[config.color]

  const glowClasses = {
    green: 'shadow-green-500/20',
    blue: 'shadow-blue-500/20',
    yellow: 'shadow-yellow-500/20',
    red: 'shadow-red-500/20',
    gray: '',
  }[config.color]

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium border rounded-full ${colorClasses} ${status === 'indexing' || status === 'cloning' ? 'animate-pulse' : ''}`}>
      <span>{config.icon}</span>
      <span>{config.label}</span>
    </span>
  )
}

export function RepoList({ repos, selectedRepo, onSelect }: RepoListProps) {
  if (repos.length === 0) {
    return (
      <div className="bg-[#111113] border border-white/5 rounded-2xl p-16 text-center">
        <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-white/5 flex items-center justify-center">
          <span className="text-4xl">📦</span>
        </div>
        <h3 className="text-lg font-semibold mb-2 text-white">No repositories yet</h3>
        <p className="text-sm text-gray-400 max-w-sm mx-auto">
          Add your first repository to start searching code semantically with AI
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {repos.map((repo) => {
        const isSelected = selectedRepo === repo.id

        return (
          <button
            key={repo.id}
            onClick={() => onSelect(repo.id)}
            className={`group relative text-left rounded-2xl p-5 transition-all duration-300 
              bg-[#111113] border overflow-hidden
              ${isSelected 
                ? 'border-blue-500/50 shadow-lg shadow-blue-500/10' 
                : 'border-white/5 hover:border-white/10 hover:bg-[#151518]'
              }`}
          >
            {/* Subtle gradient overlay on hover */}
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            
            {/* Content */}
            <div className="relative">
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg
                    ${isSelected 
                      ? 'bg-blue-500/20 border border-blue-500/30' 
                      : 'bg-white/5 border border-white/10 group-hover:bg-white/10'
                    } transition-colors`}
                  >
                    📁
                  </div>
                  <div>
                    <h3 className="font-semibold text-white truncate max-w-[140px]">
                      {repo.name}
                    </h3>
                    <p className="text-xs text-gray-500 font-mono">{repo.branch}</p>
                  </div>
                </div>
                <StatusIndicator status={repo.status} />
              </div>

              {/* Stats */}
              <div className="space-y-3">
                {repo.file_count > 0 && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-500">Functions indexed</span>
                    <span className="text-sm font-semibold text-blue-400 font-mono">
                      {repo.file_count.toLocaleString()}
                    </span>
                  </div>
                )}
                
                {/* Quick actions on hover */}
                <div className={`flex items-center gap-2 pt-3 border-t border-white/5 transition-all duration-200
                  ${isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}
                >
                  <span className="text-xs text-gray-500">Click to explore →</span>
                </div>
              </div>
            </div>

            {/* Selected indicator */}
            {isSelected && (
              <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-blue-500 to-blue-600 rounded-l-2xl" />
            )}
          </button>
        )
      })}
    </div>
  )
}
