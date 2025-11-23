export interface Repository {
  id: string
  name: string
  git_url: string
  branch: string
  status: string
  file_count: number
}

export interface SearchResult {
  code: string
  file_path: string
  name: string
  type: string
  language: string
  score: number
  line_start: number
  line_end: number
}
