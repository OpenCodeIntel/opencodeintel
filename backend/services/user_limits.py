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
from services.sentry import capture_exception


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


# Tier definitions - Single source of truth
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
    tier: str = "free"  # Include tier for frontend upgrade prompts
    error_code: Optional[str] = None  # e.g., "REPO_LIMIT_REACHED"
    
    @property
    def limit_display(self) -> str:
        """Display limit as string (handles unlimited)"""
        return str(self.limit) if self.limit is not None else "unlimited"
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "allowed": self.allowed,
            "current": self.current,
            "limit": self.limit,
            "limit_display": self.limit_display,
            "message": self.message,
            "tier": self.tier,
        }
        if self.error_code:
            result["error_code"] = self.error_code
        return result


class LimitCheckError(Exception):
    """Raised when limit check fails due to system error (not limit exceeded)"""
    pass


class UserLimitsService:
    """
    Service for checking and enforcing user tier limits.
    
    Usage:
        limits = UserLimitsService(supabase_client, redis_client)
        
        # Check if user can add another repo
        result = limits.check_repo_count(user_id)
        if not result.allowed:
            raise HTTPException(403, result.to_dict())
        
        # Check if repo size is within limits
        result = limits.check_repo_size(user_id, file_count, function_count)
        if not result.allowed:
            raise HTTPException(400, result.to_dict())
    """
    
    def __init__(self, supabase_client, redis_client=None):
        self.supabase = supabase_client
        self.redis = redis_client
        self._tier_cache_ttl = 300  # Cache tier for 5 minutes
    
    def _validate_user_id(self, user_id: str) -> bool:
        """Validate user_id is not empty"""
        if not user_id or not isinstance(user_id, str) or not user_id.strip():
            return False
        return True
    
    # ===== TIER MANAGEMENT =====
    
    def get_user_tier(self, user_id: str) -> UserTier:
        """
        Get user's current tier.
        
        Checks Redis cache first, then Supabase.
        Defaults to FREE if not found.
        """
        if not self._validate_user_id(user_id):
            logger.warning("Invalid user_id provided to get_user_tier", user_id=user_id)
            return UserTier.FREE
        
        # Try cache first
        if self.redis:
            try:
                cache_key = f"user:tier:{user_id}"
                cached = self.redis.get(cache_key)
                if cached:
                    tier_value = cached.decode() if isinstance(cached, bytes) else cached
                    return UserTier(tier_value)
            except Exception as e:
                logger.warning("Redis cache read failed", error=str(e))
                # Continue to DB lookup
        
        # Query Supabase
        tier = self._get_tier_from_db(user_id)
        
        # Cache the result
        if self.redis:
            try:
                cache_key = f"user:tier:{user_id}"
                self.redis.setex(cache_key, self._tier_cache_ttl, tier.value)
            except Exception as e:
                logger.warning("Redis cache write failed", error=str(e))
        
        return tier
    
    def _get_tier_from_db(self, user_id: str) -> UserTier:
        """Get tier from Supabase user_profiles table"""
        try:
            result = self.supabase.table("user_profiles").select("tier").eq("user_id", user_id).execute()
            
            if result.data and result.data[0].get("tier"):
                tier_value = result.data[0]["tier"]
                return UserTier(tier_value)
        except Exception as e:
            logger.warning("Failed to get user tier from DB", user_id=user_id, error=str(e))
            capture_exception(e)
        
        # Default to FREE - this is safe because FREE has the most restrictive limits
        return UserTier.FREE
    
    def get_limits(self, tier: UserTier) -> TierLimits:
        """Get limits for a tier"""
        return TIER_LIMITS.get(tier, TIER_LIMITS[UserTier.FREE])
    
    def get_user_limits(self, user_id: str) -> TierLimits:
        """Get limits for a specific user"""
        tier = self.get_user_tier(user_id)
        return self.get_limits(tier)
    
    def invalidate_tier_cache(self, user_id: str) -> None:
        """Invalidate cached tier (call after tier upgrade)"""
        if self.redis and self._validate_user_id(user_id):
            try:
                cache_key = f"user:tier:{user_id}"
                self.redis.delete(cache_key)
                logger.info("Tier cache invalidated", user_id=user_id)
            except Exception as e:
                logger.warning("Failed to invalidate tier cache", error=str(e))
    
    # ===== REPO COUNT LIMITS (#95) =====
    
    def get_user_repo_count(self, user_id: str, raise_on_error: bool = False) -> int:
        """
        Get current repo count for user.
        
        Args:
            user_id: The user ID
            raise_on_error: If True, raise LimitCheckError on DB failure
                           If False, return 0 (fail-open for reads, fail-closed for writes)
        """
        if not self._validate_user_id(user_id):
            return 0
            
        try:
            result = self.supabase.table("repositories").select("id", count="exact").eq("user_id", user_id).execute()
            return result.count or 0
        except Exception as e:
            logger.error("Failed to get repo count", user_id=user_id, error=str(e))
            capture_exception(e)
            if raise_on_error:
                raise LimitCheckError(f"Failed to check repository count: {str(e)}")
            return 0
    
    def check_repo_count(self, user_id: str) -> LimitCheckResult:
        """
        Check if user can add another repository.
        
        Returns:
            LimitCheckResult with allowed=True if under limit
        
        Note: Fails CLOSED - if we can't check, we don't allow.
        """
        if not self._validate_user_id(user_id):
            return LimitCheckResult(
                allowed=False,
                current=0,
                limit=0,
                message="Invalid user ID",
                tier="unknown",
                error_code="INVALID_USER"
            )
        
        tier = self.get_user_tier(user_id)
        limits = self.get_limits(tier)
        
        try:
            current_count = self.get_user_repo_count(user_id, raise_on_error=True)
        except LimitCheckError as e:
            # Fail CLOSED - don't allow if we can't verify
            return LimitCheckResult(
                allowed=False,
                current=0,
                limit=limits.max_repos,
                message="Unable to verify repository limit. Please try again.",
                tier=tier.value,
                error_code="SYSTEM_ERROR"
            )
        
        # Unlimited repos
        if limits.max_repos is None:
            return LimitCheckResult(
                allowed=True,
                current=current_count,
                limit=None,
                message=f"OK ({current_count} repos)",
                tier=tier.value
            )
        
        # Check limit
        if current_count >= limits.max_repos:
            metrics.increment("user_limit_exceeded", tags={"limit": "repo_count", "tier": tier.value})
            logger.info("Repo count limit reached", user_id=user_id, current=current_count, limit=limits.max_repos)
            return LimitCheckResult(
                allowed=False,
                current=current_count,
                limit=limits.max_repos,
                message=f"Repository limit reached ({current_count}/{limits.max_repos}). Upgrade to add more repositories.",
                tier=tier.value,
                error_code="REPO_LIMIT_REACHED"
            )
        
        return LimitCheckResult(
            allowed=True,
            current=current_count,
            limit=limits.max_repos,
            message=f"OK ({current_count}/{limits.max_repos} repos)",
            tier=tier.value
        )
    
    # ===== REPO SIZE LIMITS (#94) =====
    
    def check_repo_size(
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
        if not self._validate_user_id(user_id):
            return LimitCheckResult(
                allowed=False,
                current=0,
                limit=0,
                message="Invalid user ID",
                tier="unknown",
                error_code="INVALID_USER"
            )
        
        tier = self.get_user_tier(user_id)
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
                message=f"Repository too large ({file_count:,} files). {tier.value.title()} tier allows up to {limits.max_files_per_repo:,} files.",
                tier=tier.value,
                error_code="REPO_TOO_LARGE"
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
                message=f"Repository has too many functions ({function_count:,}). {tier.value.title()} tier allows up to {limits.max_functions_per_repo:,} functions.",
                tier=tier.value,
                error_code="REPO_TOO_LARGE"
            )
        
        return LimitCheckResult(
            allowed=True,
            current=file_count,
            limit=limits.max_files_per_repo,
            message=f"OK ({file_count:,} files, {function_count:,} functions)",
            tier=tier.value
        )
    
    # ===== PLAYGROUND RATE LIMITS (#93) =====
    
    def get_playground_limit(self, tier: UserTier = UserTier.FREE) -> Optional[int]:
        """Get playground search limit for tier"""
        return self.get_limits(tier).playground_searches_per_day
    
    # ===== USAGE SUMMARY =====
    
    def get_usage_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get complete usage summary for user.
        Useful for dashboard display.
        """
        if not self._validate_user_id(user_id):
            # Return free tier defaults for invalid user
            limits = TIER_LIMITS[UserTier.FREE]
            return {
                "tier": "free",
                "repositories": {
                    "current": 0,
                    "limit": limits.max_repos,
                    "display": f"0/{limits.max_repos}"
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
        
        tier = self.get_user_tier(user_id)
        limits = self.get_limits(tier)
        repo_count = self.get_user_repo_count(user_id)
        
        return {
            "tier": tier.value,
            "repositories": {
                "current": repo_count,
                "limit": limits.max_repos,
                "display": f"{repo_count}/{limits.max_repos if limits.max_repos else 'unlimited'}"
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
