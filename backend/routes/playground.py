"""
Playground routes - no auth required, rate limited via Redis.

Rate limiting strategy (see #93):
- Session token (httpOnly cookie): 50 searches/day per device
- IP fallback: 100 searches/day for shared networks
- Global circuit breaker: 10k searches/hour (cost protection)
"""
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
import time

from dependencies import indexer, cache, repo_manager, redis_client
from services.input_validator import InputValidator
from services.observability import logger
from services.playground_limiter import PlaygroundLimiter, get_playground_limiter

router = APIRouter(prefix="/playground", tags=["Playground"])

# Demo repo mapping (populated on startup)
DEMO_REPO_IDS = {}

# Session cookie config
SESSION_COOKIE_NAME = "pg_session"
SESSION_COOKIE_MAX_AGE = 86400  # 24 hours
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"


class PlaygroundSearchRequest(BaseModel):
    query: str
    demo_repo: str = "flask"
    max_results: int = 10


async def load_demo_repos():
    """Load pre-indexed demo repos. Called from main.py on startup."""
    # Note: We mutate DEMO_REPO_IDS dict, no need for 'global' statement
    try:
        repos = repo_manager.list_repos()
        for repo in repos:
            name_lower = repo.get("name", "").lower()
            if "flask" in name_lower:
                DEMO_REPO_IDS["flask"] = repo["id"]
            elif "fastapi" in name_lower:
                DEMO_REPO_IDS["fastapi"] = repo["id"]
            elif "express" in name_lower:
                DEMO_REPO_IDS["express"] = repo["id"]
            elif "react" in name_lower:
                DEMO_REPO_IDS["react"] = repo["id"]
        logger.info("Loaded demo repos", repos=list(DEMO_REPO_IDS.keys()))
    except Exception as e:
        logger.warning("Could not load demo repos", error=str(e))


def _get_client_ip(req: Request) -> str:
    """Extract client IP from request."""
    client_ip = req.client.host if req.client else "unknown"
    forwarded = req.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    return client_ip


def _get_session_token(req: Request) -> Optional[str]:
    """Get session token from cookie."""
    return req.cookies.get(SESSION_COOKIE_NAME)


