"""
Sentry Error Tracking Integration
Provides production error visibility and performance monitoring

NOTE: This module initializes Sentry. For logging and tracing,
use the observability module: from services.observability import get_logger, trace_operation
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

            # Performance monitoring - sample rate based on environment
            traces_sample_rate=0.1 if environment == "production" else 1.0,

            # Profile sampled transactions
            profiles_sample_rate=0.1 if environment == "production" else 1.0,

            # Send PII for debugging (user IDs, emails)
            send_default_pii=True,

            # Integrations
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                StarletteIntegration(transaction_style="endpoint"),
            ],

            # Filter noisy events
            before_send=_filter_events,

            # Debug mode for development
            debug=environment == "development",

            # Attach stack traces to messages
            attach_stacktrace=True,

            # Include local variables in stack traces
            include_local_variables=True,
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
    """Filter out noisy events before sending to Sentry."""

    # Don't send health check errors
    request_url = event.get("request", {}).get("url", "")
    if "/health" in request_url:
        return None

    # Don't send 404s for common bot paths
    exception_values = event.get("exception", {}).get("values", [])
    if exception_values:
        exception_value = str(exception_values[0].get("value", ""))
        bot_paths = ["/wp-admin", "/wp-login", "/.env", "/config", "/admin", "/phpmyadmin", "/.git"]
        if any(path in exception_value for path in bot_paths):
            return None

    # Don't send validation errors (they're expected)
    if exception_values:
        exception_type = exception_values[0].get("type", "")
        if exception_type in ("RequestValidationError", "ValidationError"):
            return None

    return event


# ============================================================================
# LEGACY FUNCTIONS - Use observability module for new code
# ============================================================================

def set_user_context(user_id: Optional[str] = None, email: Optional[str] = None):
    """
    Set user context for error tracking.

    DEPRECATED: Use from services.observability import set_user_context
    """
    try:
        import sentry_sdk
        sentry_sdk.set_user({"id": user_id, "email": email})
    except ImportError:
        pass


def capture_exception(error: Exception, **extra_context):
    """
    Manually capture an exception with additional context.

    DEPRECATED: Use from services.observability import capture_exception
    """
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in extra_context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(error)
    except ImportError:
        pass


def capture_message(message: str, level: str = "info", **extra_context):
    """
    Capture a message (not an exception) for tracking.

    DEPRECATED: Use from services.observability import get_logger
    """
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in extra_context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_message(message, level=level)
    except ImportError:
        pass


def set_operation_context(operation: str, **tags):
    """
    Set operation context for the current scope.

    DEPRECATED: Use from services.observability import trace_operation
    """
    try:
        import sentry_sdk
        sentry_sdk.set_tag("operation", operation)
        for key, value in tags.items():
            sentry_sdk.set_tag(key, str(value))
    except ImportError:
        pass


def capture_http_exception(request, exc: Exception, status_code: int):
    """
    Capture HTTP exception with request context for error tracking.
    """
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            scope.set_extra("status_code", status_code)
            scope.set_extra("path", str(request.url.path))
            scope.set_extra("method", request.method)
            sentry_sdk.capture_exception(exc)
    except ImportError:
        pass
        pass
