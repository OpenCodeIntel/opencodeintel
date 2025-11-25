"""
Authentication Middleware
Protects routes requiring authentication
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from typing import Dict, Any, Optional
from services.auth import get_auth_service

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from JWT token
    
    Usage:
        @app.get("/protected")
        async def protected_route(user: Dict = Depends(get_current_user)):
            return {"user_id": user["user_id"]}
    
    Returns:
        Dict with user_id, email, and metadata
        
    Raises:
        HTTPException: 401 if token invalid
    """
    auth_service = get_auth_service()
    return auth_service.verify_jwt(credentials.credentials)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[Dict[str, Any]]:
    """
    Optional authentication - returns None if no token provided
    
    Usage:
        @app.get("/optional-auth")
        async def route(user: Optional[Dict] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello {user['email']}"}
            return {"message": "Hello guest"}
    """
    if not credentials:
        return None
    
    try:
        auth_service = get_auth_service()
        return auth_service.verify_jwt(credentials.credentials)
    except:
        return None
