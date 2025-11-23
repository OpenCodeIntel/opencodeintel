-- CodeIntel Database Schema
-- Run this in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Repositories table
CREATE TABLE IF NOT EXISTS repositories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    git_url TEXT NOT NULL,
    branch TEXT DEFAULT 'main',
    local_path TEXT,
    status TEXT DEFAULT 'cloned', -- cloned, indexing, indexed, error
    file_count INTEGER DEFAULT 0,
    function_count INTEGER DEFAULT 0,
    last_indexed_commit TEXT,
    last_indexed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- File dependencies table (for dependency graph)
CREATE TABLE IF NOT EXISTS file_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repo_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    depends_on TEXT[], -- Array of file paths this file depends on
    depended_by TEXT[], -- Array of file paths that depend on this
    import_count INTEGER DEFAULT 0,
    dependent_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(repo_id, file_path)
);

-- Code style analysis results
CREATE TABLE IF NOT EXISTS code_style_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repo_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    language TEXT NOT NULL,
    naming_convention JSONB, -- {functions: 'snake_case', classes: 'PascalCase', etc}
    async_usage JSONB, -- {total_functions: X, async_functions: Y, percentage: Z}
    type_hints JSONB, -- {total_functions: X, typed_functions: Y, percentage: Z}
    common_imports JSONB[], -- Array of import patterns
    patterns JSONB, -- Other coding patterns
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(repo_id, language)
);

-- Repository insights (cached high-level metrics)
CREATE TABLE IF NOT EXISTS repository_insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repo_id UUID REFERENCES repositories(id) ON DELETE CASCADE UNIQUE,
    total_files INTEGER DEFAULT 0,
    total_dependencies INTEGER DEFAULT 0,
    avg_dependencies_per_file FLOAT DEFAULT 0,
    max_dependencies INTEGER DEFAULT 0,
    critical_files TEXT[], -- Files with high dependency count
    architecture_patterns JSONB, -- Detected patterns
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexing jobs (track indexing progress)
CREATE TABLE IF NOT EXISTS indexing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repo_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending', -- pending, running, completed, failed
    files_processed INTEGER DEFAULT 0,
    functions_indexed INTEGER DEFAULT 0,
    total_files INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_repos_status ON repositories(status);
CREATE INDEX IF NOT EXISTS idx_repos_updated_at ON repositories(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_file_deps_repo ON file_dependencies(repo_id);
CREATE INDEX IF NOT EXISTS idx_file_deps_path ON file_dependencies(file_path);
CREATE INDEX IF NOT EXISTS idx_style_repo_lang ON code_style_analysis(repo_id, language);
CREATE INDEX IF NOT EXISTS idx_indexing_jobs_repo ON indexing_jobs(repo_id);
CREATE INDEX IF NOT EXISTS idx_indexing_jobs_status ON indexing_jobs(status);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at (drop first if exists)
DROP TRIGGER IF EXISTS update_repositories_updated_at ON repositories;
CREATE TRIGGER update_repositories_updated_at BEFORE UPDATE ON repositories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_file_dependencies_updated_at ON file_dependencies;
CREATE TRIGGER update_file_dependencies_updated_at BEFORE UPDATE ON file_dependencies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_code_style_analysis_updated_at ON code_style_analysis;
CREATE TRIGGER update_code_style_analysis_updated_at BEFORE UPDATE ON code_style_analysis
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_repository_insights_updated_at ON repository_insights;
CREATE TRIGGER update_repository_insights_updated_at BEFORE UPDATE ON repository_insights
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
