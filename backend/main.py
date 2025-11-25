"""
CodeIntel Backend API
FastAPI backend for codebase intelligence
"""
from fastapi import FastAPI, HTTPException, Header, WebSocket, WebSocketDisconnect, Depends
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
from middleware.auth import get_current_user

app = FastAPI(
    title="CodeIntel API",
    description="Codebase Intelligence API for MCP",
    version="0.2.0"
)

# Include routers
app.include_router(auth_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Development API Key (for local testing only)
DEV_API_KEY = os.getenv("API_KEY", "dev-secret-key")


def verify_api_key(authorization: str = Header(None)):
    """Verify API key and check rate limits"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    
    # Allow dev key for local development
    if token == DEV_API_KEY and os.getenv("DEBUG", "false").lower() == "true":
        return {"key": token, "tier": "enterprise", "user_id": None, "name": "Development"}
    
    # Verify production API key
    key_data = api_key_manager.verify_key(token)
    if not key_data:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Check rate limits
    allowed, error_msg = rate_limiter.check_rate_limit(token, key_data.get("tier", "free"))
    if not allowed:
        raise HTTPException(status_code=429, detail=error_msg)
    
    return key_data


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


@app.get("/api/repos")
async def list_repositories(current_user: dict = Depends(get_current_user)):
    """List all repositories for authenticated user"""
    user_id = current_user["user_id"]
    
    # TODO: Filter repos by user_id once we add user_id column to repositories table
    # For now, return all repos (will fix in next section)
    repos = repo_manager.list_repos()
    return {"repositories": repos}


@app.post("/api/repos")
async def add_repository(
    request: AddRepoRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add a new repository with validation and cost controls"""
    user_id = current_user["user_id"]
    
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


@app.websocket("/ws/index/{repo_id}")
async def websocket_index(websocket: WebSocket, repo_id: str):
    """Real-time indexing with progress updates"""
    await websocket.accept()
    
    try:
        # Get repo info
        repo = repo_manager.get_repo(repo_id)
        if not repo:
            await websocket.send_json({"error": "Repository not found"})
            await websocket.close()
            return
        
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
    api_key: str = Header(None, alias="Authorization")
):
    """Trigger indexing for a repository - automatically uses incremental if possible"""
    verify_api_key(api_key)
    
    import time
    import git
    start_time = time.time()
    
    try:
        repo = repo_manager.get_repo(repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
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
    api_key: str = Header(None, alias="Authorization")
):
    """Search code semantically with caching and validation"""
    verify_api_key(api_key)
    
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
            max_results=min(request.max_results, 50)  # Cap at 50 results
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
    api_key: str = Header(None, alias="Authorization")
):
    """Generate code explanation"""
    verify_api_key(api_key)
    
    try:
        repo = repo_manager.get_repo(request.repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        explanation = await indexer.explain_code(
            repo_id=request.repo_id,
            file_path=request.file_path,
            function_name=request.function_name
        )
        
        return {"explanation": explanation}
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
    api_key: str = Header(None, alias="Authorization")
):
    """Get dependency graph for repository with Supabase caching"""
    verify_api_key(api_key)
    
    try:
        repo = repo_manager.get_repo(repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
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
    api_key: str = Header(None, alias="Authorization")
):
    """Analyze impact of changing a file with validation and caching"""
    verify_api_key(api_key)
    
    try:
        repo = repo_manager.get_repo(repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
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
    api_key: str = Header(None, alias="Authorization")
):
    """Get comprehensive insights about repository with Supabase caching"""
    verify_api_key(api_key)
    
    try:
        repo = repo_manager.get_repo(repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
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
    api_key: str = Header(None, alias="Authorization")
):
    """Analyze code style and team patterns with Supabase caching"""
    verify_api_key(api_key)
    
    try:
        repo = repo_manager.get_repo(repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
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
    api_key: str = Header(None, alias="Authorization")
):
    """Get performance metrics and monitoring data"""
    verify_api_key(api_key)
    
    return metrics.get_metrics()


# ===== API KEY MANAGEMENT =====

class CreateAPIKeyRequest(BaseModel):
    name: str
    tier: str = "free"


@app.post("/api/keys/generate")
async def generate_api_key(
    request: CreateAPIKeyRequest,
    api_key: str = Header(None, alias="Authorization")
):
    """Generate a new API key (requires existing valid key or dev mode)"""
    key_data = verify_api_key(api_key)
    
    # Generate new key
    new_key = api_key_manager.generate_key(
        name=request.name,
        tier=request.tier,
        user_id=key_data.get("user_id")
    )
    
    return {
        "api_key": new_key,
        "tier": request.tier,
        "name": request.name,
        "message": "Save this key securely - it won't be shown again"
    }


@app.get("/api/keys/usage")
async def get_api_usage(
    api_key: str = Header(None, alias="Authorization")
):
    """Get current API usage stats"""
    key_data = verify_api_key(api_key)
    token = api_key.replace("Bearer ", "")
    
    usage = rate_limiter.get_usage(token)
    
    return {
        "tier": key_data.get("tier", "free"),
        "limits": {
            "free": {"minute": 20, "hour": 200, "day": 1000},
            "pro": {"minute": 100, "hour": 2000, "day": 20000},
            "enterprise": {"minute": 500, "hour": 10000, "day": 100000}
        }[key_data.get("tier", "free")],
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
