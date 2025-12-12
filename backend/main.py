"""
CodeIntel Backend API
FastAPI backend for codebase intelligence
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import os

# Initialize Sentry FIRST (before other imports to catch all errors)
from services.sentry import init_sentry
init_sentry()

# Import API config (single source of truth for versioning)
from config.api import API_PREFIX, API_VERSION

# Import routers
from routes.auth import router as auth_router
from routes.health import router as health_router
from routes.playground import router as playground_router, load_demo_repos
from routes.repos import router as repos_router, websocket_index
from routes.search import router as search_router
from routes.analysis import router as analysis_router
from routes.api_keys import router as api_keys_router


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await load_demo_repos()
    yield
    # Shutdown (cleanup if needed)


app = FastAPI(
    title="CodeIntel API",
    description="Codebase Intelligence API for MCP",
    version="0.2.0",
    lifespan=lifespan
)


# ===== MIDDLEWARE =====

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent abuse."""
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.MAX_REQUEST_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request too large (max {self.MAX_REQUEST_SIZE / 1024 / 1024}MB)"}
                )
        return await call_next(request)


# Add middleware
app.add_middleware(RequestSizeLimitMiddleware)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ===== ROUTERS =====
# All API routes are prefixed with API_PREFIX (e.g., /api/v1)
# Route files define their sub-path (e.g., /auth, /repos)
# Final paths: /api/v1/auth, /api/v1/repos, etc.

app.include_router(health_router)  # /health stays at root (no versioning needed)
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(playground_router, prefix=API_PREFIX)
app.include_router(repos_router, prefix=API_PREFIX)
app.include_router(search_router, prefix=API_PREFIX)
app.include_router(analysis_router, prefix=API_PREFIX)
app.include_router(api_keys_router, prefix=API_PREFIX)

# WebSocket endpoint (versioned)
app.add_api_websocket_route(f"{API_PREFIX}/ws/index/{{repo_id}}", websocket_index)


# ===== ERROR HANDLERS =====

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with clear messages."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )


@app.exception_handler(429)
async def rate_limit_handler(request: Request, exc):
    """Handle rate limit errors."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."}
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unhandled exceptions.
    Captures to Sentry and returns 500.
    """
    from services.sentry import capture_http_exception
    capture_http_exception(request, exc, 500)
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
