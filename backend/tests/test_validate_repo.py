"""
Tests for the validate-repo endpoint (Issue #124).
Tests GitHub URL validation for anonymous indexing.

Note: These tests rely on conftest.py for Pinecone/OpenAI mocking.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Import directly - conftest.py handles external service mocking
from routes.playground import (
    _parse_github_url,
    GITHUB_URL_PATTERN,
    ANONYMOUS_FILE_LIMIT,
    ValidateRepoRequest,
)


# =============================================================================
# URL PARSING TESTS
# =============================================================================

class TestParseGitHubUrl:
    """Tests for URL parsing."""

    def test_valid_https_url(self):
        owner, repo, error = _parse_github_url("https://github.com/facebook/react")
        assert owner == "facebook"
        assert repo == "react"
        assert error is None

    def test_valid_http_url(self):
        owner, repo, error = _parse_github_url("http://github.com/user/repo")
        assert owner == "user"
        assert repo == "repo"
        assert error is None

    def test_url_with_trailing_slash(self):
        owner, repo, error = _parse_github_url("https://github.com/owner/repo/")
        assert owner == "owner"
        assert repo == "repo"
        assert error is None

    def test_url_with_dots_and_dashes(self):
        owner, repo, error = _parse_github_url(
            "https://github.com/my-org/my.repo-name"
        )
        assert owner == "my-org"
        assert repo == "my.repo-name"
        assert error is None

    def test_invalid_url_wrong_domain(self):
        owner, repo, error = _parse_github_url("https://gitlab.com/user/repo")
        assert owner is None
        assert repo is None
        assert "Invalid GitHub URL format" in error

    def test_invalid_url_no_repo(self):
        owner, repo, error = _parse_github_url("https://github.com/justowner")
        assert owner is None
        assert error is not None

    def test_invalid_url_with_path(self):
        owner, repo, error = _parse_github_url(
            "https://github.com/owner/repo/tree/main"
        )
        assert owner is None
        assert error is not None

    def test_invalid_url_blob_path(self):
        owner, repo, error = _parse_github_url(
            "https://github.com/owner/repo/blob/main/file.py"
        )
        assert owner is None
        assert error is not None


class TestGitHubUrlPattern:
    """Tests for the regex pattern."""

    def test_pattern_matches_standard(self):
        match = GITHUB_URL_PATTERN.match("https://github.com/user/repo")
        assert match is not None
        assert match.group("owner") == "user"
        assert match.group("repo") == "repo"

    def test_pattern_rejects_subpath(self):
        match = GITHUB_URL_PATTERN.match("https://github.com/user/repo/issues")
        assert match is None


# =============================================================================
# REQUEST MODEL TESTS
# =============================================================================

class TestValidateRepoRequest:
    """Tests for the request model validation."""

    def test_invalid_url_format(self):
        """Test with malformed URL."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ValidateRepoRequest(github_url="not-a-url")

    def test_non_github_url(self):
        """Test with non-GitHub URL."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ValidateRepoRequest(github_url="https://gitlab.com/user/repo")

    def test_empty_url(self):
        """Test with empty URL."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ValidateRepoRequest(github_url="")

    def test_valid_request_model(self):
        """Test valid request passes validation."""
        req = ValidateRepoRequest(github_url="https://github.com/user/repo")
        assert req.github_url == "https://github.com/user/repo"

    def test_url_with_whitespace_trimmed(self):
        """Test that whitespace is trimmed."""
        req = ValidateRepoRequest(github_url="  https://github.com/user/repo  ")
        assert req.github_url == "https://github.com/user/repo"


# =============================================================================
# GITHUB API TESTS
# =============================================================================

