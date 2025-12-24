import { useState, useRef, useEffect } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { toast } from 'sonner';
import type { SearchResult } from '../../types';

interface ResultCardProps {
  result: SearchResult;
  rank: number;
  isExpanded?: boolean;
  aiSummary?: string;
  repoUrl?: string;
}

export function ResultCard({ 
  result, 
  rank, 
  isExpanded: initialExpanded = false,
  aiSummary,
  repoUrl 
}: ResultCardProps) {
  const [expanded, setExpanded] = useState(initialExpanded);
  const contentRef = useRef<HTMLDivElement>(null);
  const [contentHeight, setContentHeight] = useState<number | undefined>(
    initialExpanded ? undefined : 0
  );
  
  const matchPercent = Math.round(result.score * 100);
  const isTopResult = rank === 1;
  
  // Extract clean file path (remove repos/{uuid}/ prefix if present)
  const cleanFilePath = result.file_path.replace(/^repos\/[a-f0-9-]+\//, '');
  const displayPath = cleanFilePath.split('/').slice(-3).join('/');
  
  // Build GitHub URL with clean path
  const githubUrl = repoUrl 
    ? `${repoUrl}/blob/main/${cleanFilePath}#L${result.line_start}-L${result.line_end}`
    : null;

  // Animate height on expand/collapse
  useEffect(() => {
    if (expanded) {
      const height = contentRef.current?.scrollHeight;
      setContentHeight(height);
      // After animation, set to auto for dynamic content
      const timer = setTimeout(() => setContentHeight(undefined), 200);
      return () => clearTimeout(timer);
    } else {
      // First set explicit height, then animate to 0
      const height = contentRef.current?.scrollHeight;
      setContentHeight(height);
      requestAnimationFrame(() => setContentHeight(0));
    }
  }, [expanded]);

  const copyCode = () => {
    navigator.clipboard.writeText(result.code);
    toast.success('Copied to clipboard');
  };

  return (
    <div 
      className={`
        card overflow-hidden transition-all duration-200
        ${expanded ? 'ring-1 ring-accent/20' : 'hover:border-border-accent'}
        ${isTopResult ? 'border-accent/30' : ''}
      `}
    >
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-start justify-between text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {isTopResult && (
              <span className="badge-accent text-[10px]">TOP MATCH</span>
            )}
            <h3 className="font-mono font-semibold text-sm text-text-primary truncate">
              {result.name || 'anonymous'}
            </h3>
            <span className="badge-neutral text-[10px] uppercase shrink-0">
              {result.type.replace('_', ' ')}
            </span>
          </div>
          <p className="text-xs text-text-muted font-mono truncate">{displayPath}</p>
        </div>

        <div className="flex items-center gap-3 ml-4 shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-16 h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-accent to-accent-light rounded-full transition-all"
                style={{ width: `${matchPercent}%` }}
              />
            </div>
            <span className="text-sm font-mono font-semibold text-accent w-10 text-right">
              {matchPercent}%
            </span>
          </div>
          
          <svg 
            className={`w-4 h-4 text-text-muted transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Expandable content with animation */}
      <div 
        ref={contentRef}
        className="overflow-hidden transition-all duration-200 ease-out"
        style={{ height: contentHeight !== undefined ? contentHeight : 'auto' }}
      >
        <div className="border-t border-border">
          {/* AI Summary */}
          {aiSummary && isTopResult && (
            <div className="px-4 py-3 bg-accent/5 border-b border-border">
              <div className="flex items-start gap-2">
                <span className="text-accent text-sm">✨</span>
                <div>
                  <p className="text-xs font-medium text-accent mb-1">AI Summary</p>
                  <p className="text-sm text-text-secondary leading-relaxed">{aiSummary}</p>
                </div>
              </div>
            </div>
          )}

          {/* Code block */}
          <div className="relative">
            <SyntaxHighlighter
              language={result.language || 'text'}
              style={oneDark}
              customStyle={{
                margin: 0,
                borderRadius: 0,
                fontSize: '0.75rem',
                lineHeight: '1.6',
                background: 'var(--color-bg-secondary)',
                padding: '1rem',
              }}
              showLineNumbers
              startingLineNumber={result.line_start}
              wrapLines
            >
              {result.code}
            </SyntaxHighlighter>

            <span className="absolute top-3 right-3 px-2 py-0.5 text-[10px] font-mono uppercase bg-bg-tertiary text-text-muted rounded">
              {result.language}
            </span>
          </div>

          {/* Footer */}
          <div className="px-4 py-3 bg-bg-secondary/50 flex items-center justify-between">
            <span className="text-xs text-text-muted font-mono">
              Lines {result.line_start}–{result.line_end}
            </span>
            
            <div className="flex items-center gap-2">
              <button
                onClick={copyCode}
                className="btn-ghost px-3 py-1.5 text-xs flex items-center gap-1.5"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Copy
              </button>
              
              {githubUrl && (
                <a
                  href={githubUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-ghost px-3 py-1.5 text-xs flex items-center gap-1.5"
                >
                  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                  </svg>
                  View
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
