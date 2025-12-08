"""
API Configuration - Single Source of Truth for API Versioning

Change API_VERSION here to update all routes across the application.
Example: "v1" -> "v2" will change /api/v1/* to /api/v2/*
"""

# =============================================================================
# API VERSION CONFIGURATION
# =============================================================================

API_VERSION = "v1"

# =============================================================================
# DERIVED PREFIXES (auto-calculated from version)
# =============================================================================

# Current versioned API prefix: /api/v1
API_PREFIX = f"/api/{API_VERSION}"

# Legacy prefix for backward compatibility: /api
# Routes here will be deprecated but still functional
LEGACY_API_PREFIX = "/api"

# =============================================================================
# DEPRECATION SETTINGS
# =============================================================================

# When True, legacy routes (/api/*) will include deprecation warning headers
LEGACY_DEPRECATION_ENABLED = True

# Header to add on deprecated routes
DEPRECATION_HEADER = "X-API-Deprecated"
DEPRECATION_MESSAGE = f"This endpoint is deprecated. Please use {API_PREFIX} instead."

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_versioned_prefix() -> str:
    """Get the current versioned API prefix."""
    return API_PREFIX


def get_legacy_prefix() -> str:
    """Get the legacy (deprecated) API prefix."""
    return LEGACY_API_PREFIX


def is_legacy_route(path: str) -> bool:
    """Check if a route path is using the legacy prefix."""
    return path.startswith(LEGACY_API_PREFIX) and not path.startswith(API_PREFIX)
