"""
Authentication Middleware for CodeIntel API

Supports three auth modes:
  1. JWT tokens (Supabase) - for web UI users
  2. API keys (ci_xxx) - for MCP/programmatic access  
  3. Public access - for demo endpoints (no auth required)

Usage:
    from middleware.auth import require_auth, public_auth, AuthContext

    @app.get("/api/repos")
    async def list_repos(auth: AuthContext = Depends(require_auth)):
        user_id = auth.user_id
        ...

    @app.get("/api/demo/search")
    async def demo_search(auth: AuthContext = Depends(public_auth)):
        # Works with or without auth
        ...
"""
from dataclasses import dataclass
from typing import Optional
import os
import hashlib

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials


# ---------------------------------------------------------------------------
# Auth Context - unified return type for all auth methods
# ---------------------------------------------------------------------------

@dataclass
class AuthContext:
    """Authentication context passed to route handlers"""
    user_id: Optional[str] = None      # Supabase user ID (JWT auth)
    email: Optional[str] = None        # User email (JWT auth)
    api_key_name: Optional[str] = None # API key name (key auth)
    tier: str = "free"                 # Rate limit tier
    is_public: bool = False            # True for unauthenticated demo access
    
    @property
    def is_authenticated(self) -> bool:
        return not self.is_public
    
    @property 
    def identifier(self) -> str:
        """Unique ID for rate limiting"""
        return self.user_id or self.api_key_name or "anonymous"


# ---------------------------------------------------------------------------
# Bearer token scheme (auto_error=False allows optional auth)
# ---------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=False)
_bearer_required = HTTPBearer(auto_error=True)


# ---------------------------------------------------------------------------
# Core validation functions
# ---------------------------------------------------------------------------

def _validate_jwt(token: str) -> Optional[AuthContext]:
    """Validate Supabase JWT token"""
    try:
        from services.auth import get_auth_service
        auth_service = get_auth_service()
        user = auth_service.verify_jwt(token)
        
        return AuthContext(
            user_id=user["user_id"],
            email=user.get("email"),
            tier=user.get("metadata", {}).get("tier", "free")
        )
    except Exception:
        return None


def _validate_api_key(token: str) -> Optional[AuthContext]:
    """Validate API key (ci_xxx format)"""
    # Dev key ONLY works in explicit DEBUG mode AND must be explicitly set
    # This prevents accidental use of dev keys in production
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    dev_key = os.getenv("DEV_API_KEY")  # Must be explicitly set, no default
    
    if debug_mode and dev_key and token == dev_key:
        return AuthContext(
            api_key_name="development",
            tier="enterprise"
        )
    
    # Production API keys start with ci_
    if not token.startswith("ci_"):
        return None
    
    try:
        from services.supabase_service import get_supabase_service
        db = get_supabase_service().client
        
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        result = db.table("api_keys").select("*").eq("key_hash", key_hash).eq("active", True).execute()
        
        if not result.data:
            return None
        
        key_data = result.data[0]
        return AuthContext(
            api_key_name=key_data.get("name"),
            user_id=key_data.get("user_id"),
            tier=key_data.get("tier", "free")
        )
    except Exception:
        return None


def _authenticate(token: str) -> AuthContext:
    """Try JWT first, then API key"""
    # Try JWT (Supabase tokens)
    ctx = _validate_jwt(token)
    if ctx:
        return ctx
    
    # Try API key
    ctx = _validate_api_key(token)
    if ctx:
        return ctx
    
    # Neither worked
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token or API key",
        headers={"WWW-Authenticate": "Bearer"}
    )


# ---------------------------------------------------------------------------
# FastAPI Dependencies - use these in your routes
# ---------------------------------------------------------------------------

async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_required)
) -> AuthContext:
    """
    Require authentication (JWT or API key)
    
    Raises 401 if no valid credentials provided.
    """
    return _authenticate(credentials.credentials)


async def public_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)
) -> AuthContext:
    """
    Optional authentication for public/demo routes
    
    Returns authenticated context if valid token provided,
    otherwise returns public context (is_public=True).
    """
    if not credentials:
        return AuthContext(is_public=True)
    
    try:
        return _authenticate(credentials.credentials)
    except HTTPException:
        # Invalid token on public route = treat as anonymous
        return AuthContext(is_public=True)


# ---------------------------------------------------------------------------
# Legacy functions - kept for backwards compatibility
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_required)
) -> dict:
    """
    [LEGACY] Get current user from JWT token
    
    Prefer using require_auth() for new code.
    """
    from services.auth import get_auth_service
    auth_service = get_auth_service()
    return auth_service.verify_jwt(credentials.credentials)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)
) -> Optional[dict]:
    """
    [LEGACY] Optional JWT authentication
    
    Prefer using public_auth() for new code.
    """
    if not credentials:
        return None
    
    try:
        from services.auth import get_auth_service
        auth_service = get_auth_service()
        return auth_service.verify_jwt(credentials.credentials)
    except Exception:
        return None
