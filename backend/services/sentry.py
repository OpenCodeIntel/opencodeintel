"""
Sentry Error Tracking Integration
Provides production error visibility and performance monitoring
"""
import os
import functools
from typing import Optional, Callable, Any
from contextlib import contextmanager


# Global flag to track if Sentry is initialized
_sentry_initialized = False


def init_sentry() -> bool:
    """
    Initialize Sentry SDK if SENTRY_DSN is configured.
    
    Returns:
        bool: True if Sentry was initialized, False otherwise
    """
    global _sentry_initialized
    sentry_dsn = os.getenv("SENTRY_DSN")
    
    if not sentry_dsn:
        print("ℹ️  Sentry DSN not configured - error tracking disabled")
        return False
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        
        environment = os.getenv("ENVIRONMENT", "development")
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            
            # Performance monitoring - sample 10% in production, 100% in dev
            traces_sample_rate=0.1 if environment == "production" else 1.0,
            
            # Profile 10% of sampled transactions
            profiles_sample_rate=0.1,
            
            # Send PII like user IDs (needed for debugging)
            send_default_pii=True,
            
            # Integrations
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                StarletteIntegration(transaction_style="endpoint"),
            ],
            
            # Filter out health check noise
            before_send=_filter_events,
            
            # Debug logging in development
            debug=environment == "development",
        )
        
        _sentry_initialized = True
        print(f"✅ Sentry initialized (environment: {environment})")
        return True
        
    except ImportError:
        print("⚠️  sentry-sdk not installed - error tracking disabled")
        return False
    except Exception as e:
        print(f"⚠️  Failed to initialize Sentry: {e}")
        return False


def _filter_events(event, hint):
    """Filter out noisy events before sending to Sentry."""
    # Don't send health check errors
    request_url = event.get("request", {}).get("url", "")
    if "/health" in request_url:
        return None
    
    # Don't send 404s for common bot paths
    if event.get("exception"):
        values = event["exception"].get("values", [{}])
        if values:
            exception_value = str(values[0].get("value", ""))
            bot_paths = ["/wp-admin", "/wp-login", "/.env", "/config", "/admin", "/phpmyadmin"]
            if any(path in exception_value for path in bot_paths):
                return None
    
    return event


# ---------------------------------------------------------------------------
# User Context
# ---------------------------------------------------------------------------

def set_user_context(user_id: Optional[str] = None, email: Optional[str] = None):
    """
    Set user context for error tracking.
    Call after authentication to attach user info to errors.
    """
    if not _sentry_initialized:
        return
    
    try:
        import sentry_sdk
        sentry_sdk.set_user({
            "id": user_id,
            "email": email,
        })
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Operation Context (for tagging operations like indexing, search)
# ---------------------------------------------------------------------------

@contextmanager
def sentry_operation(operation: str, **tags):
    """
    Context manager to tag operations with context.
    
    Usage:
        with sentry_operation("indexing", repo_id="abc", repo_name="zustand"):
            # do indexing work
            # any errors here will have repo_id and repo_name tags
    """
    if not _sentry_initialized:
        yield
        return
    
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("operation", operation)
            for key, value in tags.items():
                scope.set_tag(key, str(value))
            yield
    except ImportError:
        yield


def set_operation_context(operation: str, **tags):
    """
    Set operation context without context manager.
    Useful when you can't use 'with' statement.
    """
    if not _sentry_initialized:
        return
    
    try:
        import sentry_sdk
        sentry_sdk.set_tag("operation", operation)
        for key, value in tags.items():
            sentry_sdk.set_tag(key, str(value))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Exception Capture
# ---------------------------------------------------------------------------

def capture_exception(error: Exception, **extra_context):
    """
    Manually capture an exception with additional context.
    
    Args:
        error: The exception to capture
        **extra_context: Additional context (repo_id, operation, etc.)
    """
    if not _sentry_initialized:
        return
    
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in extra_context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(error)
    except Exception:
        pass


def capture_message(message: str, level: str = "info", **extra_context):
    """
    Capture a message (not an exception) for tracking.
    
    Args:
        message: The message to capture
        level: Severity level (info, warning, error)
        **extra_context: Additional context
    """
    if not _sentry_initialized:
        return
    
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in extra_context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_message(message, level=level)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Background Task Decorator
# ---------------------------------------------------------------------------

def track_background_task(operation: str):
    """
    Decorator to track background tasks and capture any errors.
    
    Usage:
        @track_background_task("indexing")
        async def index_repository(repo_id: str):
            # any unhandled exception here will be captured with context
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            if not _sentry_initialized:
                return await func(*args, **kwargs)
            
            try:
                import sentry_sdk
                with sentry_sdk.push_scope() as scope:
                    scope.set_tag("operation", operation)
                    scope.set_tag("background_task", "true")
                    # Add function args as context
                    scope.set_extra("args", str(args)[:500])
                    scope.set_extra("kwargs", str(kwargs)[:500])
                    
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        sentry_sdk.capture_exception(e)
                        raise  # Re-raise so caller knows it failed
            except ImportError:
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            if not _sentry_initialized:
                return func(*args, **kwargs)
            
            try:
                import sentry_sdk
                with sentry_sdk.push_scope() as scope:
                    scope.set_tag("operation", operation)
                    scope.set_tag("background_task", "true")
                    scope.set_extra("args", str(args)[:500])
                    scope.set_extra("kwargs", str(kwargs)[:500])
                    
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        sentry_sdk.capture_exception(e)
                        raise
            except ImportError:
                return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio_iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def asyncio_iscoroutinefunction(func):
    """Check if function is async."""
    import asyncio
    return asyncio.iscoroutinefunction(func)


# ---------------------------------------------------------------------------
# HTTP Exception Handler Helper
# ---------------------------------------------------------------------------

def capture_http_exception(request, exc, status_code: int):
    """
    Capture HTTP exceptions that would otherwise be swallowed.
    Call this from FastAPI exception handlers for 500+ errors.
    
    Args:
        request: FastAPI request object
        exc: The exception
        status_code: HTTP status code being returned
    """
    # Only capture server errors (5xx)
    if status_code < 500 or not _sentry_initialized:
        return
    
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("http_status", str(status_code))
            scope.set_extra("path", str(request.url.path))
            scope.set_extra("method", request.method)
            sentry_sdk.capture_exception(exc)
    except Exception:
        pass
