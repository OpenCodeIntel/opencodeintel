/**
 * ValidationStatus
 * Shows validation result: loading, valid, invalid states
 */

import { cn } from '@/lib/utils';
import { ValidationResult } from '@/services/playground-api';

type ValidationState = 
  | { type: 'idle' }
  | { type: 'validating' }
  | { type: 'valid'; validation: ValidationResult }
  | { type: 'invalid'; error: string; reason?: string };

interface ValidationStatusProps {
  state: ValidationState;
  onStartIndexing?: () => void;
}

// Icons
const CheckIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

const XIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

const LockIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
  </svg>
);

const SpinnerIcon = () => (
  <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
  </svg>
);

const StarIcon = () => (
  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
  </svg>
);

function formatNumber(num: number): string {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k';
  }
  return num.toString();
}

export function ValidationStatus({ state, onStartIndexing }: ValidationStatusProps) {
  if (state.type === 'idle') {
    return null;
  }

  if (state.type === 'validating') {
    return (
      <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-zinc-900/50 border border-zinc-800">
        <SpinnerIcon />
        <span className="text-zinc-400">Checking repository...</span>
      </div>
    );
  }

  if (state.type === 'invalid') {
    const icon = state.reason === 'private' ? <LockIcon /> : <XIcon />;
    
    return (
      <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20">
        <span className="text-red-400">{icon}</span>
        <span className="text-red-300">{state.error}</span>
      </div>
    );
  }

  // Valid state
  const { validation } = state;
  
  return (
    <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3">
        <span className="text-emerald-400">
          <CheckIcon />
        </span>
        <span className="text-emerald-300 font-medium">Ready to index</span>
      </div>
      
      {/* Stats */}
      <div className="px-4 py-3 border-t border-emerald-500/10 flex flex-wrap items-center gap-4 text-sm">
        <div className="flex items-center gap-1.5 text-zinc-400">
          <span>📁</span>
          <span>{validation.file_count} files</span>
        </div>
        
        {validation.stars > 0 && (
          <div className="flex items-center gap-1.5 text-zinc-400">
            <StarIcon />
            <span>{formatNumber(validation.stars)}</span>
          </div>
        )}
        
        {validation.language && (
          <div className="flex items-center gap-1.5 text-zinc-400">
            <span>🔤</span>
            <span>{validation.language}</span>
          </div>
        )}
        
        <div className="flex items-center gap-1.5 text-zinc-400">
          <span>⏱️</span>
          <span>~{validation.estimated_time_seconds}s</span>
        </div>
      </div>

      {/* Action */}
      {onStartIndexing && (
        <div className="px-4 py-3 border-t border-emerald-500/10">
          <button
            onClick={onStartIndexing}
            className={cn(
              'w-full py-2.5 px-4 rounded-lg font-medium',
              'bg-indigo-600 hover:bg-indigo-500 text-white',
              'transition-colors duration-200',
              'flex items-center justify-center gap-2'
            )}
          >
            <span>🚀</span>
            Start Indexing
          </button>
        </div>
      )}
    </div>
  );
}
