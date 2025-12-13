# User Tier & Limits System - Design Document

> **Issues**: #93, #94, #95, #96, #97
> **Author**: Devanshu
> **Status**: Implemented
> **Last Updated**: 2025-12-13

---

## 1. Problem Statement

CodeIntel needs a tiered system to:
1. **Protect costs** - Indexing is expensive ($0.02-$50/repo depending on size)
2. **Enable growth** - Freemium model with upgrade path
3. **Prevent abuse** - Rate limit anonymous playground users

**Key Insight**: Searching is nearly free ($0.000001/query). Indexing is the real cost driver.

---

## 2. Tier Definitions

| Tier | Max Repos | Files/Repo | Functions/Repo | Playground/Day |
|------|-----------|------------|----------------|----------------|
| **Free** | 3 | 500 | 2,000 | 50 |
| **Pro** | 20 | 5,000 | 20,000 | Unlimited |
| **Enterprise** | Unlimited | 50,000 | 200,000 | Unlimited |

**Rationale**:
- Free tier: Enough for personal projects, not enterprise codebases
- Playground limit: 50/day is generous (anti-abuse, not business gate)
- File/function limits: Prevent expensive indexing jobs

---

## 3. Current API Endpoints

### 3.1 Authentication (`/api/v1/auth`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/signup` | None | Create account |
| POST | `/login` | None | Get JWT |
| POST | `/refresh` | JWT | Refresh token |
| POST | `/logout` | JWT | Invalidate session |
| GET | `/me` | JWT | Get current user |

### 3.2 Repositories (`/api/v1/repos`)
| Method | Endpoint | Auth | Description | **Limits Check** |
|--------|----------|------|-------------|------------------|
| GET | `/` | JWT | List user repos | - |
| POST | `/` | JWT | Add repo | **#95: Check repo count** |
| POST | `/{id}/index` | JWT | Index repo | **#94: Check file/function count** |

### 3.3 Search (`/api/v1/search`)
| Method | Endpoint | Auth | Description | **Limits Check** |
|--------|----------|------|-------------|------------------|
| POST | `/search` | JWT | Search code | - |
| POST | `/explain` | JWT | Explain code | - |

### 3.4 Playground (`/api/v1/playground`) - **Anonymous**
| Method | Endpoint | Auth | Description | **Limits Check** |
|--------|----------|------|-------------|------------------|
| GET | `/repos` | None | List demo repos | - |
| POST | `/search` | None | Search demo repos | **#93: Rate limit 50/day** |

### 3.5 Analysis (`/api/v1/analysis`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/{id}/dependencies` | JWT | Dependency graph |
| POST | `/{id}/impact` | JWT | Impact analysis |
| GET | `/{id}/insights` | JWT | Repo insights |
| GET | `/{id}/style-analysis` | JWT | Code style |

### 3.6 Users (`/api/v1/users`) - **NEW**
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/usage` | JWT | Get tier, limits, current usage |
| GET | `/limits/check-repo-add` | JWT | Pre-check before adding repo |

---

## 4. Implementation Plan by Issue

### Issue #96: User Tier System (Foundation) ✅ DONE
**Files Created**:
- `backend/services/user_limits.py` - Core service
- `backend/routes/users.py` - API endpoints
- `supabase/migrations/001_user_profiles.sql` - DB schema

**Service Methods**:
```python
class UserLimitsService:
    def get_user_tier(user_id) -> UserTier
    def get_user_limits(user_id) -> TierLimits
    def get_user_repo_count(user_id) -> int
    def check_repo_count(user_id) -> LimitCheckResult
    def check_repo_size(user_id, file_count, func_count) -> LimitCheckResult
    def get_usage_summary(user_id) -> dict
    def invalidate_tier_cache(user_id) -> None  # Call after tier upgrade
