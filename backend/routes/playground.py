"""
Playground routes - no auth required, rate limited via Redis.

Rate limiting strategy (see #93):
- Session token (httpOnly cookie): 50 searches/day per device
- IP fallback: 100 searches/day for shared networks
- Global circuit breaker: 10k searches/hour (cost protection)
"""
import os
import re
import httpx
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Response, BackgroundTasks
from pydantic import BaseModel, field_validator
import time

from dependencies import indexer, cache, repo_manager, redis_client
from services.input_validator import InputValidator
from services.repo_validator import RepoValidator
from services.observability import logger
from services.playground_limiter import PlaygroundLimiter, get_playground_limiter
from services.anonymous_indexer import (
    AnonymousIndexingJob,
    run_indexing_job,
)

router = APIRouter(prefix="/playground", tags=["Playground"])

# Demo repo mapping (populated on startup)
DEMO_REPO_IDS = {}

# Session cookie config
SESSION_COOKIE_NAME = "pg_session"
SESSION_COOKIE_MAX_AGE = 86400  # 24 hours
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"

# GitHub validation config
GITHUB_URL_PATTERN = re.compile(
    r"^https?://github\.com/(?P<owner>[a-zA-Z0-9_.-]+)/(?P<repo>[a-zA-Z0-9_.-]+)/?$"
)
ANONYMOUS_FILE_LIMIT = 200  # Max files for anonymous indexing
GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_TIMEOUT = 10.0  # seconds
VALIDATION_CACHE_TTL = 300  # 5 minutes


class PlaygroundSearchRequest(BaseModel):
    query: str
    demo_repo: str = "flask"
    max_results: int = 10


class ValidateRepoRequest(BaseModel):
    """Request body for GitHub repo validation."""
    github_url: str

    @field_validator("github_url")
    @classmethod
    def validate_github_url_format(cls, v: str) -> str:
        """Basic URL format validation."""
        v = v.strip()
        if not v:
            raise ValueError("GitHub URL is required")
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        if "github.com" not in v.lower():
            raise ValueError("URL must be a GitHub repository URL")
        return v


class IndexRepoRequest(BaseModel):
    """
    Request body for anonymous repository indexing.

    Used by POST /playground/index endpoint (#125).
    """
    github_url: str
    branch: Optional[str] = None  # None = use repo's default branch

    @field_validator("github_url")
    @classmethod
    def validate_github_url_format(cls, v: str) -> str:
        """Basic URL format validation (detailed validation in endpoint)."""
        v = v.strip()
        if not v:
            raise ValueError("GitHub URL is required")
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        if "github.com" not in v.lower():
            raise ValueError("URL must be a GitHub repository URL")
        return v


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


def _parse_github_url(url: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse GitHub URL to extract owner and repo.

    Returns:
        (owner, repo, error) - error is None if successful
    """
    match = GITHUB_URL_PATTERN.match(url.strip().rstrip("/"))
    if not match:
        return None, None, "Invalid GitHub URL format. Expected: https://github.com/owner/repo"
    return match.group("owner"), match.group("repo"), None


async def _fetch_repo_metadata(owner: str, repo: str) -> dict:
    """
    Fetch repository metadata from GitHub API.

    Returns dict with repo info or error details.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "OpenCodeIntel/1.0",
    }

    # Add GitHub token if available (for higher rate limits)
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    async with httpx.AsyncClient(timeout=GITHUB_API_TIMEOUT) as client:
        try:
            response = await client.get(url, headers=headers)

            if response.status_code == 404:
                return {"error": "not_found", "message": "Repository not found"}
            if response.status_code == 403:
                return {
                    "error": "rate_limited",
                    "message": "GitHub API rate limit exceeded"
                }
            if response.status_code != 200:
                return {
                    "error": "api_error",
                    "message": f"GitHub API error: {response.status_code}"
                }

            return response.json()
        except httpx.TimeoutException:
            return {"error": "timeout", "message": "GitHub API request timed out"}
        except Exception as e:
            logger.error("GitHub API request failed", error=str(e))
            return {"error": "request_failed", "message": str(e)}


