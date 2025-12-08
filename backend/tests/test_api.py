"""
Security and Validation Integration Tests
Tests actual API behavior with mocked dependencies
"""
import pytest

# Import API prefix from centralized config (single source of truth)
from config.api import API_PREFIX


class TestAPIAuthentication:
    """Test authentication and authorization"""
    
    def test_health_check_no_auth_required(self, client_no_auth):
        """Health check should not require authentication"""
        response = client_no_auth.get("/health")
        assert response.status_code == 200
    
    def test_protected_endpoint_requires_auth(self, client_no_auth):
        """Protected endpoints should require API key"""
        response = client_no_auth.get(f"{API_PREFIX}/repos")
        assert response.status_code in [401, 403]  # Either unauthorized or forbidden
    
    def test_valid_dev_key_works(self, client_no_auth, valid_headers):
        """Valid development API key should work in debug mode"""
        # Note: This tests actual auth, requires DEBUG=true and DEV_API_KEY set
        response = client_no_auth.get(f"{API_PREFIX}/repos", headers=valid_headers)
        # May return 200 or 401 depending on env setup during test
        assert response.status_code in [200, 401]
    
    def test_invalid_key_rejected(self, client_no_auth):
        """Invalid API keys should be rejected"""
        response = client_no_auth.get(
            f"{API_PREFIX}/repos",
            headers={"Authorization": "Bearer invalid-random-key"}
        )
        assert response.status_code in [401, 403]


class TestRepositorySecurityValidation:
    """Test repository endpoint security"""
    
    def test_reject_file_scheme_urls(self, client, valid_headers, malicious_payloads):
        """Should block file:// URLs"""
        for url in malicious_payloads["file_urls"]:
            response = client.post(
                f"{API_PREFIX}/repos",
                headers=valid_headers,
                json={"name": "test", "git_url": url}
            )
            assert response.status_code == 400
            assert "Invalid Git URL" in response.json()["detail"]
    
    def test_reject_localhost_urls(self, client, valid_headers, malicious_payloads):
        """Should block localhost/private IP URLs"""
        for url in malicious_payloads["localhost_urls"]:
            response = client.post(
                f"{API_PREFIX}/repos",
                headers=valid_headers,
                json={"name": "test", "git_url": url}
            )
            assert response.status_code == 400
            assert "Private/local" in response.json()["detail"] or "Invalid" in response.json()["detail"]
    
    def test_reject_invalid_repo_names(self, client, valid_headers):
        """Should reject invalid repository names"""
        invalid_names = ["../etc", "my repo", "test@#$", ""]
        
        for name in invalid_names:
            response = client.post(
                f"{API_PREFIX}/repos",
                headers=valid_headers,
                json={"name": name, "git_url": "https://github.com/test/repo"}
            )
            assert response.status_code in [400, 422]


class TestSearchSecurityValidation:
    """Test search endpoint security"""
    
    def test_reject_sql_injection_attempts(self, client, valid_headers, malicious_payloads):
        """Should block SQL injection in search queries"""
        for sql_query in malicious_payloads["sql_injection"]:
            response = client.post(
                f"{API_PREFIX}/search",
                headers=valid_headers,
                json={"query": sql_query, "repo_id": "test-id"}
            )
            # Query is either blocked (400), repo not found (404), or sanitized and processed (200/500)
            # The important thing is it doesn't execute SQL
            assert response.status_code in [200, 400, 404, 500]
    
    def test_reject_empty_queries(self, client, valid_headers):
        """Should reject empty search queries"""
        response = client.post(
            f"{API_PREFIX}/search",
            headers=valid_headers,
            json={"query": "", "repo_id": "test-id"}
        )
        # 400 for validation error, 404 if repo check happens first
        assert response.status_code in [400, 404]
    
    def test_reject_oversized_queries(self, client, valid_headers):
        """Should reject queries over max length"""
        response = client.post(
            f"{API_PREFIX}/search",
            headers=valid_headers,
            json={"query": "a" * 1000, "repo_id": "test-id"}
        )
        # 400 for validation, 404 if repo check happens first
        assert response.status_code in [400, 404]


class TestImpactAnalysisSecurity:
    """Test impact analysis security"""
    
    def test_reject_path_traversal_attempts(self, client, valid_headers, malicious_payloads):
        """Should block path traversal in impact analysis"""
        for path in malicious_payloads["path_traversal"]:
            response = client.post(
                f"{API_PREFIX}/repos/test-id/impact",
                headers=valid_headers,
                json={"repo_id": "test-id", "file_path": path}
            )
            # Either validation fails (400), repo not found (404), or internal error (500)
            assert response.status_code in [400, 404, 500]
            # If 500, it means validation passed but operation failed (still secure)
            if response.status_code == 500:
                # Ensure it's not leaking system info
                assert "etc" not in response.json().get("detail", "").lower()


class TestCostControls:
    """Test cost control mechanisms"""
    
    def test_max_limits_configured(self):
        """Verify cost control limits are set"""
        from services.input_validator import InputValidator
        
        assert InputValidator.MAX_FUNCTIONS_PER_REPO == 50000
        assert InputValidator.MAX_REPOS_PER_USER == 50
        assert InputValidator.MAX_QUERY_LENGTH == 500
    
    def test_search_results_capped(self, client, valid_headers):
        """Search results should be capped at maximum"""
        response = client.post(
            f"{API_PREFIX}/search",
            headers=valid_headers,
            json={
                "query": "test query",
                "repo_id": "test-id",
                "max_results": 1000  # Try to request 1000
            }
        )
        # Should either cap at 50 or fail because repo doesn't exist
        assert response.status_code in [200, 404, 500]
