import { useState } from 'react';
import { toast } from 'sonner';
import { SearchBox, ResultCard } from './search';
import type { SearchResult } from '../types';

interface SearchPanelProps {
  repoId: string;
  apiUrl: string;
  apiKey: string;
  repoUrl?: string;
}

export function SearchPanel({ repoId, apiUrl, apiKey, repoUrl }: SearchPanelProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTime, setSearchTime] = useState<number | null>(null);
  const [cached, setCached] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [aiSummary, setAiSummary] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setHasSearched(true);
    setAiSummary(null);
    const startTime = Date.now();

    try {
      const response = await fetch(`${apiUrl}/search`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          repo_id: repoId,
          max_results: 10,
        }),
      });

      const data = await response.json();
      setResults(data.results || []);
      setSearchTime(Date.now() - startTime);
      setCached(data.cached || false);
      
      if (data.ai_summary) {
        setAiSummary(data.ai_summary);
      }
    } catch (error) {
      console.error('Search error:', error);
      toast.error('Search failed', {
        description: 'Please check your query and try again',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Search Box */}
      <div className="card p-5">
        <SearchBox
          value={query}
          onChange={setQuery}
          onSubmit={handleSearch}
          loading={loading}
          autoFocus
        />

        {searchTime !== null && (
          <div className="mt-4 pt-4 border-t border-border flex items-center gap-4 text-sm text-text-secondary">
            <span>
              <span className="font-semibold text-text-primary">{results.length}</span> results
            </span>
            <span className="text-text-muted">•</span>
            <span className="font-mono">
              <span className="font-semibold text-text-primary">{searchTime}</span>ms
            </span>
            {cached && (
              <>
                <span className="text-text-muted">•</span>
                <span className="badge-success">⚡ Cached</span>
              </>
            )}
          </div>
        )}
      </div>

      {/* Results */}
      <div className="space-y-3">
        {results.map((result, idx) => (
          <ResultCard
            key={`${result.file_path}-${result.line_start}-${idx}`}
            result={result}
            rank={idx + 1}
            isExpanded={idx === 0}
            aiSummary={idx === 0 ? aiSummary || undefined : undefined}
            repoUrl={repoUrl}
          />
        ))}
      </div>

      {/* Empty State */}
      {results.length === 0 && hasSearched && !loading && (
        <div className="card p-16 text-center">
          <div className="w-20 h-20 mx-auto mb-4 rounded-2xl glass flex items-center justify-center">
            <span className="text-4xl">🔍</span>
          </div>
          <h3 className="text-base font-semibold mb-2 text-text-primary">No results found</h3>
          <p className="text-sm text-text-secondary">
            Try a different query or check if the repository is fully indexed
          </p>
        </div>
      )}
    </div>
  );
}
