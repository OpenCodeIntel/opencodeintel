"""
Observability Module
Centralized logging, tracing, and metrics for CodeIntel

Usage:
    from services.observability import logger, trace_operation, track_time

    logger.info("Starting indexing", repo_id="abc", files=100)
    
    @trace_operation("indexing")
    async def index_repo(repo_id: str):
        ...
    
    with track_time("embedding_batch"):
        embeddings = await create_embeddings(texts)
"""
import os
import sys
import time
import logging
import json
from typing import Optional, Any, Dict
from functools import wraps
from contextlib import contextmanager
from datetime import datetime

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if IS_PRODUCTION else "DEBUG")


# =============================================================================
# STRUCTURED LOGGER
# =============================================================================

class StructuredLogger:
    """
    Structured logger that outputs JSON in production, pretty logs in development.
    
    Usage:
        logger.info("User logged in", user_id="abc", ip="1.2.3.4")
        logger.error("Failed to index", repo_id="xyz", error=str(e))
    """
    
    def __init__(self, name: str = "codeintel"):
        self.name = name
        self.level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
        self._context: Dict[str, Any] = {}
    
    def _format_message(self, level: str, message: str, **kwargs) -> str:
        """Format log message based on environment"""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "service": self.name,
            "message": message,
            **self._context,
            **kwargs
        }
        
        if IS_PRODUCTION:
            # JSON for production (easy to parse in log aggregators)
            return json.dumps(data)
        else:
            # Pretty format for development
            extras = " | ".join(f"{k}={v}" for k, v in kwargs.items())
            ctx = " | ".join(f"{k}={v}" for k, v in self._context.items())
            parts = [f"[{level}] {message}"]
            if ctx:
                parts.append(f"[ctx: {ctx}]")
            if extras:
                parts.append(extras)
            return " ".join(parts)
    
    def _log(self, level: str, level_num: int, message: str, **kwargs):
        """Internal log method"""
        if level_num < self.level:
            return
        
        formatted = self._format_message(level, message, **kwargs)
        
        # Use stderr for errors, stdout for rest
        output = sys.stderr if level_num >= logging.ERROR else sys.stdout
        print(formatted, file=output)
    
    def set_context(self, **kwargs):
        """Set persistent context for all subsequent logs"""
        self._context.update(kwargs)
    
    def clear_context(self):
        """Clear all context"""
        self._context = {}
    
    def debug(self, message: str, **kwargs):
        self._log("DEBUG", logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log("INFO", logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("WARNING", logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("ERROR", logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log("CRITICAL", logging.CRITICAL, message, **kwargs)


# Global logger instance
logger = StructuredLogger()


# =============================================================================
# SENTRY INTEGRATION HELPERS
# =============================================================================

def set_operation_context(operation: str, **kwargs):
    """
    Set Sentry context for current operation.
    
    Args:
        operation: Type of operation (indexing, search, analysis, etc.)
        **kwargs: Additional context (repo_id, user_id, etc.)
    """
    try:
        import sentry_sdk
        sentry_sdk.set_tag("operation", operation)
        for key, value in kwargs.items():
            sentry_sdk.set_tag(key, str(value))
        sentry_sdk.set_context("operation_details", {
            "type": operation,
            **kwargs
        })
    except ImportError:
        pass


def add_breadcrumb(message: str, category: str = "custom", level: str = "info", **data):
    """
    Add breadcrumb for Sentry error context.
    
    Breadcrumbs show the trail of events leading to an error.
    """
    try:
        import sentry_sdk
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data
        )
    except ImportError:
        pass


def capture_exception(error: Exception, **context):
    """
    Capture exception with additional context.
    
    Args:
        error: The exception to capture
        **context: Additional context to attach
    """
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(error)
        
        # Also log it
        logger.error(
            f"Exception captured: {type(error).__name__}: {str(error)}",
            **context
        )
    except ImportError:
        logger.error(f"Exception: {error}", **context)


def capture_message(message: str, level: str = "info", **context):
    """Capture a message (not exception) to Sentry"""
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_message(message, level=level)
    except ImportError:
        pass


# =============================================================================
# PERFORMANCE TRACKING
# =============================================================================

@contextmanager
def track_time(operation: str, **tags):
    """
    Context manager to track operation duration.
    
    Usage:
        with track_time("embedding_batch", batch_size=100):
            embeddings = await create_embeddings(texts)
    
    Logs duration and creates Sentry span if available.
    """
    start = time.perf_counter()
    
    # Start Sentry span if available
    span = None
    try:
        import sentry_sdk
        span = sentry_sdk.start_span(op=operation, description=operation)
        for key, value in tags.items():
            span.set_tag(key, str(value))
    except ImportError:
        pass
    
    add_breadcrumb(f"Started: {operation}", category="performance", **tags)
    
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        duration_ms = round(duration * 1000, 2)
        
        # Log completion
        logger.debug(f"{operation} completed", duration_ms=duration_ms, **tags)
        
        # Finish Sentry span
        if span:
            span.finish()
        
        add_breadcrumb(
            f"Completed: {operation}",
            category="performance",
            duration_ms=duration_ms,
            **tags
        )


def trace_operation(operation: str):
    """
    Decorator to trace an entire function/method.
    
    Usage:
        @trace_operation("index_repository")
        async def index_repository(repo_id: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract useful context from kwargs
            context = {k: v for k, v in kwargs.items() 
                      if k in ('repo_id', 'user_id', 'query', 'file_path')}
            
            set_operation_context(operation, **context)
            add_breadcrumb(f"Starting {operation}", category="function", **context)
            
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration = time.perf_counter() - start
                logger.info(
                    f"{operation} completed successfully",
                    duration_s=round(duration, 2),
                    **context
                )
                return result
            except Exception as e:
                duration = time.perf_counter() - start
                capture_exception(e, operation=operation, duration_s=round(duration, 2), **context)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            context = {k: v for k, v in kwargs.items() 
                      if k in ('repo_id', 'user_id', 'query', 'file_path')}
            
            set_operation_context(operation, **context)
            add_breadcrumb(f"Starting {operation}", category="function", **context)
            
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start
                logger.info(
                    f"{operation} completed successfully",
                    duration_s=round(duration, 2),
                    **context
                )
                return result
            except Exception as e:
                duration = time.perf_counter() - start
                capture_exception(e, operation=operation, duration_s=round(duration, 2), **context)
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# =============================================================================
# SIMPLE METRICS (in-memory counters)
# =============================================================================

class Metrics:
    """
    Simple in-memory metrics counters.
    
    Usage:
        metrics.increment("search_requests", repo_id="abc")
        metrics.timing("search_latency_ms", 150)
        metrics.get_stats()  # Returns all metrics
    """
    
    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._timings: Dict[str, list] = {}
    
    def increment(self, name: str, value: int = 1, **tags):
        """Increment a counter"""
        key = f"{name}"
        self._counters[key] = self._counters.get(key, 0) + value
    
    def timing(self, name: str, value_ms: float):
        """Record a timing measurement"""
        if name not in self._timings:
            self._timings[name] = []
        self._timings[name].append(value_ms)
        # Keep only last 1000 timings
        if len(self._timings[name]) > 1000:
            self._timings[name] = self._timings[name][-1000:]
    
    def get_stats(self) -> Dict:
        """Get all metrics with basic stats"""
        stats = {
            "counters": self._counters.copy(),
            "timings": {}
        }
        
        for name, values in self._timings.items():
            if values:
                stats["timings"][name] = {
                    "count": len(values),
                    "avg_ms": round(sum(values) / len(values), 2),
                    "min_ms": round(min(values), 2),
                    "max_ms": round(max(values), 2)
                }
        
        return stats
    
    def reset(self):
        """Reset all metrics"""
        self._counters = {}
        self._timings = {}


# Global metrics instance
metrics = Metrics()
