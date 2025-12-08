"""Analysis routes - dependencies, impact, insights, style."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from dependencies import (
    dependency_analyzer, style_analyzer,
    get_repo_or_404
)
from services.input_validator import InputValidator
from middleware.auth import require_auth, AuthContext

router = APIRouter(prefix="/repos", tags=["Analysis"])


class ImpactRequest(BaseModel):
    repo_id: str
    file_path: str


@router.get("/{repo_id}/dependencies")
async def get_dependency_graph(
    repo_id: str,
    auth: AuthContext = Depends(require_auth)
):
    """Get dependency graph for repository."""
    try:
        repo = get_repo_or_404(repo_id, auth.user_id)
        
        # Try cache first
        cached_graph = dependency_analyzer.load_from_cache(repo_id)
        if cached_graph:
            print(f"✅ Using cached dependency graph for {repo_id}")
            return {**cached_graph, "cached": True}
        
        # Build fresh
        print(f"🔄 Building fresh dependency graph for {repo_id}")
        graph_data = dependency_analyzer.build_dependency_graph(repo["local_path"])
        dependency_analyzer.save_to_cache(repo_id, graph_data)
        
        return {**graph_data, "cached": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{repo_id}/impact")
async def analyze_impact(
    repo_id: str,
    request: ImpactRequest,
    auth: AuthContext = Depends(require_auth)
):
    """Analyze impact of changing a file."""
    try:
        repo = get_repo_or_404(repo_id, auth.user_id)
        
        # Validate file path
        valid_path, path_error = InputValidator.validate_file_path(
            request.file_path, repo["local_path"]
        )
        if not valid_path:
            raise HTTPException(status_code=400, detail=f"Invalid file path: {path_error}")
        
        # Get or build graph
        graph_data = dependency_analyzer.load_from_cache(repo_id)
        if not graph_data:
            print(f"🔄 Building dependency graph for impact analysis")
            graph_data = dependency_analyzer.build_dependency_graph(repo["local_path"])
            dependency_analyzer.save_to_cache(repo_id, graph_data)
        
        impact = dependency_analyzer.get_file_impact(
            repo["local_path"],
            request.file_path,
            graph_data
        )
        
        return impact
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{repo_id}/insights")
async def get_repository_insights(
    repo_id: str,
    auth: AuthContext = Depends(require_auth)
):
    """Get comprehensive insights about repository."""
    try:
        repo = get_repo_or_404(repo_id, auth.user_id)
        
        # Get or build graph
        graph_data = dependency_analyzer.load_from_cache(repo_id)
        if not graph_data:
            print(f"🔄 Building dependency graph for insights")
            graph_data = dependency_analyzer.build_dependency_graph(repo["local_path"])
            dependency_analyzer.save_to_cache(repo_id, graph_data)
        
        return {
            "repo_id": repo_id,
            "name": repo["name"],
            "graph_metrics": graph_data.get("metrics", {}),
            "total_files": len(graph_data.get("dependencies", {})),
            "total_dependencies": sum(
                len(deps) for deps in graph_data.get("dependencies", {}).values()
            ),
            "status": repo["status"],
            "functions_indexed": repo["file_count"],
            "cached": bool(graph_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{repo_id}/style-analysis")
async def get_style_analysis(
    repo_id: str,
    auth: AuthContext = Depends(require_auth)
):
    """Analyze code style and team patterns."""
    try:
        repo = get_repo_or_404(repo_id, auth.user_id)
        
        # Try cache first
        cached_style = style_analyzer.load_from_cache(repo_id)
        if cached_style:
            print(f"✅ Using cached code style for {repo_id}")
            return {**cached_style, "cached": True}
        
        # Analyze fresh
        print(f"🔄 Analyzing code style for {repo_id}")
        style_data = style_analyzer.analyze_repository_style(repo["local_path"])
        style_analyzer.save_to_cache(repo_id, style_data)
        
        return {**style_data, "cached": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