def _set_session_cookie(response: Response, token: str):
    """Set httpOnly session cookie."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,           # Can't be accessed by JavaScript
        samesite="lax",          # CSRF protection
        secure=IS_PRODUCTION,    # HTTPS only in production
    )


def _get_limiter() -> PlaygroundLimiter:
    """Get the playground limiter instance."""
    return get_playground_limiter(redis_client)


@router.get("/limits")
async def get_playground_limits(req: Request):
    """
    Get current rate limit status for this user.

    Frontend should call this on page load to show accurate remaining count.
    """
    session_token = _get_session_token(req)
    client_ip = _get_client_ip(req)

    limiter = _get_limiter()
    result = limiter.check_limit(session_token, client_ip)

    return {
        "remaining": result.remaining,
        "limit": result.limit,
        "resets_at": result.resets_at.isoformat(),
        "tier": "anonymous",
    }


@router.get("/session")
async def get_session_info(req: Request, response: Response):
    """
    Get current session state including indexed repo info.

    Returns complete session data for frontend state management.
    Creates a new session if none exists.

    Response schema (see issue #127):
    {
        "session_id": "pg_abc123...",
        "created_at": "2025-12-24T10:00:00Z",
        "expires_at": "2025-12-25T10:00:00Z",
        "indexed_repo": {
            "repo_id": "repo_abc123",
            "github_url": "https://github.com/user/repo",
            "name": "repo",
            "indexed_at": "2025-12-24T10:05:00Z",
            "expires_at": "2025-12-25T10:05:00Z",
            "file_count": 198
        },
        "searches": {
            "used": 12,
            "limit": 50,
            "remaining": 38
        }
    }
    """
    session_token = _get_session_token(req)
    limiter = _get_limiter()

    # Check if Redis is available
    if not redis_client:
        logger.error("Redis unavailable for session endpoint")
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Service temporarily unavailable",
                "retry_after": 30,
            }
        )

    # Get existing session data
    session_data = limiter.get_session_data(session_token)

    # If no session exists, create one
    if session_data.session_id is None:
        new_token = limiter._generate_session_token()

        if limiter.create_session(new_token):
            _set_session_cookie(response, new_token)
            session_data = limiter.get_session_data(new_token)
            logger.info("Created new session via /session endpoint",
                        session_token=new_token[:8])
        else:
            # Failed to create session (Redis issue)
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Failed to create session",
                    "retry_after": 30,
                }
            )

    # Return formatted response
    return session_data.to_response(limit=limiter.SESSION_LIMIT_PER_DAY)


@router.post("/search")
async def playground_search(
    request: PlaygroundSearchRequest,
    req: Request,
    response: Response
):
    """
    Public playground search - rate limited by session/IP.

    Sets httpOnly cookie on first request to track device.
    """
    session_token = _get_session_token(req)
    client_ip = _get_client_ip(req)

    # Rate limit check AND record
    limiter = _get_limiter()
    limit_result = limiter.check_and_record(session_token, client_ip)

    if not limit_result.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "message": limit_result.reason,
                "remaining": 0,
                "limit": limit_result.limit,
                "resets_at": limit_result.resets_at.isoformat(),
            }
        )

    # Set session cookie if new token was created
    if limit_result.session_token:
        _set_session_cookie(response, limit_result.session_token)

    # Validate query
    valid_query, query_error = InputValidator.validate_search_query(request.query)
    if not valid_query:
        raise HTTPException(status_code=400, detail=f"Invalid query: {query_error}")

    # Get demo repo ID
    repo_id = DEMO_REPO_IDS.get(request.demo_repo)
    if not repo_id:
        repos = repo_manager.list_repos()
        indexed_repos = [r for r in repos if r.get("status") == "indexed"]
        if indexed_repos:
            repo_id = indexed_repos[0]["id"]
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Demo repo '{request.demo_repo}' not available"
            )

    start_time = time.time()

    try:
        sanitized_query = InputValidator.sanitize_string(request.query, max_length=200)

        # Check cache
        cached_results = cache.get_search_results(sanitized_query, repo_id)
        if cached_results:
            return {
                "results": cached_results,
                "count": len(cached_results),
                "cached": True,
                "remaining_searches": limit_result.remaining,
                "limit": limit_result.limit,
            }

        # Search
        results = await indexer.semantic_search(
            query=sanitized_query,
            repo_id=repo_id,
            max_results=min(request.max_results, 10),
            use_query_expansion=True,
            use_reranking=True
        )

        # Cache results
        cache.set_search_results(sanitized_query, repo_id, results, ttl=3600)

        search_time = int((time.time() - start_time) * 1000)

        return {
            "results": results,
            "count": len(results),
            "cached": False,
            "remaining_searches": limit_result.remaining,
            "limit": limit_result.limit,
            "search_time_ms": search_time,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Playground search failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repos")
async def list_playground_repos():
    """List available demo repositories."""
    return {
        "repos": [
            {
                "id": "flask",
                "name": "Flask",
                "description": "Python web framework",
                "available": "flask" in DEMO_REPO_IDS
            },
            {
                "id": "fastapi",
                "name": "FastAPI",
                "description": "Modern Python API",
                "available": "fastapi" in DEMO_REPO_IDS
            },
            {
                "id": "express",
                "name": "Express",
                "description": "Node.js framework",
                "available": "express" in DEMO_REPO_IDS
            },
        ]
    }


@router.get("/stats")
async def get_playground_stats():
    """
    Get playground usage stats (for monitoring/debugging).
    """
    limiter = _get_limiter()
    stats = limiter.get_usage_stats()
    return stats
