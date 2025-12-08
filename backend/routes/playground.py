"""Playground routes - no auth required, rate limited."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from collections import defaultdict
import time as time_module

from dependencies import indexer, cache, repo_manager
from services.input_validator import InputValidator

router = APIRouter(prefix="/api/playground", tags=["Playground"])

# Demo repo mapping (populated on startup)
DEMO_REPO_IDS = {}

# Rate limiting config
PLAYGROUND_LIMIT = 10  # searches per hour
PLAYGROUND_WINDOW = 3600  # 1 hour
playground_rate_limits = defaultdict(list)


class PlaygroundSearchRequest(BaseModel):
    query: str
    demo_repo: str = "flask"
    max_results: int = 10


async def load_demo_repos():
    """Load pre-indexed demo repos. Called from main.py on startup."""
    global DEMO_REPO_IDS
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
        print(f"📦 Loaded demo repos: {list(DEMO_REPO_IDS.keys())}")
    except Exception as e:
        print(f"⚠️ Could not load demo repos: {e}")


def _check_rate_limit(ip: str) -> tuple[bool, int]:
    """Check if IP is within rate limit."""
    now = time_module.time()
    playground_rate_limits[ip] = [
        t for t in playground_rate_limits[ip] if now - t < PLAYGROUND_WINDOW
    ]
    remaining = PLAYGROUND_LIMIT - len(playground_rate_limits[ip])
    return (remaining > 0, max(0, remaining))


def _record_search(ip: str):
    """Record a search for rate limiting."""
    playground_rate_limits[ip].append(time_module.time())


def _get_client_ip(req: Request) -> str:
    """Extract client IP from request."""
    client_ip = req.client.host if req.client else "unknown"
    forwarded = req.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    return client_ip


@router.post("/search")
async def playground_search(request: PlaygroundSearchRequest, req: Request):
    """Public playground search - rate limited by IP."""
    client_ip = _get_client_ip(req)
    
    # Rate limit check
    allowed, remaining = _check_rate_limit(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Sign up for unlimited searches!"
        )
    
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
    
    import time
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
                "remaining_searches": remaining
            }
        
        # Search
        results = await indexer.semantic_search(
            query=sanitized_query,
            repo_id=repo_id,
            max_results=min(request.max_results, 10),
            use_query_expansion=True,
            use_reranking=True
        )
        
        # Cache and record
        cache.set_search_results(sanitized_query, repo_id, results, ttl=3600)
        _record_search(client_ip)
        
        return {
            "results": results,
            "count": len(results),
            "cached": False,
            "remaining_searches": remaining - 1
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repos")
async def list_playground_repos():
    """List available demo repositories."""
    return {
        "repos": [
            {"id": "flask", "name": "Flask", "description": "Python web framework", "available": "flask" in DEMO_REPO_IDS},
            {"id": "fastapi", "name": "FastAPI", "description": "Modern Python API", "available": "fastapi" in DEMO_REPO_IDS},
            {"id": "express", "name": "Express", "description": "Node.js framework", "available": "express" in DEMO_REPO_IDS},
        ]
    }