async def _count_code_files(
    owner: str, repo: str, default_branch: str
) -> tuple[int, Optional[str]]:
    """
    Count code files in repository using GitHub tree API.

    Returns:
        (file_count, error) - error is None if successful
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "OpenCodeIntel/1.0",
    }

    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    async with httpx.AsyncClient(timeout=GITHUB_API_TIMEOUT) as client:
        try:
            response = await client.get(url, headers=headers)

            if response.status_code == 404:
                return 0, "Could not fetch repository tree"
            if response.status_code == 403:
                return 0, "GitHub API rate limit exceeded"
            if response.status_code != 200:
                return 0, f"GitHub API error: {response.status_code}"

            data = response.json()

            # Check if tree was truncated (very large repos)
            if data.get("truncated", False):
                # For truncated trees, estimate from repo size
                # GitHub's size is in KB, rough estimate: 1 code file per 5KB
                return -1, "truncated"

            # Count files with code extensions
            code_extensions = RepoValidator.CODE_EXTENSIONS
            skip_dirs = RepoValidator.SKIP_DIRS

            count = 0
            for item in data.get("tree", []):
                if item.get("type") != "blob":
                    continue

                path = item.get("path", "")

                # Skip if in excluded directory
                path_parts = path.split("/")
                if any(part in skip_dirs for part in path_parts):
                    continue

                # Check extension
                ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
                if ext.lower() in code_extensions:
                    count += 1

            return count, None
        except httpx.TimeoutException:
            return 0, "GitHub API request timed out"
        except Exception as e:
            logger.error("GitHub tree API failed", error=str(e))
            return 0, str(e)


@router.post("/validate-repo")
async def validate_github_repo(request: ValidateRepoRequest, req: Request):
    """
    Validate a GitHub repository URL for anonymous indexing.

    Checks:
    - URL format is valid
    - Repository exists and is public
    - File count is within anonymous limit (200 files)

    Response varies based on validation result (see issue #124).
    """
    start_time = time.time()

    # Check cache first
    cache_key = f"validate:{request.github_url}"
    cached = cache.get(cache_key) if cache else None
    if cached:
        logger.info("Returning cached validation", url=request.github_url[:50])
        return cached

    # Parse URL
    owner, repo_name, parse_error = _parse_github_url(request.github_url)
    if parse_error:
        return {
            "valid": False,
            "reason": "invalid_url",
            "message": parse_error,
        }

    # Fetch repo metadata from GitHub
    metadata = await _fetch_repo_metadata(owner, repo_name)

    if "error" in metadata:
        error_type = metadata["error"]
        if error_type == "not_found":
            return {
                "valid": False,
                "reason": "not_found",
                "message": "Repository not found. Check the URL or ensure it's public.",
            }
        elif error_type == "rate_limited":
            raise HTTPException(
                status_code=429,
                detail={"message": "GitHub API rate limit exceeded. Try again later."}
            )
        else:
            raise HTTPException(
                status_code=502,
                detail={"message": metadata.get("message", "Failed to fetch repository info")}
            )

    # Check if private
    is_private = metadata.get("private", False)
    if is_private:
        return {
            "valid": True,
            "repo_name": repo_name,
            "owner": owner,
            "is_public": False,
            "can_index": False,
            "reason": "private",
            "message": "This repository is private. "
                       "Anonymous indexing only supports public repositories.",
        }

    # Get file count
    default_branch = metadata.get("default_branch", "main")
    file_count, count_error = await _count_code_files(owner, repo_name, default_branch)

    # Handle truncated tree (very large repo)
    if count_error == "truncated":
        # Estimate from repo size (GitHub size is in KB)
        repo_size_kb = metadata.get("size", 0)
        # Rough estimate: 1 code file per 3KB for code repos
        file_count = max(repo_size_kb // 3, ANONYMOUS_FILE_LIMIT + 1)
        logger.info("Using estimated file count for large repo",
                    owner=owner, repo=repo_name, estimated=file_count)

    elif count_error:
        logger.warning("Could not count files", owner=owner, repo=repo_name, error=count_error)
        # Fall back to size-based estimate
        repo_size_kb = metadata.get("size", 0)
        file_count = max(repo_size_kb // 3, 1)

    # Build response
    response_time_ms = int((time.time() - start_time) * 1000)

    if file_count > ANONYMOUS_FILE_LIMIT:
        result = {
            "valid": True,
            "repo_name": repo_name,
            "owner": owner,
            "is_public": True,
            "default_branch": default_branch,
            "file_count": file_count,
            "size_kb": metadata.get("size", 0),
            "language": metadata.get("language"),
            "stars": metadata.get("stargazers_count", 0),
            "can_index": False,
            "reason": "too_large",
            "message": f"Repository has {file_count:,} code files. "
                       f"Anonymous limit is {ANONYMOUS_FILE_LIMIT}.",
            "limit": ANONYMOUS_FILE_LIMIT,
            "response_time_ms": response_time_ms,
        }
    else:
        result = {
            "valid": True,
            "repo_name": repo_name,
            "owner": owner,
            "is_public": True,
            "default_branch": default_branch,
            "file_count": file_count,
            "size_kb": metadata.get("size", 0),
            "language": metadata.get("language"),
            "stars": metadata.get("stargazers_count", 0),
            "can_index": True,
            "message": "Ready to index",
            "response_time_ms": response_time_ms,
        }

    # Cache successful validations
    if cache:
        cache.set(cache_key, result, ttl=VALIDATION_CACHE_TTL)

    logger.info("Validated GitHub repo",
                owner=owner, repo=repo_name,
                file_count=file_count, can_index=result["can_index"],
                response_time_ms=response_time_ms)

    return result


# =============================================================================
# Anonymous Indexing Endpoint (#125)
# =============================================================================

@router.post("/index", status_code=202)
async def start_anonymous_indexing(
    request: IndexRepoRequest,
    req: Request,
    response: Response,
    background_tasks: BackgroundTasks
):
    """
    Start indexing a public GitHub repository for anonymous users.

    This endpoint validates the repository and queues it for indexing.
    Returns a job_id that can be used to poll for status via GET /index/{job_id}.

    Constraints:
    - Max 200 code files (anonymous limit)
    - 1 repo per session (no concurrent indexing)
    - Public repos only
    - 24hr TTL on indexed data

    See issue #125 for full specification.
    """
    start_time = time.time()
    limiter = _get_limiter()

    # --- Step 1: Session validation (get existing or create new) ---
    session_token = _get_session_token(req)
    client_ip = _get_client_ip(req)

    if not session_token:
        # Create new session
        session_token = limiter.create_session()
        _set_session_cookie(response, session_token)
        logger.info("Created new session for indexing",
                    session_token=session_token[:8],
                    client_ip=client_ip)

    # --- Step 2: Check if session already has an indexed repo ---
    session_data = limiter.get_session_data(session_token)

    if session_data.indexed_repo:
        # Check if the existing repo has expired
        from datetime import datetime, timezone

        expires_at_str = session_data.indexed_repo.get("expires_at", "")
        is_expired = False

        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                is_expired = datetime.now(timezone.utc) > expires_at
            except (ValueError, AttributeError):
                is_expired = True  # Treat parse errors as expired

        if not is_expired:
            # Session already has a valid indexed repo - return 409 Conflict
            logger.info("Session already has indexed repo",
                        session_token=session_token[:8],
                        existing_repo=session_data.indexed_repo.get("repo_id"))

            raise HTTPException(
                status_code=409,
                detail={
                    "error": "already_indexed",
                    "message": "You already have an indexed repository. "
                               "Only 1 repo per session allowed.",
                    "indexed_repo": session_data.indexed_repo
                }
            )
        else:
            # Existing repo expired - allow new indexing
            logger.info("Existing indexed repo expired, allowing new indexing",
                        session_token=session_token[:8])

    # --- Step 3: Validate GitHub URL (reuse existing logic) ---
    owner, repo_name, parse_error = _parse_github_url(request.github_url)
    if parse_error:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_failed",
                "reason": "invalid_url",
                "message": parse_error
            }
        )

    # Fetch repo metadata from GitHub
    metadata = await _fetch_repo_metadata(owner, repo_name)

    if "error" in metadata:
        error_type = metadata["error"]
        if error_type == "not_found":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_failed",
                    "reason": "not_found",
                    "message": "Repository not found. Check the URL or ensure it's public."
                }
            )
        elif error_type == "rate_limited":
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "github_rate_limit",
                    "message": "GitHub API rate limit exceeded. Try again later."
                }
            )
        else:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "github_error",
                    "message": metadata.get("message", "Failed to fetch repository info")
                }
            )

    # Check if private
    if metadata.get("private", False):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_failed",
                "reason": "private",
                "message": "This repository is private. "
                           "Anonymous indexing only supports public repositories."
            }
        )

    # Determine branch
    branch = request.branch or metadata.get("default_branch", "main")

    # Get file count
    file_count, count_error = await _count_code_files(owner, repo_name, branch)

    # Handle truncated tree (very large repo)
    if count_error == "truncated":
        repo_size_kb = metadata.get("size", 0)
        file_count = max(repo_size_kb // 3, ANONYMOUS_FILE_LIMIT + 1)
    elif count_error:
        repo_size_kb = metadata.get("size", 0)
        file_count = max(repo_size_kb // 3, 1)

    # Check file limit
    if file_count > ANONYMOUS_FILE_LIMIT:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_failed",
                "reason": "too_large",
                "message": f"Repository has {file_count:,} code files. "
                           f"Anonymous limit is {ANONYMOUS_FILE_LIMIT}.",
                "file_count": file_count,
                "limit": ANONYMOUS_FILE_LIMIT
            }
        )

    # --- Validation passed! Create job and start background indexing ---

    response_time_ms = int((time.time() - start_time) * 1000)

    # Initialize job manager
    job_manager = AnonymousIndexingJob(redis_client)
    job_id = job_manager.generate_job_id()

    # Create job in Redis
    job_manager.create_job(
        job_id=job_id,
        session_id=session_token,
        github_url=request.github_url,
        owner=owner,
        repo_name=repo_name,
        branch=branch,
        file_count=file_count
    )

    # Queue background task
    background_tasks.add_task(
        run_indexing_job,
        job_manager=job_manager,
        indexer=indexer,
        limiter=limiter,
        job_id=job_id,
        session_id=session_token,
        github_url=request.github_url,
        owner=owner,
        repo_name=repo_name,
        branch=branch,
        file_count=file_count
    )

    logger.info("Indexing job queued",
                job_id=job_id,
                owner=owner,
                repo=repo_name,
                branch=branch,
                file_count=file_count,
                session_token=session_token[:8],
                response_time_ms=response_time_ms)

    # Estimate time based on file count (~0.3s per file)
    estimated_seconds = max(10, int(file_count * 0.3))

    return {
        "job_id": job_id,
        "status": "queued",
        "estimated_time_seconds": estimated_seconds,
        "file_count": file_count,
        "message": f"Indexing started. Poll /playground/index/{job_id} for status."
    }
