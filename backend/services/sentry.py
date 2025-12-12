"""
Sentry Error Tracking Integration
Provides production error visibility and performance monitoring
"""
import os
from typing import Optional


def init_sentry() -> bool:
    """
    Initialize Sentry SDK if SENTRY_DSN is configured.
    
    Returns:
        bool: True if Sentry was initialized, False otherwise
    """
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
            
            # Performance monitoring - sample 10% of transactions in production
            traces_sample_rate=0.1 if environment == "production" else 1.0,
            
            # Profile 10% of sampled transactions
            profiles_sample_rate=0.1,
            
            # Send PII like user IDs (we need this for debugging)
            send_default_pii=True,
            
            # Integrations
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                StarletteIntegration(transaction_style="endpoint"),
            ],
            
            # Filter out health check noise
            before_send=_filter_events,
            
            # Don't send in debug mode
            debug=environment == "development",
        )
        
        print(f"✅ Sentry initialized (environment: {environment})")
        return True
        
    except ImportError:
        print("⚠️  sentry-sdk not installed - error tracking disabled")
        return False
    except Exception as e:
        print(f"⚠️  Failed to initialize Sentry: {e}")
        return False


def _filter_events(event, hint):
    """
    Filter out noisy events before sending to Sentry.
    """
    # Don't send health check errors
    if "health" in event.get("request", {}).get("url", ""):
        return None
    
    # Don't send 404s for common bot paths
    if event.get("exception"):
        exception_value = str(event["exception"].get("values", [{}])[0].get("value", ""))
        bot_paths = ["/wp-admin", "/wp-login", "/.env", "/config", "/admin"]
        if any(path in exception_value for path in bot_paths):
            return None
    
    return event


def set_user_context(user_id: Optional[str] = None, email: Optional[str] = None):
    """
    Set user context for error tracking.
    Call this after authentication to attach user info to errors.
    
    Args:
        user_id: The authenticated user's ID
        email: The user's email (optional)
    """
    try:
        import sentry_sdk
        sentry_sdk.set_user({
            "id": user_id,
            "email": email,
        })
    except ImportError:
        pass  # Sentry not installed


def capture_exception(error: Exception, **extra_context):
    """
    Manually capture an exception with additional context.
    
    Args:
        error: The exception to capture
        **extra_context: Additional context to attach
    """
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in extra_context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(error)
    except ImportError:
        pass  # Sentry not installed


def capture_message(message: str, level: str = "info", **extra_context):
    """
    Capture a message (not an exception) for tracking.
    
    Args:
        message: The message to capture
        level: Severity level (info, warning, error)
        **extra_context: Additional context to attach
    """
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in extra_context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_message(message, level=level)
    except ImportError:
        pass  # Sentry not installed
