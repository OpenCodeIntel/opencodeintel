"""
Observability Module
Centralized logging, tracing, and metrics for CodeIntel

Features:
- Structured JSON logging (prod) / Pretty logging (dev)
- Sentry integration with context
- Performance tracking decorators
- Operation context managers
"""
import os
import json
import time
import logging
import functools
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from datetime import datetime


# ============================================================================
# CONFIGURATION
# ============================================================================

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "pretty" if ENVIRONMENT == "development" else "json")


# ============================================================================
# STRUCTURED LOGGER
# ============================================================================

class StructuredLogger:
    """
    Structured logger with JSON output for production and pretty output for dev.
    
    Usage:
        logger = get_logger("indexer")
        logger.info("Starting indexing", repo_id="abc", files=100)
        logger.error("Failed to index", error=str(e), repo_id="abc")
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
        
        # Only configure if not already configured
        if not self.logger.handlers:
            self.logger.setLevel(getattr(logging, LOG_LEVEL))
            handler = logging.StreamHandler()
            handler.setLevel(getattr(logging, LOG_LEVEL))
            
            if LOG_FORMAT == "json":
                handler.setFormatter(JsonFormatter())
            else:
                handler.setFormatter(PrettyFormatter())
            
            self.logger.addHandler(handler)
            self.logger.propagate = False
    
    def _log(self, level: str, message: str, **context):
        """Internal log method with context"""
        extra = {
            "service": self.name,
            "timestamp": datetime.utcnow().isoformat(),
            "environment": ENVIRONMENT,
            **context
        }
        
        log_method = getattr(self.logger, level)
        log_method(message, extra={"structured": extra})
    
    def debug(self, message: str, **context):
        self._log("debug", message, **context)
    
    def info(self, message: str, **context):
        self._log("info", message, **context)
    
    def warning(self, message: str, **context):
        self._log("warning", message, **context)
    
    def error(self, message: str, **context):
        self._log("error", message, **context)
        
        # Also send to Sentry if it's a real error
        if "error" in context or "exception" in context:
            _capture_to_sentry(message, level="error", **context)
    
    def critical(self, message: str, **context):
        self._log("critical", message, **context)
        _capture_to_sentry(message, level="fatal", **context)


class JsonFormatter(logging.Formatter):
    """JSON formatter for production logs"""
    
    def format(self, record):
        structured = getattr(record, "structured", {})
        log_entry = {
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            **structured
        }
        return json.dumps(log_entry)


class PrettyFormatter(logging.Formatter):
    """Pretty formatter for development"""
    
    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record):
        structured = getattr(record, "structured", {})
        color = self.COLORS.get(record.levelname, "")
        
        # Build context string
        context_parts = []
        for key, value in structured.items():
            if key not in ("service", "timestamp", "environment"):
                context_parts.append(f"{key}={value}")
        
        context_str = " | ".join(context_parts) if context_parts else ""
        service = structured.get("service", "app")
        
        return f"{color}[{record.levelname}]{self.RESET} [{service}] {record.getMessage()} {context_str}"


# Logger cache
_loggers: Dict[str, StructuredLogger] = {}

def get_logger(name: str) -> StructuredLogger:
    """Get or create a structured logger"""
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name)
    return _loggers[name]


# ============================================================================
# SENTRY INTEGRATION
# ============================================================================

def _capture_to_sentry(message: str, level: str = "error", **context):
    """Send message/error to Sentry with context"""
    try:
        import sentry_sdk
        
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
            
            if level == "fatal":
                sentry_sdk.capture_message(message, level="fatal")
            else:
                sentry_sdk.capture_message(message, level=level)
    except ImportError:
        pass  # Sentry not installed


def capture_exception(error: Exception, **context):
    """
    Capture an exception to Sentry with full context.
    
    Usage:
        try:
            risky_operation()
        except Exception as e:
            capture_exception(e, repo_id="abc", operation="indexing")
    """
    try:
        import sentry_sdk
        
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(error)
    except ImportError:
        # Log to console if Sentry not available
        logger = get_logger("error")
        logger.error(f"Exception: {error}", exception=str(error), **context)


def set_user_context(user_id: Optional[str] = None, email: Optional[str] = None):
    """Set user context for error tracking"""
    try:
        import sentry_sdk
        sentry_sdk.set_user({"id": user_id, "email": email})
    except ImportError:
        pass


def set_tag(key: str, value: str):
    """Set a tag that persists across the request"""
    try:
        import sentry_sdk
        sentry_sdk.set_tag(key, value)
    except ImportError:
        pass


# ============================================================================
# PERFORMANCE TRACKING
# ============================================================================

@contextmanager
def trace_operation(
    operation: str,
    description: Optional[str] = None,
    **tags
):
    """
    Context manager for tracing operations with timing.
    
    Usage:
        with trace_operation("indexing", repo_id="abc") as span:
            do_indexing()
            span.set_data("files_processed", 100)
    """
    logger = get_logger(operation)
    start_time = time.time()
    
    # Start Sentry span if available
    span = None
    try:
        import sentry_sdk
        span = sentry_sdk.start_span(op=operation, description=description)
        for key, value in tags.items():
            span.set_tag(key, str(value))
        span.__enter__()
    except ImportError:
        pass
    
    # Create a simple span-like object for data attachment
    class SpanData:
        def __init__(self):
            self.data = {}
        
        def set_data(self, key: str, value: Any):
            self.data[key] = value
            if span:
                span.set_data(key, value)
    
    span_data = SpanData()
    
    try:
        logger.debug(f"Starting {operation}", **tags)
        yield span_data
        
        duration = time.time() - start_time
        logger.info(
            f"Completed {operation}",
            duration_ms=round(duration * 1000, 2),
            **tags,
            **span_data.data
        )
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Failed {operation}",
            error=str(e),
            duration_ms=round(duration * 1000, 2),
            **tags,
            **span_data.data
        )
        capture_exception(e, operation=operation, **tags, **span_data.data)
        raise
    
    finally:
        if span:
            try:
                span.__exit__(None, None, None)
            except Exception:
                pass


def track_performance(operation: str = None):
    """
    Decorator for tracking function performance.
    
    Usage:
        @track_performance("search")
        async def semantic_search(query: str, repo_id: str):
            ...
    """
    def decorator(func: Callable):
        op_name = operation or func.__name__
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with trace_operation(op_name, description=func.__name__):
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with trace_operation(op_name, description=func.__name__):
                return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio_iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def asyncio_iscoroutinefunction(func):
    """Check if function is async"""
    import asyncio
    return asyncio.iscoroutinefunction(func)


# ============================================================================
# METRICS (Simple counters - can be extended to Prometheus later)
# ============================================================================

class Metrics:
    """
    Simple metrics collection.
    
    Usage:
        metrics = get_metrics()
        metrics.increment("indexing.files_processed", 10)
        metrics.timing("search.latency_ms", 150)
    """
    
    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._timings: Dict[str, list] = {}
    
    def increment(self, name: str, value: int = 1):
        """Increment a counter"""
        self._counters[name] = self._counters.get(name, 0) + value
    
    def timing(self, name: str, value_ms: float):
        """Record a timing measurement"""
        if name not in self._timings:
            self._timings[name] = []
        self._timings[name].append(value_ms)
        
        # Keep only last 1000 measurements
        if len(self._timings[name]) > 1000:
            self._timings[name] = self._timings[name][-1000:]
    
    def get_counter(self, name: str) -> int:
        """Get counter value"""
        return self._counters.get(name, 0)
    
    def get_timing_stats(self, name: str) -> Dict[str, float]:
        """Get timing statistics"""
        timings = self._timings.get(name, [])
        if not timings:
            return {"count": 0, "avg": 0, "min": 0, "max": 0}
        
        return {
            "count": len(timings),
            "avg": sum(timings) / len(timings),
            "min": min(timings),
            "max": max(timings)
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get all metrics"""
        return {
            "counters": self._counters.copy(),
            "timings": {
                name: self.get_timing_stats(name)
                for name in self._timings
            }
        }


# Metrics singleton
_metrics: Optional[Metrics] = None

def get_metrics() -> Metrics:
    """Get metrics instance"""
    global _metrics
    if _metrics is None:
        _metrics = Metrics()
    return _metrics


# ============================================================================
# CONVENIENCE EXPORTS
# ============================================================================

__all__ = [
    "get_logger",
    "capture_exception", 
    "set_user_context",
    "set_tag",
    "trace_operation",
    "track_performance",
    "get_metrics",
]
