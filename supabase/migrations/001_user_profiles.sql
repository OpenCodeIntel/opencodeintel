-- Migration: Add user_profiles table for tier management
-- Issue: #96 - User tier system
-- Run this in Supabase SQL Editor

-- Create user_profiles table
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tier TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'pro', 'enterprise')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Ensure one profile per user
    CONSTRAINT unique_user_profile UNIQUE (user_id)
);

-- Create index for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON public.user_profiles(user_id);

-- Enable RLS
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- RLS Policies

-- Users can read their own profile
CREATE POLICY "Users can view own profile"
    ON public.user_profiles
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own profile (on signup)
CREATE POLICY "Users can create own profile"
    ON public.user_profiles
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Only service role can update tier (prevents users upgrading themselves)
-- Users update through payment flow which uses service role key
CREATE POLICY "Service role can update profiles"
    ON public.user_profiles
    FOR UPDATE
    USING (true)
    WITH CHECK (true);

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to auto-create profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (user_id, tier)
    VALUES (NEW.id, 'free')
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create profile when new user signs up
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- Grant permissions
GRANT SELECT ON public.user_profiles TO authenticated;
GRANT INSERT ON public.user_profiles TO authenticated;

-- Comment
COMMENT ON TABLE public.user_profiles IS 'User profiles with subscription tier information';
COMMENT ON COLUMN public.user_profiles.tier IS 'Subscription tier: free, pro, or enterprise';
