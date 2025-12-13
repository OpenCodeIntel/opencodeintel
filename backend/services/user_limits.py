"""
User Tier & Limits Service
Centralized system for managing user tiers and resource limits.

Tiers:
- free: Default tier for new users
- pro: Paid tier with higher limits
- enterprise: Custom limits for large organizations

Used by:
- #93: Playground rate limiting
- #94: Repo size limits
- #95: Repo count limits
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

from services.observability import logger, metrics


class UserTier(str, Enum):
    """User subscription tiers"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass(frozen=True)
class TierLimits:
    """Resource limits for a tier"""
    # Repository limits
    max_repos: Optional[int]  # None = unlimited
    max_files_per_repo: int
    max_functions_per_repo: int
    
    # Playground limits (anti-abuse, not business gate)
    playground_searches_per_day: Optional[int]  # None = unlimited
    
    # Future limits (placeholders)
    max_team_members: Optional[int] = None
    priority_indexing: bool = False
    mcp_access: bool = True


# Tier definitions
TIER_LIMITS: Dict[UserTier, TierLimits] = {
    UserTier.FREE: TierLimits(
        max_repos=3,
        max_files_per_repo=500,
        max_functions_per_repo=2000,
        playground_searches_per_day=50,  # Generous, anti-abuse only
        max_team_members=1,
        priority_indexing=False,
        mcp_access=True,
    ),
    UserTier.PRO: TierLimits(
        max_repos=20,
        max_files_per_repo=5000,
        max_functions_per_repo=20000,
        playground_searches_per_day=None,  # Unlimited
        max_team_members=10,
        priority_indexing=True,
        mcp_access=True,
    ),
    UserTier.ENTERPRISE: TierLimits(
        max_repos=None,  # Unlimited
        max_files_per_repo=50000,
        max_functions_per_repo=200000,
        playground_searches_per_day=None,
        max_team_members=None,
        priority_indexing=True,
        mcp_access=True,
    ),
}


@dataclass
class LimitCheckResult:
    """Result of a limit check"""
    allowed: bool
    current: int
    limit: Optional[int]
    message: str
    
    @property
    def limit_display(self) -> str:
        """Display limit as string (handles unlimited)"""
        return str(self.limit) if self.limit is not None else "∞"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "current": self.current,
            "limit": self.limit,
            "limit_display": self.limit_display,
            "message": self.message,
        }


