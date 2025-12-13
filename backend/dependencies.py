"""
Shared dependencies and service instances.
All route modules import from here to avoid circular imports.
"""
from fastapi import HTTPException, Depends
from dotenv import load_dotenv

# Load env vars first
load_dotenv()

from services.indexer_optimized import OptimizedCodeIndexer
from services.repo_manager import RepositoryManager
from services.cache import CacheService
from services.dependency_analyzer import DependencyAnalyzer
from services.style_analyzer import StyleAnalyzer
from services.performance_metrics import PerformanceMetrics
from services.rate_limiter import RateLimiter, APIKeyManager
from services.supabase_service import get_supabase_service
from services.input_validator import InputValidator, CostController
from services.user_limits import init_user_limits_service, get_user_limits_service

# Service instances (singleton pattern)
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

# User tier and limits management
user_limits = init_user_limits_service(
    supabase_client=get_supabase_service().client,
    redis_client=cache.redis if cache.redis else None
)


def get_repo_or_404(repo_id: str, user_id: str) -> dict:
    """
    Get repository with ownership verification.
    Returns 404 if not found or user doesn't own it.
    """
    repo = repo_manager.get_repo_for_user(repo_id, user_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


def verify_repo_access(repo_id: str, user_id: str) -> None:
    """
    Verify user has access to repository.
    Raises 404 if no access.
    """
    if not repo_manager.verify_ownership(repo_id, user_id):
        raise HTTPException(status_code=404, detail="Repository not found")
