/**
 * IndexingProgress
 * 
 * Displays real-time progress during repository indexing.
 * Shows progress bar, file stats, and current file being processed.
 */

import { cn } from '@/lib/utils';
import { Progress } from '@/components/ui/progress';

export interface ProgressData {
  percent: number;
  filesProcessed: number;
  filesTotal: number;
  currentFile?: string;
  functionsFound: number;
}

interface IndexingProgressProps {
  progress: ProgressData;
  repoName?: string;
  onCancel?: () => void;
}

function AnimatedDots() {
  return (
    <span className="inline-flex" aria-hidden="true">
      <span className="animate-bounce" style={{ animationDelay: '0ms' }}>.</span>
      <span className="animate-bounce" style={{ animationDelay: '150ms' }}>.</span>
      <span className="animate-bounce" style={{ animationDelay: '300ms' }}>.</span>
    </span>
  );
}

/**
 * Estimate remaining time based on current progress.
 * Returns null if not enough data to estimate.
 */
function estimateRemainingSeconds(percent: number, filesProcessed: number): number | null {
  if (percent <= 0 || filesProcessed <= 0) return null;
  
  // Rough estimate: assume ~0.15s per file on average
  const remainingFiles = Math.ceil((filesProcessed / percent) * (100 - percent));
  return Math.max(1, Math.ceil(remainingFiles * 0.15));
}

export function IndexingProgress({ progress, repoName, onCancel }: IndexingProgressProps) {
  const { percent, filesProcessed, filesTotal, currentFile, functionsFound } = progress;
  const estimatedRemaining = estimateRemainingSeconds(percent, filesProcessed);

  return (
    <div 
      className="rounded-xl bg-zinc-900/80 border border-zinc-800 overflow-hidden"
      role="status"
      aria-label={`Indexing ${repoName || 'repository'}: ${percent}% complete`}
    >
      {/* Header */}
      <div className="px-5 py-4 border-b border-zinc-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg" aria-hidden="true">⚡</span>
            <span className="text-white font-medium">
              Indexing {repoName || 'repository'}
              <AnimatedDots />
            </span>
          </div>
          <span className="text-2xl font-bold text-indigo-400">
            {percent}%
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="px-5 py-4">
        <Progress 
          value={percent} 
          className="h-2 bg-zinc-800"
          aria-label={`${percent}% complete`}
        />
      </div>

      {/* Stats grid */}
      <div className="px-5 py-3 bg-zinc-900/50 border-t border-zinc-800">
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-zinc-500">Files</div>
            <div className="text-white font-medium">
              {filesProcessed} / {filesTotal}
            </div>
          </div>
          <div>
            <div className="text-zinc-500">Functions</div>
            <div className="text-white font-medium">
              {functionsFound.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-zinc-500">Remaining</div>
            <div className="text-white font-medium">
              {estimatedRemaining !== null ? `~${estimatedRemaining}s` : '—'}
            </div>
          </div>
        </div>
      </div>

      {/* Current file */}
      {currentFile && (
        <div className="px-5 py-3 border-t border-zinc-800">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-zinc-500" aria-hidden="true">📄</span>
            <span className="text-zinc-400 font-mono truncate" title={currentFile}>
              {currentFile}
            </span>
          </div>
        </div>
      )}

      {/* Cancel button */}
      {onCancel && (
        <div className="px-5 py-3 border-t border-zinc-800">
          <button
            type="button"
            onClick={onCancel}
            className={cn(
              'w-full py-2 px-4 rounded-lg text-sm',
              'bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200',
              'transition-colors duration-200'
            )}
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
