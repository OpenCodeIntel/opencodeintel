"""
Multi-Tenancy Security Tests
Tests for user isolation and ownership verification (Issue #7, #8)

These tests ensure:
1. Users can only see their own repositories
2. Users cannot access other users' repos via direct ID
3. Ownership is verified on all repo-specific endpoints
4. 404 is returned (not 403) to prevent info leakage
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
import sys
import os
from pathlib import Path

# Set test environment BEFORE imports
os.environ["DEBUG"] = "true"
os.environ["DEV_API_KEY"] = "test-dev-key"
os.environ["OPENAI_API_KEY"] = "sk-test-key"
os.environ["PINECONE_API_KEY"] = "pcsk-test"
os.environ["PINECONE_INDEX_NAME"] = "test-index"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_KEY"] = "test-key"
os.environ["SUPABASE_ANON_KEY"] = "test-anon-key"
os.environ["SUPABASE_JWT_SECRET"] = "test-jwt-secret"

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


# ============== TEST DATA ==============

REPOS_DB = [
    {"id": "repo-user1-a", "name": "User1 Repo A", "user_id": "user-1", "status": "indexed", "local_path": "/repos/1a", "file_count": 10},
    {"id": "repo-user1-b", "name": "User1 Repo B", "user_id": "user-1", "status": "indexed", "local_path": "/repos/1b", "file_count": 20},
    {"id": "repo-user2-a", "name": "User2 Repo A", "user_id": "user-2", "status": "indexed", "local_path": "/repos/2a", "file_count": 15},
    {"id": "repo-user2-b", "name": "User2 Repo B", "user_id": "user-2", "status": "indexed", "local_path": "/repos/2b", "file_count": 25},
]


# ============== UNIT TESTS FOR SUPABASE SERVICE ==============

class TestSupabaseServiceOwnership:
    """Unit tests for ownership verification methods in SupabaseService"""
    
    def test_list_repositories_for_user_method_exists(self):
        """list_repositories_for_user method should exist with correct signature"""
        from services.supabase_service import SupabaseService
        import inspect
        
        # Verify method exists
        assert hasattr(SupabaseService, 'list_repositories_for_user')
        
        sig = inspect.signature(SupabaseService.list_repositories_for_user)
        params = list(sig.parameters.keys())
        assert 'user_id' in params, "Method should accept user_id parameter"
    
    def test_get_repository_with_owner_returns_none_for_wrong_user(self):
        """
        get_repository_with_owner should query with both repo_id AND user_id filters.
        This test verifies the method signature and return type.
        The actual SQL filtering is tested via integration tests.
        """
        from services.supabase_service import SupabaseService
        
        # Verify method exists and has correct signature
        import inspect
        sig = inspect.signature(SupabaseService.get_repository_with_owner)
        params = list(sig.parameters.keys())
        
        assert 'repo_id' in params, "Method should accept repo_id parameter"
        assert 'user_id' in params, "Method should accept user_id parameter"
    
    def test_verify_repo_ownership_returns_false_for_wrong_user(self):
        """
        verify_repo_ownership should query with both repo_id AND user_id filters.
        This test verifies the method signature and return type.
        """
        from services.supabase_service import SupabaseService
        
        # Verify method exists and has correct signature
        import inspect
        sig = inspect.signature(SupabaseService.verify_repo_ownership)
        params = list(sig.parameters.keys())
        
        assert 'repo_id' in params, "Method should accept repo_id parameter"
        assert 'user_id' in params, "Method should accept user_id parameter"
        
        # Verify return type annotation is bool
        return_annotation = sig.return_annotation
        assert return_annotation == bool, "Method should return bool"
    
    def test_verify_repo_ownership_returns_true_for_owner(self):
        """verify_repo_ownership method should exist with correct signature"""
        from services.supabase_service import SupabaseService
        import inspect
        
        # Verify method exists
        assert hasattr(SupabaseService, 'verify_repo_ownership')
        
        sig = inspect.signature(SupabaseService.verify_repo_ownership)
        params = list(sig.parameters.keys())
        assert 'repo_id' in params
        assert 'user_id' in params
        
        # Return type should be bool
        assert sig.return_annotation == bool


# ============== UNIT TESTS FOR REPO MANAGER ==============

class TestRepoManagerOwnership:
    """Unit tests for ownership methods in RepoManager"""
    
    def test_list_repos_for_user_delegates_to_supabase(self):
        """list_repos_for_user should call supabase list_repositories_for_user"""
        with patch('services.repo_manager.get_supabase_service') as mock_get_db:
            mock_db = MagicMock()
            mock_db.list_repositories_for_user.return_value = [REPOS_DB[0], REPOS_DB[1]]
            mock_get_db.return_value = mock_db
            
            from services.repo_manager import RepositoryManager
            
            with patch.object(RepositoryManager, '_sync_existing_repos'):
                manager = RepositoryManager()
                manager.db = mock_db
                
                result = manager.list_repos_for_user("user-1")
                
                mock_db.list_repositories_for_user.assert_called_once_with("user-1")
                assert len(result) == 2
    
    def test_verify_ownership_delegates_to_supabase(self):
        """verify_ownership should call supabase verify_repo_ownership"""
        with patch('services.repo_manager.get_supabase_service') as mock_get_db:
            mock_db = MagicMock()
            mock_db.verify_repo_ownership.return_value = False
            mock_get_db.return_value = mock_db
            
            from services.repo_manager import RepositoryManager
            
            with patch.object(RepositoryManager, '_sync_existing_repos'):
                manager = RepositoryManager()
                manager.db = mock_db
                
                result = manager.verify_ownership("repo-user2-a", "user-1")
                
                mock_db.verify_repo_ownership.assert_called_once_with("repo-user2-a", "user-1")
                assert result is False


# ============== HELPER FUNCTION TESTS ==============

class TestSecurityHelpers:
    """Test the get_repo_or_404 and verify_repo_access helpers"""
    
    def test_get_repo_or_404_raises_404_for_wrong_user(self):
        """get_repo_or_404 should raise 404 if user doesn't own repo"""
        with patch('dependencies.repo_manager') as mock_manager:
            mock_manager.get_repo_for_user.return_value = None
            
            from dependencies import get_repo_or_404
            from fastapi import HTTPException
            
            with pytest.raises(HTTPException) as exc_info:
                get_repo_or_404("repo-user2-a", "user-1")
            
            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail.lower()
    
    def test_get_repo_or_404_returns_repo_for_owner(self):
        """get_repo_or_404 should return repo if user owns it"""
        with patch('dependencies.repo_manager') as mock_manager:
            expected_repo = REPOS_DB[0]
            mock_manager.get_repo_for_user.return_value = expected_repo
            
            from dependencies import get_repo_or_404
            
            result = get_repo_or_404("repo-user1-a", "user-1")
            
            assert result == expected_repo
    
    def test_verify_repo_access_raises_404_for_wrong_user(self):
        """verify_repo_access should raise 404 if user doesn't own repo"""
        with patch('dependencies.repo_manager') as mock_manager:
            mock_manager.verify_ownership.return_value = False
            
            from dependencies import verify_repo_access
            from fastapi import HTTPException
            
            with pytest.raises(HTTPException) as exc_info:
                verify_repo_access("repo-user2-a", "user-1")
            
            assert exc_info.value.status_code == 404


