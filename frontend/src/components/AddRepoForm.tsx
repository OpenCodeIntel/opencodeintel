import { useState } from 'react'

interface AddRepoFormProps {
  onAdd: (gitUrl: string, branch: string) => Promise<void>
  loading: boolean
}

export function AddRepoForm({ onAdd, loading }: AddRepoFormProps) {
  const [gitUrl, setGitUrl] = useState('')
  const [branch, setBranch] = useState('main')
  const [showForm, setShowForm] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!gitUrl) return

    await onAdd(gitUrl, branch)
    setGitUrl('')
    setBranch('main')
    setShowForm(false)
  }

  if (!showForm) {
    return (
      <button
        onClick={() => setShowForm(true)}
        className="btn-primary"
        disabled={loading}
      >
        + Add Repository
      </button>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-5 border-b border-gray-200">
          <h3 className="text-base font-semibold text-gray-900">Add Repository</h3>
          <button
            onClick={() => setShowForm(false)}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            disabled={loading}
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2 text-gray-700">
              Git URL
            </label>
            <input
              type="url"
              value={gitUrl}
              onChange={(e) => setGitUrl(e.target.value)}
              placeholder="https://github.com/username/repo"
              className="input"
              required
              disabled={loading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2 text-gray-700">
              Branch
            </label>
            <input
              type="text"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              placeholder="main"
              className="input"
              required
              disabled={loading}
            />
            <p className="mt-1.5 text-xs text-gray-500">
              The repository will be cloned and automatically indexed
            </p>
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="submit"
              className="btn-primary flex-1"
              disabled={loading}
            >
              {loading ? 'Adding...' : 'Add & Index'}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowForm(false)
                setGitUrl('')
                setBranch('main')
              }}
              className="btn-secondary px-6"
              disabled={loading}
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
