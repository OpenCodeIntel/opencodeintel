"""API key management and metrics routes."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from dependencies import api_key_manager, rate_limiter, metrics
from middleware.auth import require_auth, AuthContext

router = APIRouter(prefix="", tags=["API Keys"])


class CreateAPIKeyRequest(BaseModel):
    name: str
    tier: str = "free"


@router.get("/metrics")
async def get_performance_metrics(
    auth: AuthContext = Depends(require_auth)
):
    """Get performance metrics and monitoring data."""
    return metrics.get_metrics()


@router.post("/keys/generate")
async def generate_api_key(
    request: CreateAPIKeyRequest,
    auth: AuthContext = Depends(require_auth)
):
    """Generate a new API key."""
    new_key = api_key_manager.generate_key(
        name=request.name,
        tier=request.tier,
        user_id=auth.user_id
    )
    
    return {
        "api_key": new_key,
        "tier": request.tier,
        "name": request.name,
        "message": "Save this key securely - it won't be shown again"
    }


@router.get("/keys/usage")
async def get_api_usage(
    auth: AuthContext = Depends(require_auth)
):
    """Get current API usage stats."""
    usage = rate_limiter.get_usage(auth.identifier)
    
    return {
        "tier": auth.tier,
        "limits": {
            "free": {"minute": 20, "hour": 200, "day": 1000},
            "pro": {"minute": 100, "hour": 2000, "day": 20000},
            "enterprise": {"minute": 500, "hour": 10000, "day": 100000}
        }[auth.tier],
        "usage": usage
    }