```

### Issue #95: Repo Count Limits
**Where**: `POST /api/v1/repos`

**Changes to `routes/repos.py`**:
```python
@router.post("")
def add_repository(request, auth):
    # NEW: Check repo count limit
    result = user_limits.check_repo_count(auth.user_id)
    if not result.allowed:
        raise HTTPException(
            status_code=403,
            detail=result.to_dict()
        )
    # ... existing code
```

**Frontend Integration**:
- Call `GET /users/limits/check-repo-add` before showing Add Repo button
- Show "2/3 repos used" in sidebar
- Show upgrade prompt when limit reached

### Issue #94: Repo Size Limits
**Where**: `POST /api/v1/repos/{id}/index`

**Changes to `routes/repos.py`**:
```python
@router.post("/{repo_id}/index")
def index_repository(repo_id, auth):
    repo = get_repo_or_404(repo_id, auth.user_id)
    
    # Count files and estimate functions BEFORE indexing
    file_count = count_code_files(repo["local_path"])
    estimated_functions = file_count * 25  # Conservative estimate
    
    # NEW: Check size limits
    result = user_limits.check_repo_size(
        auth.user_id, file_count, estimated_functions
    )
    if not result.allowed:
        raise HTTPException(
            status_code=400,
            detail=result.to_dict()
        )
    # ... existing indexing code
```

### Issue #93: Playground Rate Limiting
**Where**: `POST /api/v1/playground/search`

**New File**: `backend/services/playground_rate_limiter.py`
```python
class PlaygroundRateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.daily_limit = 50
    
    def check_and_increment(self, ip: str) -> tuple[bool, dict]:
        """Returns (allowed, headers_dict)"""
        key = f"playground:rate:{ip}"
        
        # Atomic increment
        count = self.redis.incr(key)
        if count == 1:
            self.redis.expire(key, 86400)  # 24h TTL
        
        ttl = self.redis.ttl(key)
        reset_time = int(time.time()) + ttl
        
        headers = {
            "X-RateLimit-Limit": str(self.daily_limit),
            "X-RateLimit-Remaining": str(max(0, self.daily_limit - count)),
            "X-RateLimit-Reset": str(reset_time)
        }
        
        if count > self.daily_limit:
            headers["Retry-After"] = str(ttl)
            return False, headers
        
        return True, headers
```

**Changes to `routes/playground.py`**:
```python
from fastapi import Request, Response

@router.post("/search")
def playground_search(request: Request, response: Response, body: SearchRequest):
    # Get client IP
    ip = request.client.host
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    
    # Check rate limit
    allowed, headers = playground_rate_limiter.check_and_increment(ip)
    
    # Always add headers
    for key, value in headers.items():
        response.headers[key] = value
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "RATE_LIMIT_EXCEEDED",
                "message": "Daily search limit reached. Sign up for unlimited searches!",
                "limit": 50,
                "reset": headers["X-RateLimit-Reset"]
            }
        )
    
    # ... existing search code
```

### Issue #97: Progressive Signup CTAs
**Where**: Frontend only

**Implementation**:
```typescript
// hooks/usePlaygroundUsage.ts
const usePlaygroundUsage = () => {
  const [searchCount, setSearchCount] = useState(0);
  
  // Read from response headers after each search
  const trackSearch = (response: Response) => {
    const remaining = response.headers.get('X-RateLimit-Remaining');
    const limit = response.headers.get('X-RateLimit-Limit');
    if (remaining && limit) {
      setSearchCount(parseInt(limit) - parseInt(remaining));
    }
  };
  
  return { searchCount, trackSearch };
};

