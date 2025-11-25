"""
Supabase Authentication Service
Handles JWT verification and user management
"""
from fastapi import HTTPException, status
from typing import Optional, Dict, Any
import os
import jwt
from datetime import datetime
from supabase import create_client, Client


class SupabaseAuthService:
    """Supabase authentication and user management"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        self.jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        
        if not all([self.supabase_url, self.supabase_key]):
            raise ValueError("Supabase credentials not configured")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
    
    def verify_jwt(self, token: str) -> Dict[str, Any]:
        """
        Verify Supabase JWT token and return user data
        
        Args:
            token: JWT token from Authorization header (format: "Bearer <token>")
            
        Returns:
            Dict with user_id, email, and other user metadata
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            # Remove "Bearer " prefix if present
            if token.startswith("Bearer "):
                token = token[7:]
            
            # Use Supabase client to verify token and get user
            response = self.client.auth.get_user(token)
            
            if not response.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token"
                )
            
            return {
                "user_id": response.user.id,
                "email": response.user.email,
                "created_at": response.user.created_at,
                "metadata": response.user.user_metadata
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(e)}"
            )
    
    async def signup(self, email: str, password: str, github_username: Optional[str] = None) -> Dict[str, Any]:
        """
        Sign up a new user with Supabase Auth
        
        Args:
            email: User email
            password: User password (min 6 chars)
            github_username: Optional GitHub username
            
        Returns:
            Dict with user data and session tokens
        """
        try:
            # Create user with Supabase Auth
            response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "github_username": github_username
                    }
                }
            })
            
            if not response.user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Signup failed"
                )
            
            return {
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "github_username": github_username
                },
                "session": {
                    "access_token": response.session.access_token if response.session else None,
                    "refresh_token": response.session.refresh_token if response.session else None,
                    "expires_at": response.session.expires_at if response.session else None
                }
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Signup failed: {str(e)}"
            )
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Login user with email and password
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Dict with user data and session tokens
        """
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if not response.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
            
            return {
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "github_username": response.user.user_metadata.get("github_username")
                },
                "session": {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "expires_at": response.session.expires_at
                }
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Login failed: {str(e)}"
            )
    
    async def refresh_session(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        try:
            response = self.client.auth.refresh_session(refresh_token)
            
            if not response.session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token refresh failed"
                )
            
            return {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "expires_at": response.session.expires_at
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Refresh failed: {str(e)}"
            )
    
    async def logout(self, token: str) -> Dict[str, str]:
        """Sign out user and invalidate session"""
        try:
            await self.client.auth.sign_out()
            return {"message": "Logged out successfully"}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Logout failed: {str(e)}"
            )


# Global instance
_auth_service: Optional[SupabaseAuthService] = None


def get_auth_service() -> SupabaseAuthService:
    """Get or create auth service singleton"""
    global _auth_service
    if _auth_service is None:
        _auth_service = SupabaseAuthService()
    return _auth_service
