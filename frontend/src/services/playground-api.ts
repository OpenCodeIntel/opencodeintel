/**
 * Playground API Service
 * Handles all anonymous indexing API calls
 * 
 * Endpoints:
 * - POST /playground/validate-repo  (BLOCKED by #134 - using mock)
 * - POST /playground/index
 * - GET  /playground/index/{job_id}
 * - GET  /playground/session
 * - POST /playground/search
 */

import { API_URL } from '../config/api';

// ============ Types ============

export interface ValidationResult {
  can_index: boolean;
  reason?: 'private' | 'too_large' | 'invalid_url' | 'rate_limited';
  repo_name: string;
  owner: string;
  file_count: number;
  stars: number;
  language: string;
  default_branch: string;
  estimated_time_seconds: number;
}

export interface IndexingJob {
  job_id: string;
  status: 'queued' | 'cloning' | 'processing' | 'completed' | 'failed';
  repo_id?: string;
  repository?: {
    owner: string;
    name: string;
    branch: string;
    github_url: string;
  };
  progress?: {
    files_processed: number;
    files_total: number;
    percent_complete: number;
    current_file?: string;
    functions_found: number;
  };
  stats?: {
    files_indexed: number;
    functions_found: number;
    time_taken_seconds: number;
  };
  error?: string;
  estimated_time_seconds?: number;
  message?: string;
}

export interface SessionData {
  session_id: string;
  indexed_repo: {
    repo_id: string;
    github_url: string;
    name: string;
    owner?: string;
    file_count: number;
    indexed_at: string;
    expires_at: string;
  } | null;
  searches: {
    used: number;
    limit: number;
    remaining: number;
  };
}

export interface SearchResult {
  name: string;
  type: string;
  file_path: string;
  code: string;
  language: string;
  line_start: number;
  line_end: number;
  score: number;
}

export interface SearchResponse {
  results: SearchResult[];
  search_time_ms: number;
  remaining_searches: number;
  limit: number;
}

// ============ API Client ============

class PlaygroundAPI {
  private baseUrl: string;

  constructor() {
    this.baseUrl = `${API_URL}/playground`;
  }

  /**
   * Validate a GitHub repo URL before indexing
   * NOTE: Currently mocked due to Bug #134 (CacheService missing get/set)
   */
  async validateRepo(githubUrl: string): Promise<ValidationResult> {
    // TODO: Remove mock when #134 is fixed
    const USE_MOCK = true; // Flip to false when backend is ready
    
    if (USE_MOCK) {
      return this.mockValidateRepo(githubUrl);
    }

    const response = await fetch(`${this.baseUrl}/validate-repo`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ github_url: githubUrl }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail?.message || 'Validation failed');
    }

    return response.json();
  }

  /**
   * Mock validation until Bug #134 is fixed
   */
  private async mockValidateRepo(githubUrl: string): Promise<ValidationResult> {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 800));

    // Parse URL to extract owner/repo
    const match = githubUrl.match(/github\.com\/([^/]+)\/([^/]+)/);
    if (!match) {
      return {
        can_index: false,
        reason: 'invalid_url',
        repo_name: '',
        owner: '',
        file_count: 0,
        stars: 0,
        language: '',
        default_branch: '',
        estimated_time_seconds: 0,
      };
    }

    const [, owner, repo] = match;
    const repoName = repo.replace(/\.git$/, '');

    // Mock successful validation
    return {
      can_index: true,
      repo_name: repoName,
      owner,
      file_count: Math.floor(Math.random() * 300) + 50,
      stars: Math.floor(Math.random() * 50000),
      language: 'Python',
      default_branch: 'main',
      estimated_time_seconds: Math.floor(Math.random() * 30) + 10,
    };
  }

  /**
   * Start indexing a repository
   */
  async startIndexing(githubUrl: string): Promise<IndexingJob> {
    const response = await fetch(`${this.baseUrl}/index`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ github_url: githubUrl }),
    });

    if (!response.ok) {
      const error = await response.json();
      if (response.status === 409) {
        throw new Error(error.detail?.message || 'Already have an indexed repo');
      }
      throw new Error(error.detail?.message || 'Failed to start indexing');
    }

    return response.json();
  }

  /**
   * Poll indexing job status
   */
  async getIndexingStatus(jobId: string): Promise<IndexingJob> {
    const response = await fetch(`${this.baseUrl}/index/${jobId}`, {
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail?.message || 'Failed to get status');
    }

    return response.json();
  }

  /**
   * Get current session data
   */
  async getSession(): Promise<SessionData> {
    const response = await fetch(`${this.baseUrl}/session`, {
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail?.message || 'Failed to get session');
    }

    return response.json();
  }

  /**
   * Search in indexed repo
   */
  async search(query: string, repoId: string, maxResults = 10): Promise<SearchResponse> {
    const response = await fetch(`${this.baseUrl}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        query,
        repo_id: repoId,
        max_results: maxResults,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      if (response.status === 429) {
        throw new Error('Daily search limit reached');
      }
      throw new Error(error.detail?.message || 'Search failed');
    }

    return response.json();
  }
}

// Export singleton instance
export const playgroundAPI = new PlaygroundAPI();