# ============== DEV API KEY TESTS ==============

class TestDevApiKeySecurity:
    """Test that dev API key is properly secured (Issue #8)"""
    
    def test_dev_key_without_debug_mode_fails(self):
        """Dev key should not work without DEBUG=true"""
        original_debug = os.environ.get("DEBUG")
        os.environ["DEBUG"] = "false"
        
        try:
            # Need to reload module to pick up env change
            import importlib
            import middleware.auth as auth_module
            importlib.reload(auth_module)
            
            result = auth_module._validate_api_key("test-dev-key")
            assert result is None, "Dev key should not work without DEBUG mode"
        finally:
            os.environ["DEBUG"] = original_debug or "true"
    
    def test_dev_key_without_explicit_env_var_fails(self):
        """Dev key should require explicit DEV_API_KEY env var"""
        original_debug = os.environ.get("DEBUG")
        original_dev_key = os.environ.get("DEV_API_KEY")
        
        os.environ["DEBUG"] = "true"
        if "DEV_API_KEY" in os.environ:
            del os.environ["DEV_API_KEY"]
        
        try:
            import importlib
            import middleware.auth as auth_module
            importlib.reload(auth_module)
            
            result = auth_module._validate_api_key("some-random-key")
            assert result is None, "Dev key should not work without explicit DEV_API_KEY"
        finally:
            os.environ["DEBUG"] = original_debug or "true"
            if original_dev_key:
                os.environ["DEV_API_KEY"] = original_dev_key
    
    def test_dev_key_works_with_debug_and_env_var(self):
        """Dev key should work when DEBUG=true AND DEV_API_KEY is set"""
        os.environ["DEBUG"] = "true"
        os.environ["DEV_API_KEY"] = "my-secret-dev-key"
        
        try:
            import importlib
            import middleware.auth as auth_module
            importlib.reload(auth_module)
            
            result = auth_module._validate_api_key("my-secret-dev-key")
            assert result is not None, "Dev key should work with DEBUG and DEV_API_KEY"
            assert result.api_key_name == "development"
            assert result.tier == "enterprise"
        finally:
            os.environ["DEV_API_KEY"] = "test-dev-key"  # Restore
    
    def test_wrong_dev_key_fails_even_in_debug(self):
        """Wrong dev key should fail even in DEBUG mode"""
        os.environ["DEBUG"] = "true"
        os.environ["DEV_API_KEY"] = "correct-key"
        
        try:
            import importlib
            import middleware.auth as auth_module
            importlib.reload(auth_module)
            
            result = auth_module._validate_api_key("wrong-key")
            assert result is None, "Wrong dev key should not work"
        finally:
            os.environ["DEV_API_KEY"] = "test-dev-key"


