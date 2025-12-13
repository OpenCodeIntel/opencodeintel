"""
Playground Rate Limiter
Redis-backed rate limiting for anonymous playground searches.

Design:
- Layer 1: Session token (httpOnly cookie) - 50 searches/day per device
- Layer 2: IP-based fallback - 100 searches/day (for shared IPs)
- Layer 3: Global circuit breaker - 10,000 searches/hour (cost protection)

Part of #93 implementation.
"""
import secrets
import hashlib
from datetime import datetime, timezone
from typing import Optional, Tuple
from dataclasses import dataclass

from services.observability import logger
from services.sentry import capture_exception


@dataclass
class PlaygroundLimitResult:
    """Result of a rate limit check"""
    allowed: bool
    remaining: int
    limit: int
    resets_at: datetime
    reason: Optional[str] = None  # Why blocked (if not allowed)
    session_token: Optional[str] = None  # New token if created
    
    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "remaining": self.remaining,
            "limit": self.limit,
            "resets_at": self.resets_at.isoformat(),
            "reason": self.reason,
        }


class PlaygroundLimiter:
    """
    Redis-backed rate limiter for playground searches.
    
    Usage:
        limiter = PlaygroundLimiter(redis_client)
        
        # Check before search
        result = limiter.check_and_record(session_token, client_ip)
        if not result.allowed:
            raise HTTPException(429, result.reason)
        
        # Set cookie if new session
        if result.session_token:
            response.set_cookie("pg_session", result.session_token, ...)
    """
    
    # Limits
    SESSION_LIMIT_PER_DAY = 50      # Per device (generous for conversion)
    IP_LIMIT_PER_DAY = 100          # Per IP (higher for shared networks)
    GLOBAL_LIMIT_PER_HOUR = 10000   # Circuit breaker (cost protection)
    
    # Redis key prefixes
    KEY_SESSION = "playground:session:"
    KEY_IP = "playground:ip:"
    KEY_GLOBAL = "playground:global:hourly"
    
    # TTLs
    TTL_DAY = 86400      # 24 hours
    TTL_HOUR = 3600      # 1 hour
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
    
    def _get_midnight_utc(self) -> datetime:
        """Get next midnight UTC for reset time"""
        now = datetime.now(timezone.utc)
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if tomorrow <= now:
            from datetime import timedelta
            tomorrow += timedelta(days=1)
        return tomorrow
    
    def _hash_ip(self, ip: str) -> str:
        """Hash IP for privacy"""
        return hashlib.sha256(ip.encode()).hexdigest()[:16]
    
    def _generate_session_token(self) -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(32)
    
    def check_limit(
        self, 
        session_token: Optional[str], 
        client_ip: str
    ) -> PlaygroundLimitResult:
        """
        Check rate limit without recording a search.
        Use this for GET /playground/limits endpoint.
        """
        return self._check_limits(session_token, client_ip, record=False)
    
    def check_and_record(
        self, 
        session_token: Optional[str], 
        client_ip: str
    ) -> PlaygroundLimitResult:
        """
        Check rate limit AND record a search if allowed.
        Use this for POST /playground/search endpoint.
        """
        return self._check_limits(session_token, client_ip, record=True)
    
    def _check_limits(
        self, 
        session_token: Optional[str], 
        client_ip: str,
        record: bool = False
    ) -> PlaygroundLimitResult:
        """
        Internal method to check all rate limit layers.
        
        Order of checks:
        1. Global circuit breaker (protects cost)
        2. Session-based limit (primary)
        3. IP-based limit (fallback)
        """
        resets_at = self._get_midnight_utc()
        new_session_token = None
        
        # If no Redis, fail OPEN (allow all)
        if not self.redis:
            logger.warning("Redis not available, allowing playground search")
            return PlaygroundLimitResult(
                allowed=True,
                remaining=self.SESSION_LIMIT_PER_DAY,
                limit=self.SESSION_LIMIT_PER_DAY,
                resets_at=resets_at,
            )
        
        try:
            # Layer 1: Global circuit breaker
            global_allowed, global_count = self._check_global_limit(record)
            if not global_allowed:
                logger.warning("Global circuit breaker triggered", count=global_count)
                return PlaygroundLimitResult(
                    allowed=False,
                    remaining=0,
                    limit=self.SESSION_LIMIT_PER_DAY,
                    resets_at=resets_at,
                    reason="Service is experiencing high demand. Please try again later.",
                )
            
            # Layer 2: Session-based limit (primary)
            if session_token:
                session_allowed, session_remaining = self._check_session_limit(
                    session_token, record
                )
                if session_allowed:
                    return PlaygroundLimitResult(
                        allowed=True,
                        remaining=session_remaining,
                        limit=self.SESSION_LIMIT_PER_DAY,
                        resets_at=resets_at,
                    )
                else:
                    # Session exhausted
                    return PlaygroundLimitResult(
                        allowed=False,
                        remaining=0,
                        limit=self.SESSION_LIMIT_PER_DAY,
                        resets_at=resets_at,
                        reason="Daily limit reached. Sign up for unlimited searches!",
                    )
            
            # No session token - create new one and check IP
            new_session_token = self._generate_session_token()
            
            # Layer 3: IP-based limit (for new sessions / fallback)
            ip_allowed, ip_remaining = self._check_ip_limit(client_ip, record)
            if not ip_allowed:
                # IP exhausted (likely abuse or shared network)
                return PlaygroundLimitResult(
                    allowed=False,
                    remaining=0,
                    limit=self.SESSION_LIMIT_PER_DAY,
                    resets_at=resets_at,
                    reason="Daily limit reached. Sign up for unlimited searches!",
                )
            
            # New session allowed
            if record:
                # Initialize session counter
                session_key = f"{self.KEY_SESSION}{new_session_token}"
                self.redis.set(session_key, "1", ex=self.TTL_DAY)
            
            return PlaygroundLimitResult(
                allowed=True,
                remaining=self.SESSION_LIMIT_PER_DAY - 1 if record else self.SESSION_LIMIT_PER_DAY,
                limit=self.SESSION_LIMIT_PER_DAY,
                resets_at=resets_at,
                session_token=new_session_token,
            )
            
        except Exception as e:
            logger.error("Playground rate limit check failed", error=str(e))
            capture_exception(e)
            # Fail OPEN - allow search but don't break UX
            return PlaygroundLimitResult(
                allowed=True,
                remaining=self.SESSION_LIMIT_PER_DAY,
                limit=self.SESSION_LIMIT_PER_DAY,
                resets_at=resets_at,
            )
    
    def _check_global_limit(self, record: bool) -> Tuple[bool, int]:
        """Check global circuit breaker"""
        try:
            if record:
                count = self.redis.incr(self.KEY_GLOBAL)
                if count == 1:
                    self.redis.expire(self.KEY_GLOBAL, self.TTL_HOUR)
            else:
                count = int(self.redis.get(self.KEY_GLOBAL) or 0)
            
            allowed = count <= self.GLOBAL_LIMIT_PER_HOUR
            return allowed, count
        except Exception as e:
            logger.error("Global limit check failed", error=str(e))
            return True, 0  # Fail open
    
    def _check_session_limit(
        self, 
        session_token: str, 
        record: bool
    ) -> Tuple[bool, int]:
        """Check session-based limit"""
        try:
            session_key = f"{self.KEY_SESSION}{session_token}"
            
            if record:
                count = self.redis.incr(session_key)
                if count == 1:
                    self.redis.expire(session_key, self.TTL_DAY)
            else:
                count = int(self.redis.get(session_key) or 0)
            
            remaining = max(0, self.SESSION_LIMIT_PER_DAY - count)
            allowed = count <= self.SESSION_LIMIT_PER_DAY
            return allowed, remaining
        except Exception as e:
            logger.error("Session limit check failed", error=str(e))
            return True, self.SESSION_LIMIT_PER_DAY  # Fail open
    
    def _check_ip_limit(self, client_ip: str, record: bool) -> Tuple[bool, int]:
        """Check IP-based limit"""
        try:
            ip_hash = self._hash_ip(client_ip)
            ip_key = f"{self.KEY_IP}{ip_hash}"
            
            if record:
                count = self.redis.incr(ip_key)
                if count == 1:
                    self.redis.expire(ip_key, self.TTL_DAY)
            else:
                count = int(self.redis.get(ip_key) or 0)
            
            remaining = max(0, self.IP_LIMIT_PER_DAY - count)
            allowed = count <= self.IP_LIMIT_PER_DAY
            return allowed, remaining
        except Exception as e:
            logger.error("IP limit check failed", error=str(e))
            return True, self.IP_LIMIT_PER_DAY  # Fail open
    
    def get_usage_stats(self) -> dict:
        """Get current global usage stats (for monitoring)"""
        if not self.redis:
            return {"global_hourly": 0, "redis_available": False}
        
        try:
            global_count = int(self.redis.get(self.KEY_GLOBAL) or 0)
            return {
                "global_hourly": global_count,
                "global_limit": self.GLOBAL_LIMIT_PER_HOUR,
                "redis_available": True,
            }
        except Exception as e:
            return {"error": str(e), "redis_available": False}


# Singleton instance
_playground_limiter: Optional[PlaygroundLimiter] = None


def get_playground_limiter(redis_client=None) -> PlaygroundLimiter:
    """Get or create PlaygroundLimiter instance"""
    global _playground_limiter
    if _playground_limiter is None:
        _playground_limiter = PlaygroundLimiter(redis_client)
    return _playground_limiter