class UserLimitsService:
    """
    Service for checking and enforcing user tier limits.
    
    Usage:
        limits = UserLimitsService(supabase_client, redis_client)
        
        # Check if user can add another repo
        result = await limits.check_repo_count(user_id)
        if not result.allowed:
            raise HTTPException(403, result.message)
        
        # Check if repo size is within limits
        result = await limits.check_repo_size(user_id, file_count, function_count)
        if not result.allowed:
            raise HTTPException(400, result.message)
    """
    
    def __init__(self, supabase_client, redis_client=None):
        self.supabase = supabase_client
        self.redis = redis_client
        self._tier_cache_ttl = 300  # Cache tier for 5 minutes
    
    # ===== TIER MANAGEMENT =====
    
    async def get_user_tier(self, user_id: str) -> UserTier:
        """
        Get user's current tier.
        
        Checks Redis cache first, then Supabase.
        Defaults to FREE if not found.
        """
        # Try cache first
        if self.redis:
            cache_key = f"user:tier:{user_id}"
            cached = self.redis.get(cache_key)
            if cached:
                try:
                    return UserTier(cached.decode() if isinstance(cached, bytes) else cached)
                except ValueError:
                    pass
        
        # Query Supabase
        tier = await self._get_tier_from_db(user_id)
        
        # Cache the result
        if self.redis:
            cache_key = f"user:tier:{user_id}"
            self.redis.setex(cache_key, self._tier_cache_ttl, tier.value)
        
        return tier
    
    async def _get_tier_from_db(self, user_id: str) -> UserTier:
        """Get tier from Supabase user_profiles table"""
        try:
            result = self.supabase.table("user_profiles").select("tier").eq("user_id", user_id).execute()
            
            if result.data and result.data[0].get("tier"):
                tier_value = result.data[0]["tier"]
                return UserTier(tier_value)
        except Exception as e:
            logger.warning("Failed to get user tier from DB", user_id=user_id, error=str(e))
        
        return UserTier.FREE
    
    def get_limits(self, tier: UserTier) -> TierLimits:
        """Get limits for a tier"""
        return TIER_LIMITS.get(tier, TIER_LIMITS[UserTier.FREE])
    
    async def get_user_limits(self, user_id: str) -> TierLimits:
        """Get limits for a specific user"""
        tier = await self.get_user_tier(user_id)
        return self.get_limits(tier)
    
    # ===== REPO COUNT LIMITS (#95) =====
    
    async def get_user_repo_count(self, user_id: str) -> int:
        """Get current repo count for user"""
        try:
            result = self.supabase.table("repositories").select("id", count="exact").eq("user_id", user_id).execute()
            return result.count or 0
        except Exception as e:
            logger.error("Failed to get repo count", user_id=user_id, error=str(e))
            return 0
    
    async def check_repo_count(self, user_id: str) -> LimitCheckResult:
        """
        Check if user can add another repository.
        
        Returns:
            LimitCheckResult with allowed=True if under limit
        """
        tier = await self.get_user_tier(user_id)
        limits = self.get_limits(tier)
        current_count = await self.get_user_repo_count(user_id)
        
        # Unlimited repos
        if limits.max_repos is None:
            return LimitCheckResult(
                allowed=True,
                current=current_count,
                limit=None,
                message=f"OK ({current_count}/∞ repos)"
            )
        
        # Check limit
        if current_count >= limits.max_repos:
            metrics.increment("user_limit_exceeded", tags={"limit": "repo_count", "tier": tier.value})
            logger.info("Repo count limit reached", user_id=user_id, current=current_count, limit=limits.max_repos)
            return LimitCheckResult(
                allowed=False,
                current=current_count,
                limit=limits.max_repos,
                message=f"Repository limit reached ({current_count}/{limits.max_repos}). Upgrade for more repos."
            )
        
        return LimitCheckResult(
            allowed=True,
            current=current_count,
            limit=limits.max_repos,
            message=f"OK ({current_count}/{limits.max_repos} repos)"
        )
    
    # ===== REPO SIZE LIMITS (#94) =====
    
    async def check_repo_size(
        self, 
        user_id: str, 
        file_count: int, 
        function_count: int
    ) -> LimitCheckResult:
        """
        Check if repo size is within user's tier limits.
        
        Args:
            user_id: The user attempting to index
            file_count: Number of code files in repo
            function_count: Number of functions/classes detected
        
        Returns:
            LimitCheckResult with allowed=True if within limits
        """
        tier = await self.get_user_tier(user_id)
        limits = self.get_limits(tier)
        
        # Check file count
        if file_count > limits.max_files_per_repo:
            metrics.increment("user_limit_exceeded", tags={"limit": "file_count", "tier": tier.value})
            logger.info(
                "Repo file count exceeds limit",
                user_id=user_id,
                file_count=file_count,
                limit=limits.max_files_per_repo
            )
            return LimitCheckResult(
                allowed=False,
                current=file_count,
                limit=limits.max_files_per_repo,
                message=f"Repository too large ({file_count:,} files). {tier.value.title()} tier allows up to {limits.max_files_per_repo:,} files."
            )
        
        # Check function count
        if function_count > limits.max_functions_per_repo:
            metrics.increment("user_limit_exceeded", tags={"limit": "function_count", "tier": tier.value})
            logger.info(
                "Repo function count exceeds limit",
                user_id=user_id,
                function_count=function_count,
                limit=limits.max_functions_per_repo
            )
            return LimitCheckResult(
                allowed=False,
                current=function_count,
                limit=limits.max_functions_per_repo,
                message=f"Repository has too many functions ({function_count:,}). {tier.value.title()} tier allows up to {limits.max_functions_per_repo:,} functions."
            )
        
        return LimitCheckResult(
            allowed=True,
            current=file_count,
            limit=limits.max_files_per_repo,
            message=f"OK ({file_count:,} files, {function_count:,} functions)"
        )
    
    # ===== PLAYGROUND RATE LIMITS (#93) =====
    
    def get_playground_limit(self, tier: UserTier = UserTier.FREE) -> Optional[int]:
        """Get playground search limit for tier"""
        return self.get_limits(tier).playground_searches_per_day
    
    # ===== USAGE SUMMARY =====
    
    async def get_usage_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get complete usage summary for user.
        Useful for dashboard display.
        """
        tier = await self.get_user_tier(user_id)
        limits = self.get_limits(tier)
        repo_count = await self.get_user_repo_count(user_id)
        
        return {
            "tier": tier.value,
            "repositories": {
                "current": repo_count,
                "limit": limits.max_repos,
                "display": f"{repo_count}/{limits.max_repos if limits.max_repos else '∞'}"
            },
            "limits": {
                "max_files_per_repo": limits.max_files_per_repo,
                "max_functions_per_repo": limits.max_functions_per_repo,
                "playground_searches_per_day": limits.playground_searches_per_day,
            },
            "features": {
                "priority_indexing": limits.priority_indexing,
                "mcp_access": limits.mcp_access,
            }
        }


# Singleton instance (initialized in dependencies.py)
_user_limits_service: Optional[UserLimitsService] = None


def get_user_limits_service() -> UserLimitsService:
    """Get or create UserLimitsService instance"""
    global _user_limits_service
    if _user_limits_service is None:
        raise RuntimeError("UserLimitsService not initialized. Call init_user_limits_service first.")
    return _user_limits_service


def init_user_limits_service(supabase_client, redis_client=None) -> UserLimitsService:
    """Initialize the UserLimitsService singleton"""
    global _user_limits_service
    _user_limits_service = UserLimitsService(supabase_client, redis_client)
    logger.info("UserLimitsService initialized")
    return _user_limits_service
