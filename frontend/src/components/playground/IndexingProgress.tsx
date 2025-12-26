/**
 * IndexingProgress
 * Shows real-time progress during repo indexing
 */

import { cn } from '@/lib/utils';
import { Progress } from '@/components/ui/progress';

interface ProgressData {
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

// Animated dots for "processing" text
function AnimatedDots() {
  return (
    <span className="inline-flex">
      <span className="animate-[bounce_1s_ease-in-out_infinite]">.</span>
      <span className="animate-[bounce_1s_ease-in-out_0.2s_infinite]">.</span>
      <span className="animate-[bounce_1s_ease-in-out_0.4s_infinite]">.</span>
    </span>
  );
}

export function IndexingProgress({ progress, repoName, onCancel }: IndexingProgressProps) {
  const { percent, filesProcessed, filesTotal, currentFile, functionsFound } = progress;
  
  // Estimate remaining time (rough calculation)
  const estimatedRemaining = percent > 0 
    ? Math.ceil(((100 - percent) / percent) * (filesProcessed * 0.1))
    : null;

  return (
    <div className="rounded-xl bg-zinc-900/80 border border-zinc-800 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-zinc-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">⚡</span>
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
        />
      </div>

      {/* Stats */}
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
              {functionsFound}
            </div>
          </div>
          <div>
            <div className="text-zinc-500">Remaining</div>
            <div className="text-white font-medium">
              {estimatedRemaining !== null ? `~${estimatedRemaining}s` : '...'}
            </div>
          </div>
        </div>
      </div>

      {/* Current file */}
      {currentFile && (
        <div className="px-5 py-3 border-t border-zinc-800">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-zinc-500">📄</span>
            <span className="text-zinc-400 font-mono truncate">
              {currentFile}
            </span>
          </div>
        </div>
      )}

      {/* Cancel button */}
      {onCancel && (
        <div className="px-5 py-3 border-t border-zinc-800">
          <button
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
