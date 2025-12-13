"""User routes - profile and usage information."""
from fastapi import APIRouter, Depends

from dependencies import user_limits
from middleware.auth import require_auth, AuthContext
from services.observability import logger
from services.user_limits import TIER_LIMITS, UserTier

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/usage")
def get_user_usage(auth: AuthContext = Depends(require_auth)):
    """
    Get current user's usage and limits.
    
    Returns:
        - tier: Current subscription tier
        - repositories: Current count and limit
        - limits: All tier limits
        - features: Available features for tier
    """
    user_id = auth.user_id
    
    if not user_id:
        logger.warning("Usage check without user_id", identifier=auth.identifier)
        # Return free tier defaults for API key users
        free_limits = TIER_LIMITS[UserTier.FREE]
        return {
            "tier": "free",
            "repositories": {
                "current": 0,
                "limit": free_limits.max_repos,
                "display": f"0/{free_limits.max_repos}"
            },
            "limits": {
                "max_files_per_repo": free_limits.max_files_per_repo,
                "max_functions_per_repo": free_limits.max_functions_per_repo,
                "playground_searches_per_day": free_limits.playground_searches_per_day,
            },
            "features": {
                "priority_indexing": free_limits.priority_indexing,
                "mcp_access": free_limits.mcp_access,
            }
        }
    
    usage = user_limits.get_usage_summary(user_id)
    logger.info("Usage retrieved", user_id=user_id, tier=usage.get("tier"))
    
    return usage


@router.get("/limits/check-repo-add")
def check_can_add_repo(auth: AuthContext = Depends(require_auth)):
    """
    Check if user can add another repository.
    
    Call this before showing "Add Repository" button to
    disable it if limit reached.
    """
    user_id = auth.user_id
    
    if not user_id:
        # API key users - return allowed with free tier info
        free_limits = TIER_LIMITS[UserTier.FREE]
        return {
            "allowed": True, 
            "message": "OK",
            "tier": "free",
            "limit": free_limits.max_repos
        }
    
    result = user_limits.check_repo_count(user_id)
    return result.to_dict()
