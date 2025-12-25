"""
Playground Rate Limiter & Session Manager
Redis-backed rate limiting and session management for anonymous playground.

Design:
- Layer 1: Session token (httpOnly cookie) - 50 searches/day per device
- Layer 2: IP-based fallback - 100 searches/day (for shared IPs)
- Layer 3: Global circuit breaker - 10,000 searches/hour (cost protection)

Session Data (Redis Hash):
- searches_used: Number of searches performed
- created_at: Session creation timestamp
- indexed_repo: JSON blob with indexed repo details (optional)

Part of #93 (rate limiting) and #127 (session management) implementation.
"""
import json
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

from services.observability import logger, metrics, track_time
from services.sentry import capture_exception


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PlaygroundLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    limit: int
    resets_at: datetime
    reason: Optional[str] = None
    session_token: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "remaining": self.remaining,
            "limit": self.limit,
            "resets_at": self.resets_at.isoformat(),
            "reason": self.reason,
        }


@dataclass
class IndexedRepoData:
    """
    Data about an indexed repository in a session.

    Stored as JSON in Redis hash field 'indexed_repo'.
    Used by #125 (indexing) and #128 (search) endpoints.
    """
    repo_id: str
    github_url: str
    name: str
    file_count: int
    indexed_at: str  # ISO format
    expires_at: str  # ISO format

    def to_dict(self) -> dict:
        return {
            "repo_id": self.repo_id,
            "github_url": self.github_url,
            "name": self.name,
            "file_count": self.file_count,
            "indexed_at": self.indexed_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IndexedRepoData":
        """Create from dictionary (parsed from Redis JSON)."""
        return cls(
            repo_id=data.get("repo_id", ""),
            github_url=data.get("github_url", ""),
            name=data.get("name", ""),
            file_count=data.get("file_count", 0),
            indexed_at=data.get("indexed_at", ""),
            expires_at=data.get("expires_at", ""),
        )

    def is_expired(self) -> bool:
        """Check if the indexed repo has expired."""
        try:
            expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) > expires
        except (ValueError, AttributeError):
            return True  # Treat parse errors as expired


@dataclass
class SessionData:
    """
    Complete session state for the /session endpoint.

    Returned by get_session_data() method.
    """
    session_id: Optional[str] = None
    searches_used: int = 0
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    indexed_repo: Optional[Dict[str, Any]] = None

    def to_response(self, limit: int) -> dict:
        """
        Convert to API response format.

        Matches the schema defined in issue #127.
        """
        return {
            "session_id": self._truncate_id(self.session_id) if self.session_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "indexed_repo": self.indexed_repo,
            "searches": {
                "used": self.searches_used,
                "limit": limit,
                "remaining": max(0, limit - self.searches_used),
            },
        }

    @staticmethod
    def _truncate_id(session_id: str) -> str:
        """Truncate session ID for display (security: don't expose full token)."""
        if len(session_id) > 12:
            return f"{session_id[:8]}..."
        return session_id


# =============================================================================
# MAIN CLASS
# =============================================================================