class TestFetchRepoMetadata:
    """Tests for GitHub API interaction."""

    @pytest.mark.asyncio
    async def test_repo_not_found(self):
        """Test handling of 404 response."""
        from routes.playground import _fetch_repo_metadata

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("routes.playground.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await _fetch_repo_metadata("nonexistent", "repo")
            assert result["error"] == "not_found"

    @pytest.mark.asyncio
    async def test_rate_limited(self):
        """Test handling of 403 rate limit response."""
        from routes.playground import _fetch_repo_metadata

        mock_response = MagicMock()
        mock_response.status_code = 403

        with patch("routes.playground.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await _fetch_repo_metadata("user", "repo")
            assert result["error"] == "rate_limited"

    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        """Test successful metadata fetch."""
        from routes.playground import _fetch_repo_metadata

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "repo",
            "owner": {"login": "user"},
            "private": False,
            "default_branch": "main",
            "stargazers_count": 100,
            "language": "Python",
            "size": 1024,
        }

        with patch("routes.playground.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await _fetch_repo_metadata("user", "repo")
            assert result["name"] == "repo"
            assert result["private"] is False
            assert result["stargazers_count"] == 100

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout is handled gracefully."""
        from routes.playground import _fetch_repo_metadata
        import httpx

        with patch("routes.playground.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.TimeoutException("timeout")
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await _fetch_repo_metadata("user", "repo")
            assert result["error"] == "timeout"


# =============================================================================
# FILE COUNTING TESTS
# =============================================================================

class TestCountCodeFiles:
    """Tests for file counting logic."""

    @pytest.mark.asyncio
    async def test_count_python_files(self):
        """Test counting Python files."""
        from routes.playground import _count_code_files

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "truncated": False,
            "tree": [
                {"type": "blob", "path": "app.py"},
                {"type": "blob", "path": "utils.py"},
                {"type": "blob", "path": "README.md"},  # Not code
                {"type": "tree", "path": "src"},  # Directory
            ]
        }

        with patch("routes.playground.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            count, error = await _count_code_files("user", "repo", "main")
            assert count == 2  # Only .py files
            assert error is None

    @pytest.mark.asyncio
    async def test_skip_node_modules(self):
        """Test that node_modules is skipped."""
        from routes.playground import _count_code_files

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "truncated": False,
            "tree": [
                {"type": "blob", "path": "index.js"},
                {"type": "blob", "path": "node_modules/lodash/index.js"},
                {"type": "blob", "path": "src/app.js"},
            ]
        }

        with patch("routes.playground.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            count, error = await _count_code_files("user", "repo", "main")
            assert count == 2  # index.js and src/app.js, not node_modules
            assert error is None

    @pytest.mark.asyncio
    async def test_truncated_tree(self):
        """Test handling of truncated tree response."""
        from routes.playground import _count_code_files

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "truncated": True,
            "tree": []
        }

        with patch("routes.playground.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            count, error = await _count_code_files("user", "repo", "main")
            assert count == -1
            assert error == "truncated"

    @pytest.mark.asyncio
    async def test_multiple_extensions(self):
        """Test counting multiple file types."""
        from routes.playground import _count_code_files

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "truncated": False,
            "tree": [
                {"type": "blob", "path": "app.py"},
                {"type": "blob", "path": "utils.js"},
                {"type": "blob", "path": "main.go"},
                {"type": "blob", "path": "lib.rs"},
                {"type": "blob", "path": "config.json"},  # Not code
                {"type": "blob", "path": "style.css"},  # Not code
            ]
        }

        with patch("routes.playground.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            count, error = await _count_code_files("user", "repo", "main")
            assert count == 4  # py, js, go, rs
            assert error is None

    @pytest.mark.asyncio
    async def test_skip_git_directory(self):
        """Test that .git directory is skipped."""
        from routes.playground import _count_code_files

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "truncated": False,
            "tree": [
                {"type": "blob", "path": "app.py"},
                {"type": "blob", "path": ".git/hooks/pre-commit.py"},
            ]
        }

        with patch("routes.playground.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            count, error = await _count_code_files("user", "repo", "main")
            assert count == 1  # Only app.py
            assert error is None


# =============================================================================
# CONSTANTS TESTS
# =============================================================================

class TestAnonymousFileLimit:
    """Tests for file limit constant."""

    def test_limit_value(self):
        """Verify anonymous file limit is 200."""
        assert ANONYMOUS_FILE_LIMIT == 200
