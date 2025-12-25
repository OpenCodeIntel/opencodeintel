# Handoff: Anonymous Indexing (#114)

## TL;DR
Let users index their own GitHub repos without signup. 5 backend endpoints needed.

## GitHub Issues (Full Specs)
- **#124** - Validate GitHub URL
- **#125** - Start anonymous indexing  
- **#126** - Get indexing status
- **#127** - Extend session management
- **#128** - Update search for user repos

**Read these first.** Each has request/response schemas, implementation notes, acceptance criteria.

## Order of Work
```
#127 + #124 (parallel) → #125 → #126 → #128
```

## Key Files to Understand

| File | What It Does |
|------|--------------|
| `backend/config/api.py` | API versioning (`/api/v1/*`) |
| `backend/routes/playground.py` | Existing playground endpoints |
| `backend/services/playground_limiter.py` | Session + rate limiting |
| `backend/services/repo_validator.py` | File counting, extensions |
| `backend/dependencies.py` | Indexer, cache, redis_client |

## Constraints (Anonymous Users)
- 200 files max
- 1 repo per session
- 50 searches per session
- 24hr TTL

## Workflow
See `CONTRIBUTING.md` for full guide.

**Quick version:**
```bash
# Create branch
git checkout -b feat/124-validate-repo

# Make changes, test
pytest tests/ -v

# Commit
git add .
git commit -m "feat(playground): add validate-repo endpoint"

# Push to YOUR fork
git push origin feat/124-validate-repo

# Create PR on OpenCodeIntel/opencodeintel
# Reference issue: "Closes #124"
```

## Questions?
- Check GitHub issues first
- Ping Devanshu for blockers
