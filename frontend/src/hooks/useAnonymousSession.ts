/**
 * useAnonymousSession Hook
 * State machine for anonymous repo indexing flow
 * 
 * States: idle → validating → valid/invalid → indexing → ready/error
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { 
  playgroundAPI, 
  ValidationResult, 
  IndexingJob, 
  SessionData 
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

interface UseAnonymousSessionReturn {
  state: PlaygroundState;
  session: SessionData | null;
  validateUrl: (url: string) => Promise<void>;
  startIndexing: () => Promise<void>;
  reset: () => void;
  isLoading: boolean;
}

// ============ Hook Implementation ============

export function useAnonymousSession(): UseAnonymousSessionReturn {
  const [state, setState] = useState<PlaygroundState>({ status: 'idle' });
  const [session, setSession] = useState<SessionData | null>(null);
  
  // Polling refs
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const currentUrlRef = useRef<string>('');

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  // Check for existing session on mount
  useEffect(() => {
    checkExistingSession();
  }, []);

  /**
   * Check if user already has an indexed repo in session
   */
  const checkExistingSession = async () => {
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
          functionsFound: 0, // Not stored in session
          expiresAt: sessionData.indexed_repo.expires_at,
        });
      }
    } catch (error) {
      // No session yet, that's fine
      console.log('No existing session');
    }
  };

  /**
   * Validate a GitHub URL
   */
  const validateUrl = useCallback(async (url: string) => {
    if (!url.trim()) {
      setState({ status: 'idle' });
      return;
    }

    currentUrlRef.current = url;
    setState({ status: 'validating', url });

    try {
      const validation = await playgroundAPI.validateRepo(url);

      // Check if URL changed while we were validating
      if (currentUrlRef.current !== url) return;

      if (validation.can_index) {
        setState({
          status: 'valid',
          url,
          validation,
        });
      } else {
        setState({
          status: 'invalid',
          url,
          error: getErrorMessage(validation.reason),
          reason: validation.reason,
        });
      }
    } catch (error) {
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

      // Start polling for status
      startPolling(job.job_id, url);
    } catch (error) {
      setState({
        status: 'error',
        message: error instanceof Error ? error.message : 'Failed to start indexing',
        canRetry: true,
      });
    }
  }, [state]);

  /**
   * Poll for indexing status
   */
  const startPolling = (jobId: string, url: string) => {
    // Clear any existing polling
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }

    const poll = async () => {
      try {
        const status = await playgroundAPI.getIndexingStatus(jobId);

        if (status.status === 'completed') {
          // Stop polling
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }

          // Refresh session data
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
          // Stop polling
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
        console.error('Polling error:', error);
        // Don't stop polling on transient errors
      }
    };

    // Poll immediately, then every 2 seconds
    poll();
    pollingRef.current = setInterval(poll, 2000);
  };

  /**
   * Reset to idle state
   */
  const reset = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    currentUrlRef.current = '';
    setState({ status: 'idle' });
  }, []);

  // Computed loading state
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
