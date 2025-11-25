"""
Authentication Routes
Handles user signup, login, and session management
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from services.auth import get_auth_service
from middleware.auth import get_current_user

# Create router
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# Request/Response Models
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    github_username: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    user: Dict[str, Any]
    session: Dict[str, Any]


# Routes
@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    """
    Sign up a new user with Supabase Auth
    
    - **email**: Valid email address
    - **password**: Password (min 6 characters recommended)
    - **github_username**: Optional GitHub username for profile
    
    Returns user data and session tokens (access_token, refresh_token)
    """
    auth_service = get_auth_service()
    return await auth_service.signup(
        email=request.email,
        password=request.password,
        github_username=request.github_username
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Login with email and password
    
    - **email**: Registered email address
    - **password**: User password
    
    Returns user data and session tokens
    """
    auth_service = get_auth_service()
    return await auth_service.login(
        email=request.email,
        password=request.password
    )


@router.post("/refresh")
async def refresh(request: RefreshRequest):
    """
    Refresh access token using refresh token
    
    - **refresh_token**: Valid refresh token from login/signup
    
    Returns new access token
    """
    auth_service = get_auth_service()
    return await auth_service.refresh_session(request.refresh_token)


@router.post("/logout")
async def logout(user: Dict = Depends(get_current_user)):
    """
    Logout current user and invalidate session
    
    Requires: Valid JWT token in Authorization header
    """
    auth_service = get_auth_service()
    return await auth_service.logout(token="")  # Supabase handles session


@router.get("/me")
async def get_current_user_info(user: Dict = Depends(get_current_user)):
    """
    Get current authenticated user information
    
    Requires: Valid JWT token in Authorization header
    
    Returns user profile data
    """
    return {"user": user}
