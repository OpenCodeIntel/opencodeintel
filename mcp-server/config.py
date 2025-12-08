"""
API Configuration - Single Source of Truth for API Versioning

Change API_VERSION here to update all API calls across the MCP server.
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
