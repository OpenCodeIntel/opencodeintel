"""Search and explain routes."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import time

from dependencies import (
    indexer, cache, metrics,
    get_repo_or_404, verify_repo_access
)
from services.input_validator import InputValidator
from middleware.auth import require_auth, AuthContext

router = APIRouter(prefix="", tags=["Search"])


class SearchRequest(BaseModel):
    query: str
    repo_id: str
    max_results: int = 10


class ExplainRequest(BaseModel):
    repo_id: str
    file_path: str
    function_name: Optional[str] = None


@router.post("/search")
async def search_code(
    request: SearchRequest,
    auth: AuthContext = Depends(require_auth)
):
    """Search code semantically with caching."""
    verify_repo_access(request.repo_id, auth.user_id)
    
    # Validate query
    valid_query, query_error = InputValidator.validate_search_query(request.query)
    if not valid_query:
        raise HTTPException(status_code=400, detail=f"Invalid query: {query_error}")
    
    sanitized_query = InputValidator.sanitize_string(request.query, max_length=500)
    start_time = time.time()
    
    try:
        # Check cache
        cached_results = cache.get_search_results(sanitized_query, request.repo_id)
        if cached_results:
            duration = time.time() - start_time
            metrics.record_search(duration, cached=True)
            return {"results": cached_results, "count": len(cached_results), "cached": True}
        
        # Search
        results = await indexer.semantic_search(
            query=sanitized_query,
            repo_id=request.repo_id,
            max_results=min(request.max_results, 50),
            use_query_expansion=True,
            use_reranking=True
        )
        
        # Cache results
        cache.set_search_results(sanitized_query, request.repo_id, results, ttl=3600)
        
        duration = time.time() - start_time
        metrics.record_search(duration, cached=False)
        
        return {"results": results, "count": len(results), "cached": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explain")
async def explain_code(
    request: ExplainRequest,
    auth: AuthContext = Depends(require_auth)
):
    """Generate code explanation."""
    try:
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
