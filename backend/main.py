"""
CodeIntel Backend API
FastAPI backend for codebase intelligence
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import hashlib
from dotenv import load_dotenv
import asyncio

# Load environment variables FIRST before importing services
load_dotenv()

# Import services (these need env vars loaded)
from services.indexer_optimized import OptimizedCodeIndexer
from services.repo_manager import RepositoryManager
from services.cache import CacheService
from services.dependency_analyzer import DependencyAnalyzer
from services.style_analyzer import StyleAnalyzer
from services.performance_metrics import PerformanceMetrics
from services.rate_limiter import RateLimiter, APIKeyManager
from services.supabase_service import get_supabase_service
from services.input_validator import InputValidator, CostController

# Import routers
from routes.auth import router as auth_router
from middleware.auth import require_auth, AuthContext

app = FastAPI(
    title="CodeIntel API",
    description="Codebase Intelligence API for MCP",
    version="0.2.0"
)

# Include routers
app.include_router(auth_router)

# CORS middleware - Restrict to specific origins for security
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Request size limit middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent abuse"""
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.MAX_REQUEST_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request too large (max {self.MAX_REQUEST_SIZE / 1024 / 1024}MB)"}
                )
        return await call_next(request)

app.add_middleware(RequestSizeLimitMiddleware)

# Initialize services
indexer = OptimizedCodeIndexer()
cache = CacheService()
repo_manager = RepositoryManager()
dependency_analyzer = DependencyAnalyzer()
style_analyzer = StyleAnalyzer()
metrics = PerformanceMetrics()

# Rate limiting and API key management
rate_limiter = RateLimiter(redis_client=cache.redis if cache.redis else None)
api_key_manager = APIKeyManager(get_supabase_service().client)
cost_controller = CostController(get_supabase_service().client)


# ===== SECURITY HELPERS =====