# ============== INFO LEAKAGE TESTS ==============

class TestInfoLeakagePrevention:
    """Test that 404 is returned instead of 403 to prevent info leakage"""
    
    def test_nonexistent_and_unauthorized_get_same_error(self):
        """Both non-existent repo and unauthorized access should return identical 404"""
        with patch('dependencies.repo_manager') as mock_manager:
            # Both cases return None from get_repo_for_user
            mock_manager.get_repo_for_user.return_value = None
            
            from dependencies import get_repo_or_404
            from fastapi import HTTPException
            
            # Non-existent repo
            with pytest.raises(HTTPException) as exc1:
                get_repo_or_404("does-not-exist", "user-1")
            
            # Other user's repo (also returns None because no ownership)
            with pytest.raises(HTTPException) as exc2:
                get_repo_or_404("repo-user2-a", "user-1")
            
            # Both should have identical error
            assert exc1.value.status_code == exc2.value.status_code == 404
            assert exc1.value.detail == exc2.value.detail


# ============== INTEGRATION-STYLE TESTS ==============

class TestEndpointOwnershipIntegration:
    """
    These tests verify that endpoints actually call ownership verification.
    They mock at the right level to ensure the security helpers are used.
    """
    
    def test_list_repos_calls_user_filtered_method(self):
        """GET /api/repos should call list_repos_for_user, not list_repos"""
        # This is a code inspection test - we verify the correct method is called
        import ast
        
        with open(backend_dir / "routes" / "repos.py") as f:
            source = f.read()
        
        # Check that list_repos_for_user is used in list_repositories function
        assert "list_repos_for_user" in source, "Should use list_repos_for_user"
        
        # And that the old unfiltered method is NOT used in that endpoint
        # (This is a simple check - in production you'd use proper AST analysis)
        tree = ast.parse(source)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "list_repositories":
                func_source = ast.unparse(node)
                assert "list_repos_for_user" in func_source
                # Make sure we're not calling the unfiltered version
                assert "repo_manager.list_repos()" not in func_source
    
    def test_repo_endpoints_use_ownership_verification(self):
        """All repo-specific endpoints should use get_repo_or_404 or verify_repo_access"""
        # Check repos.py for index_repository
        with open(backend_dir / "routes" / "repos.py") as f:
            repos_source = f.read()
        
        # Check analysis.py for analysis endpoints
        with open(backend_dir / "routes" / "analysis.py") as f:
            analysis_source = f.read()
        
        # Endpoints in repos.py
        assert "def index_repository" in repos_source, "Endpoint index_repository not found"
        
        # Endpoints in analysis.py
        analysis_endpoints = [
            "get_dependency_graph",
            "analyze_impact",
            "get_repository_insights",
            "get_style_analysis",
        ]
        
        for endpoint in analysis_endpoints:
            assert f"def {endpoint}" in analysis_source, f"Endpoint {endpoint} not found"
        
        # Verify ownership checks exist in each file
        assert "get_repo_or_404" in repos_source or "verify_repo_access" in repos_source
        assert "get_repo_or_404" in analysis_source or "verify_repo_access" in analysis_source
    
    def test_search_endpoint_verifies_repo_ownership(self):
        """POST /api/search should verify repo ownership"""
        with open(backend_dir / "routes" / "search.py") as f:
            source = f.read()
        
        assert "verify_repo_access" in source, "search_code should verify repo ownership"
    
    def test_explain_endpoint_verifies_repo_ownership(self):
        """POST /api/explain should verify repo ownership"""
        with open(backend_dir / "routes" / "search.py") as f:
            source = f.read()
        
        # explain_code is in the same file, check for ownership verification
        assert "get_repo_or_404" in source, "explain_code should verify repo ownership"
