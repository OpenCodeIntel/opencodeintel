"""
Test Suite for Input Validation
"""
import pytest
from services.input_validator import InputValidator, CostController


class TestInputValidator:
    """Test input validation functions"""
    
    def test_valid_git_url(self):
        """Test valid Git URLs"""
        valid_urls = [
            "https://github.com/pmndrs/zustand",
            "https://github.com/user/repo.git",
            "git@github.com:user/repo.git",
        ]
        
        for url in valid_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert is_valid, f"Should accept valid URL: {url}, got error: {error}"
    
    def test_malicious_git_urls(self):
        """Test malicious Git URLs are blocked"""
        malicious_urls = [
            "file:///etc/passwd",
            "http://localhost/repo",
            "https://127.0.0.1/repo",
            "ftp://example.com/repo",
        ]
        
        for url in malicious_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"Should reject malicious URL: {url}"
            assert error is not None
    
    def test_path_traversal_prevention(self):
        """Test path traversal attacks are blocked"""
        malicious_paths = [
            "../../etc/passwd",
            "../../../secret.key",
            "~/private/file.txt",
            "/etc/passwd",
            "C:\\Windows\\System32",
        ]
        
        for path in malicious_paths:
            is_valid, error = InputValidator.validate_file_path(path)
            assert not is_valid, f"Should reject malicious path: {path}"
            assert error is not None
    
    def test_valid_file_paths(self):
        """Test valid file paths"""
        valid_paths = [
            "src/auth/middleware.py",
            "components/Button.tsx",
            "utils/helpers.js",
        ]
        
        for path in valid_paths:
            is_valid, error = InputValidator.validate_file_path(path)
            assert is_valid, f"Should accept valid path: {path}, got error: {error}"
    
    def test_search_query_validation(self):
        """Test search query validation"""
        # Valid queries
        assert InputValidator.validate_search_query("authentication logic")[0]
        assert InputValidator.validate_search_query("error handling in user service")[0]
        
        # Invalid queries
        assert not InputValidator.validate_search_query("")[0]  # Empty
        assert not InputValidator.validate_search_query("a" * 600)[0]  # Too long
        assert not InputValidator.validate_search_query("DROP TABLE users--")[0]  # SQL injection
    
    def test_repo_name_validation(self):
        """Test repository name validation"""
        # Valid names
        assert InputValidator.validate_repo_name("my-repo")[0]
        assert InputValidator.validate_repo_name("project_name")[0]
        assert InputValidator.validate_repo_name("repo.v2")[0]
        
        # Invalid names
        assert not InputValidator.validate_repo_name("../../../etc")[0]
        assert not InputValidator.validate_repo_name("repo with spaces")[0]
        assert not InputValidator.validate_repo_name("")[0]
    
    def test_string_sanitization(self):
        """Test string sanitization removes dangerous content"""
        # Null bytes
        assert '\x00' not in InputValidator.sanitize_string("hello\x00world")
        
        # Control characters
        sanitized = InputValidator.sanitize_string("test\x01\x02\x03data")
        assert '\x01' not in sanitized
        
        # Length limiting
        long_string = "a" * 1000
        sanitized = InputValidator.sanitize_string(long_string, max_length=100)
        assert len(sanitized) == 100