// Show CTAs at thresholds
// 10 searches: Subtle "Want to search YOUR codebase?"
// 25 searches: More prominent with feature list
// 40 searches: Final "You clearly love this"
```

---

## 5. Error Response Format

All limit-related errors use `LimitCheckResult.to_dict()`:

```json
{
  "detail": {
    "allowed": false,
    "current": 3,
    "limit": 3,
    "limit_display": "3",
    "message": "Repository limit reached (3/3). Upgrade to add more repositories.",
    "tier": "free",
    "error_code": "REPO_LIMIT_REACHED"
  }
}
```

**Error Codes**:
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `REPO_LIMIT_REACHED` | 403 | Max repos for tier |
| `REPO_TOO_LARGE` | 400 | File/function count exceeds tier |
| `RATE_LIMIT_EXCEEDED` | 429 | Playground daily limit |
| `INVALID_USER` | 400 | Invalid or missing user_id |
| `SYSTEM_ERROR` | 500 | Database/system failure |

---

## 6. Database Schema

### user_profiles (NEW)
```sql
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    tier TEXT DEFAULT 'free',  -- 'free', 'pro', 'enterprise'
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

**Security Notes:**
- RLS enabled with SELECT/INSERT for authenticated users
- NO UPDATE policy for users (prevents self-upgrade)
- Tier updates only via service role key (payment webhooks)

### repositories (existing, no changes needed)
Already has `user_id` column for ownership.

---

## 7. Fail-Safe Behavior

| Scenario | Behavior | Reason |
|----------|----------|--------|
| DB down during `check_repo_count` | **DENY** (fail-closed) | Prevent unlimited repos |
| DB down during `get_usage_summary` | Return defaults | Read-only, safe to fail-open |
| Redis cache miss | Query DB | Graceful degradation |
| Redis down | Continue without cache | Non-critical |
| Invalid user_id | Return FREE limits | Safe default |

---

## 8. Redis Keys

| Key Pattern | TTL | Description |
|-------------|-----|-------------|
| `playground:rate:{ip}` | 24h | Playground search count |
| `user:tier:{user_id}` | 5min | Cached user tier |

---

## 9. Frontend Integration Points

### Dashboard
- Show usage bar: "2/3 repositories"
- Show tier badge: "Free Tier"
- Upgrade CTA when near limits

### Add Repository Flow
1. Call `GET /users/limits/check-repo-add`
2. If `allowed: false`, show upgrade modal
3. If `allowed: true`, proceed with add

### Playground
1. Read rate limit headers from search responses
2. Show remaining searches: "47/50 searches today"
3. Show progressive CTAs at thresholds
4. On 429, show signup modal

---

## 10. Migration Path

### Existing Users
All existing users default to `free` tier. Migration auto-creates profile on first API call.

### Existing Repos
No changes needed. Limit checks only apply to NEW repos.

---

## 11. Implementation Order

| Phase | Issue | Priority | Depends On |
|-------|-------|----------|------------|
| 1 | #96 User tier system | P0 | - | ✅ DONE |
| 2 | #94 Repo size limits | P0 | #96 |
| 2 | #95 Repo count limits | P0 | #96 |
| 3 | #93 Playground rate limit | P1 | Redis |
| 4 | #97 Progressive CTAs | P2 | #93 |

---

## 12. Open Questions

1. **Upgrade Flow**: Stripe integration? Manual for now?
2. **Existing Large Repos**: Grandfather them or enforce limits?
3. **Team/Org Support**: Future consideration for enterprise?
4. **API Key Users**: Same limits as JWT users?

---

## 13. Files to Create/Modify

### Create
- [x] `backend/services/user_limits.py`
- [x] `backend/routes/users.py`
- [x] `supabase/migrations/001_user_profiles.sql`
- [ ] `backend/services/playground_rate_limiter.py`
- [ ] `frontend/src/hooks/usePlaygroundUsage.ts`
- [ ] `frontend/src/components/PlaygroundCTA.tsx`
- [ ] `frontend/src/components/UsageBar.tsx`

### Modify
- [x] `backend/dependencies.py`
- [x] `backend/main.py`
- [ ] `backend/routes/repos.py` - Add limit checks
- [ ] `backend/routes/playground.py` - Add rate limiting
- [ ] `frontend/src/pages/Dashboard.tsx` - Show usage
- [ ] `frontend/src/pages/LandingPage.tsx` - Show CTAs
