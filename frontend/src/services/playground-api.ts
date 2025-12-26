/**
 * Playground API Service
 * 
 * Handles all anonymous indexing API calls.
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

// ============ Error Classes ============

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

// ============ Helpers ============

async function parseErrorResponse(response: Response): Promise<string> {
  try {
    const data = await response.json();
    return data.detail?.message || data.detail || data.message || 'Request failed';
  } catch {
    return `Request failed with status ${response.status}`;
  }
}

// ============ API Client ============

class PlaygroundAPI {
  private baseUrl: string;

  constructor() {
    this.baseUrl = `${API_URL}/playground`;
  }

  /**
   * Validate a GitHub repo URL before indexing.
   * 
   * @param githubUrl - Full GitHub URL (e.g., https://github.com/owner/repo)
   * @returns Validation result with repo metadata
   * @throws APIError on failure
   * 
   * NOTE: Currently mocked due to Bug #134 (CacheService missing get/set)
   */
  async validateRepo(githubUrl: string): Promise<ValidationResult> {
    // TODO: Remove mock when #134 is fixed
    const USE_MOCK = true;
    
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
      const message = await parseErrorResponse(response);
      throw new APIError(message, response.status);
    }

    return response.json();
  }

  /**
   * Mock validation for development until Bug #134 is fixed.
   * Simulates realistic validation responses.
   */
  private async mockValidateRepo(githubUrl: string): Promise<ValidationResult> {
    // Simulate network latency
    await new Promise(resolve => setTimeout(resolve, 600 + Math.random() * 400));

    // Parse URL
    const match = githubUrl.match(/github\.com\/([^/]+)\/([^/\s?#]+)/);
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

    // Detect language from common repo names
    const language = this.detectLanguage(repoName, owner);
    const fileCount = 50 + Math.floor(Math.random() * 250);

    return {
      can_index: true,
      repo_name: repoName,
      owner,
      file_count: fileCount,
      stars: Math.floor(Math.random() * 50000),
      language,
      default_branch: 'main',
      estimated_time_seconds: Math.ceil(fileCount / 10),
    };
  }

  /**
   * Simple language detection based on repo/owner name patterns.
   */
  private detectLanguage(repo: string, owner: string): string {
    const name = `${owner}/${repo}`.toLowerCase();
    
    if (name.includes('flask') || name.includes('django') || name.includes('fastapi')) {
      return 'Python';
    }
    if (name.includes('express') || name.includes('next') || name.includes('react')) {
      return 'TypeScript';
    }
    if (name.includes('rails') || name.includes('ruby')) {
      return 'Ruby';
    }
    if (name.includes('spring') || name.includes('java')) {
      return 'Java';
    }
    if (name.includes('gin') || name.includes('echo')) {
      return 'Go';
    }
    
    // Random fallback
    const languages = ['Python', 'TypeScript', 'JavaScript', 'Go', 'Rust'];
    return languages[Math.floor(Math.random() * languages.length)];
  }

  /**
   * Start indexing a repository.
   * 
   * @param githubUrl - Full GitHub URL
   * @returns Job info with job_id for polling
   * @throws APIError on failure (409 if already indexed)
   */
  async startIndexing(githubUrl: string): Promise<IndexingJob> {
    const response = await fetch(`${this.baseUrl}/index`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ github_url: githubUrl }),
    });

    if (!response.ok) {
      const message = await parseErrorResponse(response);
      throw new APIError(message, response.status, response.status === 409 ? 'ALREADY_INDEXED' : undefined);
    }

    return response.json();
  }

  /**
   * Poll indexing job status.
   * 
   * @param jobId - Job ID from startIndexing
   * @returns Current job status with progress
   */
  async getIndexingStatus(jobId: string): Promise<IndexingJob> {
    const response = await fetch(`${this.baseUrl}/index/${jobId}`, {
      credentials: 'include',
    });

    if (!response.ok) {
      const message = await parseErrorResponse(response);
      throw new APIError(message, response.status);
    }

    return response.json();
  }

  /**
   * Get current session data including indexed repo and search limits.
   */
  async getSession(): Promise<SessionData> {
    const response = await fetch(`${this.baseUrl}/session`, {
      credentials: 'include',
    });

    if (!response.ok) {
      const message = await parseErrorResponse(response);
      throw new APIError(message, response.status);
    }

    return response.json();
  }

  /**
   * Search in indexed repository.
   * 
   * @param query - Natural language search query
   * @param repoId - Repository ID from session
   * @param maxResults - Maximum results to return (default: 10)
   * @throws APIError on failure (429 if rate limited)
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
      const message = await parseErrorResponse(response);
      throw new APIError(
        response.status === 429 ? 'Daily search limit reached' : message,
        response.status,
        response.status === 429 ? 'RATE_LIMITED' : undefined
      );
    }

    return response.json();
  }
}

// Export singleton instance
export const playgroundAPI = new PlaygroundAPI();
