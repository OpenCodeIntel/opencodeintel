# Legacy Code Archive

This folder contains old implementations that were replaced during development.

## Files:

### indexer_old.py
- Original indexer implementation before batch processing optimization
- Replaced by `indexer_optimized.py` which achieves 100x performance improvement
- Kept for reference on the evolution from individual API calls to batch processing

### repo_manager_old.py  
- Original repository manager with in-memory storage
- Replaced by current `repo_manager.py` with Supabase persistence
- Shows the migration from ephemeral to production-grade storage

### IndexingProgress.tsx
- Original indexing progress component using WebSocket
- Replaced by integrated progress in `RepoOverview.tsx` using shadcn Progress component
- Kept for reference on the WebSocket implementation approach

**Note:** These files are not imported or used anywhere in the active codebase.
They're preserved for historical reference and to show the development evolution.
