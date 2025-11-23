-- API Keys Table
-- Stores API keys with usage tracking and rate limits

CREATE TABLE IF NOT EXISTS api_keys (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    key_hash TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free', -- 'free', 'pro', 'enterprise'
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    request_count INTEGER DEFAULT 0,
    CONSTRAINT valid_tier CHECK (tier IN ('free', 'pro', 'enterprise'))
);

-- Create index for fast key lookups
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash) WHERE active = true;
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id) WHERE active = true;

-- Add user_id column to repositories for multi-tenancy
ALTER TABLE repositories 
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS api_key_hash TEXT;

-- Create index for user-specific queries
CREATE INDEX IF NOT EXISTS idx_repositories_user ON repositories(user_id);

-- Enable Row Level Security (RLS) on repositories
ALTER TABLE repositories ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own repositories
CREATE POLICY "Users can view own repositories" ON repositories
    FOR SELECT
    USING (user_id = auth.uid() OR user_id IS NULL);

CREATE POLICY "Users can insert own repositories" ON repositories
    FOR INSERT
    WITH CHECK (user_id = auth.uid() OR user_id IS NULL);

CREATE POLICY "Users can update own repositories" ON repositories
    FOR UPDATE
    USING (user_id = auth.uid() OR user_id IS NULL);

CREATE POLICY "Users can delete own repositories" ON repositories
    FOR DELETE
    USING (user_id = auth.uid() OR user_id IS NULL);

-- Enable RLS on related tables
ALTER TABLE file_dependencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE code_style_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE repository_insights ENABLE ROW LEVEL SECURITY;

-- Policies for file_dependencies (inherit from repositories)
CREATE POLICY "Users can view own file dependencies" ON file_dependencies
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM repositories
            WHERE repositories.id = file_dependencies.repo_id
            AND (repositories.user_id = auth.uid() OR repositories.user_id IS NULL)
        )
    );

CREATE POLICY "Users can insert own file dependencies" ON file_dependencies
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM repositories
            WHERE repositories.id = file_dependencies.repo_id
            AND (repositories.user_id = auth.uid() OR repositories.user_id IS NULL)
        )
    );

-- Similar policies for other tables
CREATE POLICY "Users can view own code style" ON code_style_analysis
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM repositories
            WHERE repositories.id = code_style_analysis.repo_id
            AND (repositories.user_id = auth.uid() OR repositories.user_id IS NULL)
        )
    );

CREATE POLICY "Users can view own insights" ON repository_insights
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM repositories
            WHERE repositories.id = repository_insights.repo_id
            AND (repositories.user_id = auth.uid() OR repositories.user_id IS NULL)
        )
    );

-- Function to clean up old rate limit data (run daily)
CREATE OR REPLACE FUNCTION cleanup_old_api_keys()
RETURNS void AS $$
BEGIN
    -- Delete API keys inactive for 90+ days
    DELETE FROM api_keys
    WHERE active = false
    AND created_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;
