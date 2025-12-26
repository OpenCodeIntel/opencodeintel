/**
 * useAnonymousSession Hook
 * 
 * State machine for anonymous repo indexing flow.
 * Manages validation, indexing progress, and session state.
 * 
 * @example
 * ```tsx
 * const { state, validateUrl, startIndexing, reset } = useAnonymousSession();
 * 
 * // State machine: idle → validating → valid/invalid → indexing → ready/error
 * ```
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { 
  playgroundAPI, 
  type ValidationResult, 
  type SessionData 
} from '../services/playground-api';

// ============ State Types ============

interface IdleState {
  status: 'idle';
}

interface ValidatingState {
  status: 'validating';
  url: string;
}

interface ValidState {
  status: 'valid';
  url: string;
  validation: ValidationResult;
}

interface InvalidState {
  status: 'invalid';
  url: string;
  error: string;
  reason?: 'private' | 'too_large' | 'invalid_url' | 'rate_limited';
}

interface IndexingState {
  status: 'indexing';
  url: string;
  jobId: string;
  progress: {
    percent: number;
    filesProcessed: number;
    filesTotal: number;
    currentFile?: string;
    functionsFound: number;
  };
}

interface ReadyState {
  status: 'ready';
  repoId: string;
  repoName: string;
  owner: string;
  fileCount: number;
  functionsFound: number;
  expiresAt: string;
}

interface ErrorState {
  status: 'error';
  message: string;
  canRetry: boolean;
}

export type PlaygroundState =
  | IdleState
  | ValidatingState
  | ValidState
  | InvalidState
  | IndexingState
  | ReadyState
  | ErrorState;

// ============ Hook Return Type ============

export interface UseAnonymousSessionReturn {
  state: PlaygroundState;
  session: SessionData | null;
  validateUrl: (url: string) => Promise<void>;
  startIndexing: () => Promise<void>;
  reset: () => void;
  isLoading: boolean;
}

// ============ Constants ============

const POLLING_INTERVAL_MS = 2000;

// ============ Hook Implementation ============

export function useAnonymousSession(): UseAnonymousSessionReturn {
  const [state, setState] = useState<PlaygroundState>({ status: 'idle' });
  const [session, setSession] = useState<SessionData | null>(null);
  
  // Refs for cleanup and race condition handling
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const currentUrlRef = useRef<string>('');
  const abortControllerRef = useRef<AbortController | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  /**
   * Check if user already has an indexed repo in session
   */
  const checkExistingSession = useCallback(async () => {
    try {
      const sessionData = await playgroundAPI.getSession();
      setSession(sessionData);
      
      if (sessionData.indexed_repo) {
        setState({
          status: 'ready',
          repoId: sessionData.indexed_repo.repo_id,
          repoName: sessionData.indexed_repo.name,
          owner: sessionData.indexed_repo.owner || '',
          fileCount: sessionData.indexed_repo.file_count,
          functionsFound: 0,
          expiresAt: sessionData.indexed_repo.expires_at,
        });
      }
    } catch {
      // No session yet - this is expected for new users
    }
  }, []);

  // Check for existing session on mount
  useEffect(() => {
    checkExistingSession();
  }, [checkExistingSession]);

  /**
   * Poll for indexing job status
   */
  const startPolling = useCallback((jobId: string, url: string) => {
    // Clear any existing polling
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }

    const poll = async () => {
      try {
        const status = await playgroundAPI.getIndexingStatus(jobId);

        if (status.status === 'completed') {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }

          const sessionData = await playgroundAPI.getSession();
          setSession(sessionData);

          setState({
            status: 'ready',
            repoId: status.repo_id!,
            repoName: status.repository?.name || '',
            owner: status.repository?.owner || '',
            fileCount: status.stats?.files_indexed || 0,
            functionsFound: status.stats?.functions_found || 0,
            expiresAt: sessionData.indexed_repo?.expires_at || '',
          });
        } else if (status.status === 'failed') {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }

          setState({
            status: 'error',
            message: status.error || 'Indexing failed',
            canRetry: true,
          });
        } else {
          // Update progress
          setState({
            status: 'indexing',
            url,
            jobId,
            progress: {
              percent: status.progress?.percent_complete || 0,
              filesProcessed: status.progress?.files_processed || 0,
              filesTotal: status.progress?.files_total || 0,
              currentFile: status.progress?.current_file,
              functionsFound: status.progress?.functions_found || 0,
            },
          });
        }
      } catch (error) {
        // Log but don't stop polling on transient errors
        console.error('Polling error:', error);
      }
    };

    // Poll immediately, then at interval
    poll();
    pollingRef.current = setInterval(poll, POLLING_INTERVAL_MS);
  }, []);

  /**
   * Validate a GitHub URL
   */
  const validateUrl = useCallback(async (url: string) => {
    if (!url.trim()) {
      setState({ status: 'idle' });
      return;
    }

    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    currentUrlRef.current = url;
    setState({ status: 'validating', url });

    try {
      const validation = await playgroundAPI.validateRepo(url);

      // Ignore if URL changed during validation
      if (currentUrlRef.current !== url) return;

      if (validation.can_index) {
        setState({ status: 'valid', url, validation });
      } else {
        setState({
          status: 'invalid',
          url,
          error: getErrorMessage(validation.reason),
          reason: validation.reason,
        });
      }
    } catch (error) {
      // Ignore abort errors
      if (error instanceof Error && error.name === 'AbortError') return;
      if (currentUrlRef.current !== url) return;
      
      setState({
        status: 'invalid',
        url,
        error: error instanceof Error ? error.message : 'Validation failed',
      });
    }
  }, []);

  /**
   * Start indexing the validated repo
   */
  const startIndexing = useCallback(async () => {
    if (state.status !== 'valid') {
      console.error('Cannot start indexing: not in valid state');
      return;
    }

    const { url, validation } = state;

    try {
      const job = await playgroundAPI.startIndexing(url);

      setState({
        status: 'indexing',
        url,
        jobId: job.job_id,
        progress: {
          percent: 0,
          filesProcessed: 0,
          filesTotal: validation.file_count,
          functionsFound: 0,
        },
      });

      startPolling(job.job_id, url);
    } catch (error) {
      setState({
        status: 'error',
        message: error instanceof Error ? error.message : 'Failed to start indexing',
        canRetry: true,
      });
    }
  }, [state, startPolling]);

  /**
   * Reset to idle state
   */
  const reset = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    currentUrlRef.current = '';
    setState({ status: 'idle' });
  }, []);

  const isLoading = state.status === 'validating' || state.status === 'indexing';

  return {
    state,
    session,
    validateUrl,
    startIndexing,
    reset,
    isLoading,
  };
}

// ============ Helpers ============

function getErrorMessage(reason?: string): string {
  switch (reason) {
    case 'private':
      return 'This repository is private. Sign up to index private repos.';
    case 'too_large':
      return 'This repository is too large for anonymous indexing. Sign up for full access.';
    case 'invalid_url':
      return 'Please enter a valid GitHub repository URL.';
    case 'rate_limited':
      return 'Rate limit reached. Please try again later.';
    default:
      return 'Unable to validate this repository.';
  }
}
