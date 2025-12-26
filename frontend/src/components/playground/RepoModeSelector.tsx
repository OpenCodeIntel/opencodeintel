/**
 * RepoModeSelector
 * 
 * Tab toggle between Demo repos and User's custom repo.
 * Used at the top of the Playground to switch input modes.
 */

import { cn } from '@/lib/utils';

export type RepoMode = 'demo' | 'custom';

interface RepoModeSelectorProps {
  mode: RepoMode;
  onModeChange: (mode: RepoMode) => void;
  disabled?: boolean;
}

export function RepoModeSelector({ 
  mode, 
  onModeChange, 
  disabled = false 
}: RepoModeSelectorProps) {
  return (
    <div 
      className="inline-flex items-center rounded-lg bg-zinc-900 p-1 border border-zinc-800"
      role="tablist"
      aria-label="Repository source"
    >
      <button
        type="button"
        role="tab"
        aria-selected={mode === 'demo'}
        aria-controls="demo-panel"
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
        type="button"
        role="tab"
        aria-selected={mode === 'custom'}
        aria-controls="custom-panel"
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