def get_repo_or_404(repo_id: str, user_id: str) -> dict:
    """
    Get repository with ownership verification.
    Returns 404 if repo doesn't exist OR if user doesn't own it.
    (We return 404 instead of 403 to not leak info about repo existence)
    """
    repo = repo_manager.get_repo_for_user(repo_id, user_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


def verify_repo_access(repo_id: str, user_id: str) -> None:
    """
    Verify user has access to repository.
    Raises 404 if no access (not 403, to avoid leaking repo existence).
    """
    if not repo_manager.verify_ownership(repo_id, user_id):
        raise HTTPException(status_code=404, detail="Repository not found")

# Request/Response Models
class SearchRequest(BaseModel):
    query: str
    repo_id: str
    max_results: int = 10


class ExplainRequest(BaseModel):
    repo_id: str
    file_path: str
    function_name: Optional[str] = None


class AddRepoRequest(BaseModel):
    name: str
    git_url: str
    branch: str = "main"


# API Routes
@app.get("/health")
async def health_check():
    """Health check endpoint with metrics"""
    perf_metrics = metrics.get_metrics()
    
    return {
        "status": "healthy",
        "service": "codeintel-api",
        "performance": perf_metrics["summary"]
    }


# ============== PLAYGROUND (No Auth Required) ==============

class PlaygroundSearchRequest(BaseModel):
    query: str
    demo_repo: str = "flask"
    max_results: int = 10

# Map demo repo names to actual repo IDs (will be populated on startup)
DEMO_REPO_IDS = {}

@app.on_event("startup")
async def load_demo_repos():
    """Load pre-indexed demo repos on startup"""
    global DEMO_REPO_IDS
    try:
        repos = repo_manager.list_repos()
        # Map common repo names to their IDs
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

# Simple in-memory rate limiting for playground (IP-based)
from collections import defaultdict
import time as time_module

playground_rate_limits = defaultdict(list)
PLAYGROUND_LIMIT = 10  # searches per hour
PLAYGROUND_WINDOW = 3600  # 1 hour in seconds

def check_playground_rate_limit(ip: str) -> tuple[bool, int]:
    """Check if IP is within rate limit. Returns (allowed, remaining)"""
    now = time_module.time()
    # Clean old entries
    playground_rate_limits[ip] = [t for t in playground_rate_limits[ip] if now - t < PLAYGROUND_WINDOW]
    
    remaining = PLAYGROUND_LIMIT - len(playground_rate_limits[ip])
    if remaining <= 0:
        return False, 0
    
    return True, remaining

def record_playground_search(ip: str):
    """Record a playground search for rate limiting"""
    playground_rate_limits[ip].append(time_module.time())


@app.post("/api/playground/search")
async def playground_search(request: PlaygroundSearchRequest, req: Request):
    """
    Public playground search - no auth required, rate limited by IP.
    Only works with pre-indexed demo repositories.
    """
    # Get client IP
    client_ip = req.client.host if req.client else "unknown"
    forwarded = req.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    
    # Check rate limit
    allowed, remaining = check_playground_rate_limit(client_ip)
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
        # Fallback: try to find any indexed repo
        repos = repo_manager.list_repos()
        indexed_repos = [r for r in repos if r.get("status") == "indexed"]
        if indexed_repos:
            repo_id = indexed_repos[0]["id"]
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"Demo repo '{request.demo_repo}' not available. Available: {list(DEMO_REPO_IDS.keys())}"
            )
    
    import time
    start_time = time.time()
    
    try:
        # Sanitize query
        sanitized_query = InputValidator.sanitize_string(request.query, max_length=200)
        
        # Check cache first
        cache_key = f"playground:{request.demo_repo}:{sanitized_query}"
        cached_results = cache.get_search_results(sanitized_query, repo_id)
        if cached_results:
            return {
                "results": cached_results, 
                "count": len(cached_results), 
                "cached": True,
                "remaining_searches": remaining
            }
        
        # Do search
        results = await indexer.semantic_search(
            query=sanitized_query,
            repo_id=repo_id,
            max_results=min(request.max_results, 10),  # Cap at 10 for playground
            use_query_expansion=True,
            use_reranking=True
        )
        
        # Cache results
        cache.set_search_results(sanitized_query, repo_id, results, ttl=3600)
        
        # Record for rate limiting
        record_playground_search(client_ip)
        
        return {
            "results": results, 
            "count": len(results), 
            "cached": False,
            "remaining_searches": remaining - 1
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/playground/repos")
async def list_playground_repos():
    """List available demo repositories for playground"""
    return {
        "repos": [
            {"id": "flask", "name": "Flask", "description": "Python web framework", "available": "flask" in DEMO_REPO_IDS},
            {"id": "fastapi", "name": "FastAPI", "description": "Modern Python API", "available": "fastapi" in DEMO_REPO_IDS},
            {"id": "express", "name": "Express", "description": "Node.js framework", "available": "express" in DEMO_REPO_IDS},
        ]
    }


# ============== AUTHENTICATED ENDPOINTS ==============

@app.get("/api/repos")
async def list_repositories(auth: AuthContext = Depends(require_auth)):
    """List all repositories for authenticated user"""
    user_id = auth.user_id
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    # Only return repos owned by this user
    repos = repo_manager.list_repos_for_user(user_id)
    return {"repositories": repos}


@app.post("/api/repos")
async def add_repository(
    request: AddRepoRequest,
    auth: AuthContext = Depends(require_auth)
):
    """Add a new repository with validation and cost controls"""
    user_id = auth.user_id or auth.identifier
    
    # Validate repository name
    valid_name, name_error = InputValidator.validate_repo_name(request.name)
    if not valid_name:
        raise HTTPException(status_code=400, detail=f"Invalid repository name: {name_error}")
    
    # Validate Git URL
    valid_url, url_error = InputValidator.validate_git_url(request.git_url)
    if not valid_url:
        raise HTTPException(status_code=400, detail=f"Invalid Git URL: {url_error}")
    
    # Check repository limit
    user_id_hash = hashlib.sha256(user_id.encode()).hexdigest()
    
    can_add, limit_error = cost_controller.check_repo_limit(user_id, user_id_hash)
    if not can_add:
        raise HTTPException(status_code=429, detail=limit_error)
    
    try:
        repo = repo_manager.add_repo(
            name=request.name,
            git_url=request.git_url,
            branch=request.branch,
            user_id=user_id,
            api_key_hash=user_id_hash
        )
        
        # Check repo size before allowing indexing
        can_index, size_error = cost_controller.check_repo_size_limit(repo["local_path"])
        if not can_index:
            # Still add repo but warn about size
            return {
                "repo_id": repo["id"], 
                "status": "added", 
                "warning": size_error,
                "message": "Repository added but too large for automatic indexing"
            }
        
        return {
            "repo_id": repo["id"], 
            "status": "added", 
            "message": "Repository added successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def authenticate_websocket(websocket: WebSocket) -> Optional[dict]:
    """
    Authenticate WebSocket connection via query parameter token.
    
    WebSockets can't use Authorization headers during handshake,
    so we pass the JWT token as a query parameter instead.
    
    Returns:
        User dict if authenticated, None otherwise (connection closed with error)
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return None
    
    try:
        from services.auth import get_auth_service
        auth_service = get_auth_service()
        return auth_service.verify_jwt(token)
    except Exception:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return None


@app.websocket("/ws/index/{repo_id}")
async def websocket_index(websocket: WebSocket, repo_id: str):
    """
    Real-time repository indexing with progress updates.
    
    Requires JWT token passed as query parameter: ?token=<jwt>
    Sends progress updates via JSON messages during indexing.
    """
    # Authenticate before accepting connection
    user = await authenticate_websocket(websocket)
    if not user:
        return
    
    user_id = user.get("user_id")
    if not user_id:
        await websocket.close(code=4001, reason="User ID required")
        return
    
    # Verify user owns this repository (return same error to not leak info)
    repo = repo_manager.get_repo_for_user(repo_id, user_id)
    if not repo:
        await websocket.close(code=4004, reason="Repository not found")
        return
    
    # Connection authenticated and repo ownership verified - accept
    await websocket.accept()
    
    try:
        repo_manager.update_status(repo_id, "indexing")
        
        # Index with progress callback
        async def progress_callback(files_processed: int, functions_indexed: int, total_files: int):
            await websocket.send_json({
                "type": "progress",
                "files_processed": files_processed,
                "functions_indexed": functions_indexed,
                "total_files": total_files,
                "progress_pct": int((files_processed / total_files) * 100) if total_files > 0 else 0
            })
        
        # Index repository with progress
        total_functions = await indexer.index_repository_with_progress(
            repo_id,
            repo["local_path"],
            progress_callback
        )
        
        repo_manager.update_status(repo_id, "indexed")
        repo_manager.update_file_count(repo_id, total_functions)
        
        # Send completion
        await websocket.send_json({
            "type": "complete",
            "total_functions": total_functions
        })
        
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for repo {repo_id}")
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
        repo_manager.update_status(repo_id, "error")
    finally:
        await websocket.close()


@app.post("/api/repos/{repo_id}/index")
async def index_repository(
    repo_id: str,
    incremental: bool = True,
    auth: AuthContext = Depends(require_auth)
):
    """Trigger indexing for a repository - automatically uses incremental if possible"""
    
    import time
    import git
    start_time = time.time()
    
    try:
        # Verify ownership - returns 404 if not owned
        repo = get_repo_or_404(repo_id, auth.user_id)
        
        # Set status to indexing
        repo_manager.update_status(repo_id, "indexing")
        
        # Check if we can do incremental
        last_commit = repo_manager.get_last_indexed_commit(repo_id)
        
        if incremental and last_commit:
            print(f"🔄 Using INCREMENTAL indexing (last: {last_commit[:8]})")
            total_functions = await indexer.incremental_index_repository(
                repo_id, 
                repo["local_path"],
                last_commit
            )
            index_type = "incremental"
        else:
            print(f"📦 Using FULL indexing")
            total_functions = await indexer.index_repository(repo_id, repo["local_path"])
            index_type = "full"
        
        # Update repo metadata
        git_repo = git.Repo(repo["local_path"])
        current_commit = git_repo.head.commit.hexsha
        
        repo_manager.update_status(repo_id, "indexed")
        repo_manager.update_file_count(repo_id, total_functions)
        repo_manager.update_last_commit(repo_id, current_commit)
        
        # Track performance
        duration = time.time() - start_time
        metrics.record_indexing(repo_id, duration, total_functions)
        
        return {
            "status": "indexed", 
            "repo_id": repo_id, 
            "functions": total_functions, 
            "duration": f"{duration:.2f}s",
            "index_type": index_type,
            "commit": current_commit[:8]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search")
async def search_code(
    request: SearchRequest,
    auth: AuthContext = Depends(require_auth)
):
    """Search code semantically with caching and validation"""
    
    # Verify user owns the repository
    verify_repo_access(request.repo_id, auth.user_id)
    
    # Validate search query
    valid_query, query_error = InputValidator.validate_search_query(request.query)
    if not valid_query:
        raise HTTPException(status_code=400, detail=f"Invalid query: {query_error}")
    
    # Sanitize query
    sanitized_query = InputValidator.sanitize_string(request.query, max_length=500)
    
    import time
    start_time = time.time()
    
    try:
        # Check cache first
        cached_results = cache.get_search_results(sanitized_query, request.repo_id)
        if cached_results:
            duration = time.time() - start_time
            metrics.record_search(duration, cached=True)
            return {"results": cached_results, "count": len(cached_results), "cached": True}
        
        # Not in cache - do search
        results = await indexer.semantic_search(
            query=sanitized_query,
            repo_id=request.repo_id,
            max_results=min(request.max_results, 50),  # Cap at 50 results
            use_query_expansion=True,
            use_reranking=True
        )
        
        # Cache results
        cache.set_search_results(sanitized_query, request.repo_id, results, ttl=3600)
        
        # Track performance
        duration = time.time() - start_time
        metrics.record_search(duration, cached=False)
        
        return {"results": results, "count": len(results), "cached": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/explain")
async def explain_code(
    request: ExplainRequest,
    auth: AuthContext = Depends(require_auth)
):
    """Generate code explanation"""
    
    try:
        # Verify ownership
        repo = get_repo_or_404(request.repo_id, auth.user_id)
        
        explanation = await indexer.explain_code(
            repo_id=request.repo_id,
            file_path=request.file_path,
            function_name=request.function_name
        )
        
        return {"explanation": explanation}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === ADVANCED FEATURES ===

# New request models
class ImpactRequest(BaseModel):
    repo_id: str
    file_path: str


@app.get("/api/repos/{repo_id}/dependencies")
async def get_dependency_graph(
    repo_id: str,
    auth: AuthContext = Depends(require_auth)
):
    """Get dependency graph for repository with Supabase caching"""
    
    try:
        # Verify ownership
        repo = get_repo_or_404(repo_id, auth.user_id)
        
        # Try loading from Supabase cache
        cached_graph = dependency_analyzer.load_from_cache(repo_id)
        
        if cached_graph:
            print(f"✅ Using cached dependency graph for {repo_id}")
            return {**cached_graph, "cached": True}
        
        # Build fresh dependency graph
        print(f"🔄 Building fresh dependency graph for {repo_id}")
        graph_data = dependency_analyzer.build_dependency_graph(repo["local_path"])
        
        # Save to Supabase cache
        dependency_analyzer.save_to_cache(repo_id, graph_data)
        
        return {**graph_data, "cached": False}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/repos/{repo_id}/impact")
async def analyze_impact(
    repo_id: str,
    request: ImpactRequest,
    auth: AuthContext = Depends(require_auth)
):
    """Analyze impact of changing a file with validation and caching"""
    
    try:
        # Verify ownership
        repo = get_repo_or_404(repo_id, auth.user_id)
        
        # Validate file path
        valid_path, path_error = InputValidator.validate_file_path(request.file_path, repo["local_path"])
        if not valid_path:
            raise HTTPException(status_code=400, detail=f"Invalid file path: {path_error}")
        
        # Try loading cached graph from Supabase
        graph_data = dependency_analyzer.load_from_cache(repo_id)
        
        if not graph_data:
            # Build and cache
            print(f"🔄 Building dependency graph for impact analysis")
            graph_data = dependency_analyzer.build_dependency_graph(repo["local_path"])
            dependency_analyzer.save_to_cache(repo_id, graph_data)
        
        # Analyze impact
        impact = dependency_analyzer.get_file_impact(
            repo["local_path"],
            request.file_path,
            graph_data
        )
        
        return impact
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/repos/{repo_id}/insights")
async def get_repository_insights(
    repo_id: str,
    auth: AuthContext = Depends(require_auth)
):
    """Get comprehensive insights about repository with Supabase caching"""
    
    try:
        # Verify ownership
        repo = get_repo_or_404(repo_id, auth.user_id)
        
        # Try loading cached graph from Supabase
        graph_data = dependency_analyzer.load_from_cache(repo_id)
        
        if not graph_data:
            # Build and cache
            print(f"🔄 Building dependency graph for insights")
            graph_data = dependency_analyzer.build_dependency_graph(repo["local_path"])
            dependency_analyzer.save_to_cache(repo_id, graph_data)
        
        return {
            "repo_id": repo_id,
            "name": repo["name"],
            "graph_metrics": graph_data.get("metrics", {}),
            "total_files": len(graph_data.get("dependencies", {})),
            "total_dependencies": sum(len(deps) for deps in graph_data.get("dependencies", {}).values()),
            "status": repo["status"],
            "functions_indexed": repo["file_count"],
            "cached": bool(graph_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# New request models
class ImpactRequest(BaseModel):
    repo_id: str
    file_path: str


@app.get("/api/repos/{repo_id}/style-analysis")
async def get_style_analysis(
    repo_id: str,
    auth: AuthContext = Depends(require_auth)
):
    """Analyze code style and team patterns with Supabase caching"""
    
    try:
        # Verify ownership
        repo = get_repo_or_404(repo_id, auth.user_id)
        
        # Try loading from Supabase cache
        cached_style = style_analyzer.load_from_cache(repo_id)
        
        if cached_style:
            print(f"✅ Using cached code style for {repo_id}")
            return {**cached_style, "cached": True}
        
        # Analyze style
        print(f"🔄 Analyzing code style for {repo_id}")
        style_data = style_analyzer.analyze_repository_style(repo["local_path"])
        
        # Save to Supabase cache
        style_analyzer.save_to_cache(repo_id, style_data)
        
        return {**style_data, "cached": False}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics")
async def get_performance_metrics(
    auth: AuthContext = Depends(require_auth)
):
    """Get performance metrics and monitoring data"""
    return metrics.get_metrics()


# ===== API KEY MANAGEMENT =====

class CreateAPIKeyRequest(BaseModel):
    name: str
    tier: str = "free"


@app.post("/api/keys/generate")
async def generate_api_key(
    request: CreateAPIKeyRequest,
    auth: AuthContext = Depends(require_auth)
):
    """Generate a new API key (requires existing valid key or dev mode)"""
    # Generate new key
    new_key = api_key_manager.generate_key(
        name=request.name,
        tier=request.tier,
        user_id=auth.user_id
    )
    
    return {
        "api_key": new_key,
        "tier": request.tier,
        "name": request.name,
        "message": "Save this key securely - it won't be shown again"
    }


@app.get("/api/keys/usage")
async def get_api_usage(
    auth: AuthContext = Depends(require_auth)
):
    """Get current API usage stats"""
    usage = rate_limiter.get_usage(auth.identifier)
    
    return {
        "tier": auth.tier,
        "limits": {
            "free": {"minute": 20, "hour": 200, "day": 1000},
            "pro": {"minute": 100, "hour": 2000, "day": 20000},
            "enterprise": {"minute": 500, "hour": 10000, "day": 100000}
        }[auth.tier],
        "usage": usage
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Custom exception handlers for better error responses
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors with clean responses"""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )

@app.exception_handler(429)
async def rate_limit_handler(request, exc):
    """Handle rate limit errors"""
    return JSONResponse(
        status_code=429,
        content={
            "detail": str(exc.detail) if hasattr(exc, 'detail') else "Rate limit exceeded",
            "retry_after": 60  # Retry after 1 minute
        }
    )
