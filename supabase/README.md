# Supabase Migrations

This folder contains SQL migrations for the Supabase database.

## Running Migrations

### Option 1: Supabase Dashboard (Recommended)

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Open the migration file and copy contents
4. Run the SQL

### Option 2: Supabase CLI

```bash
# Install Supabase CLI
npm install -g supabase

# Link to your project
supabase link --project-ref YOUR_PROJECT_REF

# Run migrations
supabase db push
```

## Migration Files

| File | Description | Issue |
|------|-------------|-------|
| `001_user_profiles.sql` | User profiles with tier (free/pro/enterprise) | #96 |

## Schema Overview

### user_profiles
Stores user subscription tier information.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to auth.users |
| tier | TEXT | 'free', 'pro', or 'enterprise' |
| created_at | TIMESTAMPTZ | Profile creation time |
| updated_at | TIMESTAMPTZ | Last update time |

**Features:**
- Auto-creates profile on user signup (trigger)
- RLS enabled - users can only read their own profile
- Tier updates only via service role (prevents self-upgrade)
