/**
 * RepoModeSelector
 * Tab toggle between Demo repos and User's own repo
 */

import { cn } from '@/lib/utils';

export type RepoMode = 'demo' | 'custom';

interface RepoModeSelectorProps {
  mode: RepoMode;
  onModeChange: (mode: RepoMode) => void;
  disabled?: boolean;
}

export function RepoModeSelector({ mode, onModeChange, disabled }: RepoModeSelectorProps) {
  return (
    <div className="inline-flex items-center rounded-lg bg-zinc-900 p-1 border border-zinc-800">
      <button
        onClick={() => onModeChange('demo')}
        disabled={disabled}
        className={cn(
          'px-4 py-2 text-sm font-medium rounded-md transition-all duration-200',
          mode === 'demo'
            ? 'bg-zinc-800 text-white shadow-sm'
            : 'text-zinc-400 hover:text-zinc-200',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        Demo Repos
      </button>
      <button
        onClick={() => onModeChange('custom')}
        disabled={disabled}
        className={cn(
          'px-4 py-2 text-sm font-medium rounded-md transition-all duration-200',
          mode === 'custom'
            ? 'bg-indigo-600 text-white shadow-sm'
            : 'text-zinc-400 hover:text-zinc-200',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        Your Repo
      </button>
    </div>
  );
}
