"""Repository management routes - CRUD and indexing."""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel
from typing import Optional
import hashlib
import time
import git

from dependencies import (
    indexer, repo_manager, metrics,
    get_repo_or_404, cost_controller
)
from services.input_validator import InputValidator
from middleware.auth import require_auth, AuthContext
from services.observability import logger, capture_exception

router = APIRouter(prefix="/repos", tags=["Repositories"])


class AddRepoRequest(BaseModel):
    name: str
    git_url: str
    branch: str = "main"


@router.get("")
async def list_repositories(auth: AuthContext = Depends(require_auth)):
    """List all repositories for authenticated user."""
    if not auth.user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    repos = repo_manager.list_repos_for_user(auth.user_id)
    return {"repositories": repos}


@router.post("")
async def add_repository(
    request: AddRepoRequest,
    auth: AuthContext = Depends(require_auth)
):
    """Add a new repository with validation and cost controls."""
    user_id = auth.user_id or auth.identifier
    
    # Validate inputs
    valid_name, name_error = InputValidator.validate_repo_name(request.name)
    if not valid_name:
        raise HTTPException(status_code=400, detail=f"Invalid repository name: {name_error}")
    
    valid_url, url_error = InputValidator.validate_git_url(request.git_url)
    if not valid_url:
        raise HTTPException(status_code=400, detail=f"Invalid Git URL: {url_error}")
    
    # Check repo limit
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
        
        # Check repo size
        can_index, size_error = cost_controller.check_repo_size_limit(repo["local_path"])
        if not can_index:
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


@router.post("/{repo_id}/index")
async def index_repository(
    repo_id: str,
    incremental: bool = True,
    auth: AuthContext = Depends(require_auth)
):
    """Trigger indexing for a repository."""
    start_time = time.time()
    
    try:
        repo = get_repo_or_404(repo_id, auth.user_id)
        repo_manager.update_status(repo_id, "indexing")
        
        # Check for incremental
        last_commit = repo_manager.get_last_indexed_commit(repo_id)
        
        if incremental and last_commit:
            logger.info("Using INCREMENTAL indexing", repo_id=repo_id, last_commit=last_commit[:8])
            total_functions = await indexer.incremental_index_repository(
                repo_id,
                repo["local_path"],
                last_commit
            )
            index_type = "incremental"
        else:
            logger.info("Using FULL indexing", repo_id=repo_id)
            total_functions = await indexer.index_repository(repo_id, repo["local_path"])
            index_type = "full"
        
        # Update metadata
        git_repo = git.Repo(repo["local_path"])
        current_commit = git_repo.head.commit.hexsha
        
        repo_manager.update_status(repo_id, "indexed")
        repo_manager.update_file_count(repo_id, total_functions)
        repo_manager.update_last_commit(repo_id, current_commit)
        
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


async def _authenticate_websocket(websocket: WebSocket) -> Optional[dict]:
    """Authenticate WebSocket via query parameter token."""
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


# Note: WebSocket routes need to be registered on the main app, not router
# This function is exported and called from main.py
async def websocket_index(websocket: WebSocket, repo_id: str):
    """Real-time repository indexing with progress updates."""
    user = await _authenticate_websocket(websocket)
    if not user:
        return
    
    user_id = user.get("user_id")
    if not user_id:
        await websocket.close(code=4001, reason="User ID required")
        return
    
    repo = repo_manager.get_repo_for_user(repo_id, user_id)
    if not repo:
        await websocket.close(code=4004, reason="Repository not found")
        return
    
    await websocket.accept()
    
    try:
        repo_manager.update_status(repo_id, "indexing")
        
        async def progress_callback(files_processed: int, functions_indexed: int, total_files: int):
            try:
                await websocket.send_json({
                    "type": "progress",
                    "files_processed": files_processed,
                    "functions_indexed": functions_indexed,
                    "total_files": total_files,
                    "progress_pct": int((files_processed / total_files) * 100) if total_files > 0 else 0
                })
            except Exception:
                pass
        
        total_functions = await indexer.index_repository_with_progress(
            repo_id,
            repo["local_path"],
            progress_callback
        )
        
        repo_manager.update_status(repo_id, "indexed")
        repo_manager.update_file_count(repo_id, total_functions)
        
        try:
            await websocket.send_json({
                "type": "complete",
                "total_functions": total_functions
            })
        except Exception:
            pass
        
    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected", repo_id=repo_id)
    except Exception as e:
        logger.error("WebSocket indexing error", repo_id=repo_id, error=str(e))
        capture_exception(e, operation="websocket_indexing", repo_id=repo_id)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
        repo_manager.update_status(repo_id, "error")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