class PlaygroundLimiter:
    """
    Redis-backed rate limiter and session manager for playground.

    Provides:
    - Rate limiting (searches per session/IP)
    - Session data management (indexed repos, search counts)
    - Global circuit breaker (cost protection)

    Usage:
        limiter = PlaygroundLimiter(redis_client)

        # Rate limiting
        result = limiter.check_and_record(session_token, client_ip)
        if not result.allowed:
            raise HTTPException(429, result.reason)

        # Session management (#127)
        session_data = limiter.get_session_data(session_token)
        limiter.set_indexed_repo(session_token, repo_data)
        has_repo = limiter.has_indexed_repo(session_token)
    """

    # -------------------------------------------------------------------------
    # Configuration
    # -------------------------------------------------------------------------

    # Rate limits
    SESSION_LIMIT_PER_DAY = 50      # Per device (generous for conversion)
    IP_LIMIT_PER_DAY = 100          # Per IP (higher for shared networks)
    GLOBAL_LIMIT_PER_HOUR = 10000   # Circuit breaker (cost protection)

    # Anonymous indexing limits (#114)
    ANON_MAX_FILES = 200            # Max files for anonymous indexing
    ANON_REPOS_PER_SESSION = 1      # Max repos per anonymous session

    # Redis key prefixes
    KEY_SESSION = "playground:session:"
    KEY_IP = "playground:ip:"
    KEY_GLOBAL = "playground:global:hourly"

    # Redis hash fields (for session data)
    FIELD_SEARCHES = "searches_used"
    FIELD_CREATED = "created_at"
    FIELD_INDEXED_REPO = "indexed_repo"

    # TTLs
    TTL_DAY = 86400      # 24 hours
    TTL_HOUR = 3600      # 1 hour

    def __init__(self, redis_client=None):
        """
        Initialize the limiter.

        Args:
            redis_client: Redis client instance. If None, limiter fails open
                         (allows all requests - useful for development).
        """
        self.redis = redis_client

    # -------------------------------------------------------------------------
    # Session Data Methods (#127)
    # -------------------------------------------------------------------------

    def get_session_data(self, session_token: Optional[str]) -> SessionData:
        """
        Get complete session data for display.

        Used by GET /playground/session endpoint.

        Args:
            session_token: The session token from cookie (can be None)

        Returns:
            SessionData with all session information

        Note:
            Returns empty SessionData if token is None or session doesn't exist.
            Does NOT create a new session - that's done by check_and_record().
        """
        if not session_token:
            logger.debug("get_session_data called with no token")
            return SessionData()

        if not self.redis:
            logger.warning("Redis unavailable in get_session_data")
            return SessionData(session_id=session_token)

        try:
            with track_time("session_data_get"):
                session_key = f"{self.KEY_SESSION}{session_token}"

                # Ensure we're reading from hash format (handles legacy migration)
                self._ensure_hash_format(session_token)

                # Get all session fields
                raw_data = self.redis.hgetall(session_key)

                if not raw_data:
                    logger.debug("Session not found", session_token=session_token[:8])
                    return SessionData()

                # Parse the data (handle bytes from Redis)
                data = self._decode_hash_data(raw_data)

                # Get TTL for expires_at calculation
                ttl = self.redis.ttl(session_key)
                expires_at = None
                if ttl and ttl > 0:
                    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

                # Parse created_at
                created_at = None
                if data.get(self.FIELD_CREATED):
                    try:
                        created_str = data[self.FIELD_CREATED].replace("Z", "+00:00")
                        created_at = datetime.fromisoformat(created_str)
                    except (ValueError, AttributeError):
                        pass

                # Parse indexed_repo JSON
                indexed_repo = None
                if data.get(self.FIELD_INDEXED_REPO):
                    try:
                        indexed_repo = json.loads(data[self.FIELD_INDEXED_REPO])
                    except (json.JSONDecodeError, TypeError):
                        logger.warning("Failed to parse indexed_repo JSON",
                                       session_token=session_token[:8])

                # Build response
                session_data = SessionData(
                    session_id=session_token,
                    searches_used=int(data.get(self.FIELD_SEARCHES, 0)),
                    created_at=created_at,
                    expires_at=expires_at,
                    indexed_repo=indexed_repo,
                )

                metrics.increment("session_data_retrieved")
                logger.debug("Session data retrieved",
                             session_token=session_token[:8],
                             searches_used=session_data.searches_used,
                             has_repo=indexed_repo is not None)

                return session_data

        except Exception as e:
            logger.error("Failed to get session data",
                         error=str(e),
                         session_token=session_token[:8] if session_token else None)
            capture_exception(e, operation="get_session_data")
            return SessionData(session_id=session_token)

    def set_indexed_repo(self, session_token: str, repo_data: dict) -> bool:
        """
        Store indexed repository info in session.

        Called by POST /playground/index endpoint (#125) after successful indexing.

        Args:
            session_token: The session token
            repo_data: Dictionary with repo info (repo_id, github_url, name, etc.)

        Returns:
            True if successful, False otherwise

        Note:
            - Overwrites any existing indexed_repo
            - Does not affect searches_used count
            - repo_data should include: repo_id, github_url, name, file_count,
              indexed_at, expires_at
        """
        if not session_token:
            logger.warning("set_indexed_repo called with no token")
            return False

        if not self.redis:
            logger.warning("Redis unavailable in set_indexed_repo")
            return False

        try:
            with track_time("session_repo_set"):
                session_key = f"{self.KEY_SESSION}{session_token}"

                # Ensure hash format exists
                self._ensure_hash_format(session_token)

                # Serialize repo data to JSON
                repo_json = json.dumps(repo_data)

                # Store in hash (preserves other fields like searches_used)
                self.redis.hset(session_key, self.FIELD_INDEXED_REPO, repo_json)

                metrics.increment("session_repo_indexed")
                logger.info("Indexed repo stored in session",
                            session_token=session_token[:8],
                            repo_id=repo_data.get("repo_id"),
                            repo_name=repo_data.get("name"))

                return True

        except Exception as e:
            logger.error("Failed to set indexed repo",
                         error=str(e),
                         session_token=session_token[:8])
            capture_exception(e, operation="set_indexed_repo")
            return False

    def has_indexed_repo(self, session_token: str) -> bool:
        """
        Check if session already has an indexed repository.

        Used by POST /playground/index endpoint (#125) to enforce
        1 repo per session limit.

        Args:
            session_token: The session token

        Returns:
            True if session has an indexed repo, False otherwise
        """
        if not session_token or not self.redis:
            return False

        try:
            session_key = f"{self.KEY_SESSION}{session_token}"

            # Check if indexed_repo field exists in hash
            exists = self.redis.hexists(session_key, self.FIELD_INDEXED_REPO)

            logger.debug("Checked for indexed repo",
                         session_token=session_token[:8],
                         has_repo=exists)

            return bool(exists)

        except Exception as e:
            logger.error("Failed to check indexed repo",
                         error=str(e),
                         session_token=session_token[:8])
            capture_exception(e, operation="has_indexed_repo")
            return False

    def clear_indexed_repo(self, session_token: str) -> bool:
        """
        Remove indexed repository from session.

        Useful for cleanup or allowing user to index a different repo.

        Args:
            session_token: The session token

        Returns:
            True if successful, False otherwise
        """
        if not session_token or not self.redis:
            return False

        try:
            session_key = f"{self.KEY_SESSION}{session_token}"
            self.redis.hdel(session_key, self.FIELD_INDEXED_REPO)

            logger.info("Cleared indexed repo from session",
                        session_token=session_token[:8])
            metrics.increment("session_repo_cleared")

            return True

        except Exception as e:
            logger.error("Failed to clear indexed repo",
                         error=str(e),
                         session_token=session_token[:8])
            capture_exception(e, operation="clear_indexed_repo")
            return False

    def create_session(self, session_token: str) -> bool:
        """
        Create a new session with initial data.

        Args:
            session_token: The session token to create

        Returns:
            True if successful, False otherwise
        """
        if not session_token or not self.redis:
            return False

        try:
            session_key = f"{self.KEY_SESSION}{session_token}"
            now = datetime.now(timezone.utc).isoformat()

            # Create hash with initial values
            self.redis.hset(session_key, mapping={
                self.FIELD_SEARCHES: "0",
                self.FIELD_CREATED: now,
            })
            self.redis.expire(session_key, self.TTL_DAY)

            logger.info("Created new session", session_token=session_token[:8])
            metrics.increment("session_created")

            return True

        except Exception as e:
            logger.error("Failed to create session",
                         error=str(e),
                         session_token=session_token[:8])
            capture_exception(e, operation="create_session")
            return False

    # -------------------------------------------------------------------------
    # Rate Limiting Methods (existing, updated for hash storage)
    # -------------------------------------------------------------------------

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
        3. IP-based limit (fallback for new sessions)
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
                metrics.increment("rate_limit_global_blocked")
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
                    if record:
                        metrics.increment("search_recorded")
                    return PlaygroundLimitResult(
                        allowed=True,
                        remaining=session_remaining,
                        limit=self.SESSION_LIMIT_PER_DAY,
                        resets_at=resets_at,
                    )
                else:
                    # Session exhausted
                    metrics.increment("rate_limit_session_blocked")
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
                metrics.increment("rate_limit_ip_blocked")
                return PlaygroundLimitResult(
                    allowed=False,
                    remaining=0,
                    limit=self.SESSION_LIMIT_PER_DAY,
                    resets_at=resets_at,
                    reason="Daily limit reached. Sign up for unlimited searches!",
                )

            # New session allowed - initialize it
            if record:
                self._init_new_session(new_session_token)
                metrics.increment("search_recorded")

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
        """Check global circuit breaker."""
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
        """
        Check session-based limit using Redis Hash.

        Updated for #127 to use hash storage instead of simple strings.
        """
        try:
            session_key = f"{self.KEY_SESSION}{session_token}"

            # Ensure hash format (handles legacy string migration)
            self._ensure_hash_format(session_token)

            if record:
                # Atomically increment searches_used field
                count = self.redis.hincrby(session_key, self.FIELD_SEARCHES, 1)

                # Set TTL on first search (if not already set)
                if count == 1:
                    now = datetime.now(timezone.utc).isoformat()
                    self.redis.hset(session_key, self.FIELD_CREATED, now)
                    self.redis.expire(session_key, self.TTL_DAY)
            else:
                # Just read current count
                count_str = self.redis.hget(session_key, self.FIELD_SEARCHES)
                count = int(count_str) if count_str else 0

            remaining = max(0, self.SESSION_LIMIT_PER_DAY - count)
            allowed = count <= self.SESSION_LIMIT_PER_DAY
            return allowed, remaining

        except Exception as e:
            logger.error("Session limit check failed", error=str(e))
            return True, self.SESSION_LIMIT_PER_DAY  # Fail open

    def _check_ip_limit(self, client_ip: str, record: bool) -> Tuple[bool, int]:
        """Check IP-based limit."""
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

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _get_midnight_utc(self) -> datetime:
        """Get next midnight UTC for reset time."""
        now = datetime.now(timezone.utc)
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if tomorrow <= now:
            tomorrow += timedelta(days=1)
        return tomorrow

    def _hash_ip(self, ip: str) -> str:
        """Hash IP for privacy."""
        return hashlib.sha256(ip.encode()).hexdigest()[:16]

    def _generate_session_token(self) -> str:
        """Generate secure session token."""
        return secrets.token_urlsafe(32)

    def _ensure_hash_format(self, session_token: str) -> None:
        """
        Ensure session data is in hash format.

        Handles migration from legacy string format (just a counter)
        to new hash format (searches_used + created_at + indexed_repo).

        This is called before any hash operations to maintain
        backward compatibility with existing sessions.
        """
        session_key = f"{self.KEY_SESSION}{session_token}"

        try:
            key_type = self.redis.type(session_key)

            # Handle bytes response from some Redis clients
            if isinstance(key_type, bytes):
                key_type = key_type.decode('utf-8')

            if key_type == 'string':
                # Legacy format - migrate to hash
                logger.info("Migrating legacy session to hash format",
                            session_token=session_token[:8])

                # Read old count
                old_count = self.redis.get(session_key)
                count = int(old_count) if old_count else 0

                # Get TTL before delete
                ttl = self.redis.ttl(session_key)

                # Delete old string key
                self.redis.delete(session_key)

                # Create new hash with migrated data
                now = datetime.now(timezone.utc).isoformat()
                self.redis.hset(session_key, mapping={
                    self.FIELD_SEARCHES: str(count),
                    self.FIELD_CREATED: now,
                })

                # Restore TTL
                if ttl and ttl > 0:
                    self.redis.expire(session_key, ttl)

                metrics.increment("session_migrated")
                logger.info("Session migrated successfully",
                            session_token=session_token[:8],
                            searches_migrated=count)

        except Exception as e:
            # Don't fail the operation, just log
            logger.warning("Session format check failed",
                           error=str(e),
                           session_token=session_token[:8])

    def _init_new_session(self, session_token: str) -> None:
        """
        Initialize a new session with hash structure.

        Called when creating a new session on first search.
        """
        session_key = f"{self.KEY_SESSION}{session_token}"
        now = datetime.now(timezone.utc).isoformat()

        self.redis.hset(session_key, mapping={
            self.FIELD_SEARCHES: "1",  # First search
            self.FIELD_CREATED: now,
        })
        self.redis.expire(session_key, self.TTL_DAY)

        metrics.increment("session_created")
        logger.debug("New session initialized", session_token=session_token[:8])

    def _decode_hash_data(self, raw_data: dict) -> dict:
        """
        Decode Redis hash data (handles bytes from some Redis clients).

        Args:
            raw_data: Raw data from redis.hgetall()

        Returns:
            Dictionary with string keys and values
        """
        decoded = {}
        for key, value in raw_data.items():
            # Decode key if bytes
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            # Decode value if bytes
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            decoded[key] = value
        return decoded

    def get_usage_stats(self) -> dict:
        """Get current global usage stats (for monitoring)."""
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


# =============================================================================
# SINGLETON
# =============================================================================

_playground_limiter: Optional[PlaygroundLimiter] = None


def get_playground_limiter(redis_client=None) -> PlaygroundLimiter:
    """Get or create PlaygroundLimiter instance."""
    global _playground_limiter
    if _playground_limiter is None:
        _playground_limiter = PlaygroundLimiter(redis_client)
    return _playground_limiter
