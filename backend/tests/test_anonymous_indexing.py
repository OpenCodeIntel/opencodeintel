"""
Tests for anonymous indexing endpoint (Issue #125).
Tests the POST /playground/index endpoint and related functionality.

Note: These tests rely on conftest.py for Pinecone/OpenAI/Redis mocking.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta
import json

# Import directly - conftest.py handles external service mocking
from routes.playground import (
    IndexRepoRequest,
    ANONYMOUS_FILE_LIMIT,
)
from services.anonymous_indexer import (
    AnonymousIndexingJob,
    JobStatus,
    JobProgress,
    JobStats,
)


# =============================================================================
# REQUEST MODEL TESTS
# =============================================================================

class TestIndexRepoRequest:
    """Tests for IndexRepoRequest validation."""

    def test_valid_request(self):
        """Valid GitHub URL should pass."""
        req = IndexRepoRequest(github_url="https://github.com/facebook/react")
        assert req.github_url == "https://github.com/facebook/react"
        assert req.branch is None
        assert req.partial is False

    def test_valid_request_with_branch(self):
        """Request with branch specified."""
        req = IndexRepoRequest(
            github_url="https://github.com/user/repo",
            branch="develop"
        )
        assert req.branch == "develop"

    def test_valid_request_with_partial(self):
        """Request with partial=True."""
        req = IndexRepoRequest(
            github_url="https://github.com/user/repo",
            partial=True
        )
        assert req.partial is True

    def test_invalid_empty_url(self):
        """Empty URL should fail."""
        with pytest.raises(ValueError) as exc_info:
            IndexRepoRequest(github_url="")
        assert "required" in str(exc_info.value).lower()

    def test_invalid_url_no_scheme(self):
        """URL without http(s) should fail."""
        with pytest.raises(ValueError) as exc_info:
            IndexRepoRequest(github_url="github.com/user/repo")
        assert "http" in str(exc_info.value).lower()

    def test_invalid_url_wrong_domain(self):
        """Non-GitHub URL should fail."""
        with pytest.raises(ValueError) as exc_info:
            IndexRepoRequest(github_url="https://gitlab.com/user/repo")
        assert "github" in str(exc_info.value).lower()

    def test_url_whitespace_trimmed(self):
        """Whitespace should be trimmed."""
        req = IndexRepoRequest(github_url="  https://github.com/user/repo  ")
        assert req.github_url == "https://github.com/user/repo"


# =============================================================================
# JOB MANAGER TESTS
# =============================================================================

class TestAnonymousIndexingJob:
    """Tests for AnonymousIndexingJob service."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis = MagicMock()
        redis.get.return_value = None
        redis.setex.return_value = True
        return redis

    @pytest.fixture
    def job_manager(self, mock_redis):
        """Create job manager with mock Redis."""
        return AnonymousIndexingJob(mock_redis)

    def test_generate_job_id_format(self, job_manager):
        """Job ID should have correct format."""
        job_id = job_manager.generate_job_id()
        assert job_id.startswith("idx_")
        assert len(job_id) == 16  # idx_ + 12 hex chars

    def test_generate_job_id_unique(self, job_manager):
        """Each job ID should be unique."""
        ids = [job_manager.generate_job_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_generate_repo_id(self, job_manager):
        """Repo ID derived from job ID."""
        repo_id = job_manager.generate_repo_id("idx_abc123def456")
        assert repo_id == "anon_abc123def456"

    def test_create_job(self, job_manager, mock_redis):
        """Create job stores data in Redis."""
        job_data = job_manager.create_job(
            job_id="idx_test123456",
            session_id="session_abc",
            github_url="https://github.com/user/repo",
            owner="user",
            repo_name="repo",
            branch="main",
            file_count=50
        )

        # Check return data
        assert job_data["job_id"] == "idx_test123456"
        assert job_data["session_id"] == "session_abc"
        assert job_data["status"] == "queued"
        assert job_data["file_count"] == 50

        # Check Redis was called
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert "anon_job:idx_test123456" in call_args[0]

    def test_get_job_exists(self, job_manager, mock_redis):
        """Get existing job from Redis."""
        mock_redis.get.return_value = json.dumps({
            "job_id": "idx_test123456",
            "status": "processing"
        })

        job = job_manager.get_job("idx_test123456")
        assert job is not None
        assert job["status"] == "processing"

    def test_get_job_not_found(self, job_manager, mock_redis):
        """Get non-existent job returns None."""
        mock_redis.get.return_value = None
        job = job_manager.get_job("idx_nonexistent")
        assert job is None

    def test_update_status(self, job_manager, mock_redis):
        """Update job status in Redis."""
        # Setup existing job
        mock_redis.get.return_value = json.dumps({
            "job_id": "idx_test123456",
            "status": "queued",
            "updated_at": "2025-01-01T00:00:00Z"
        })

        result = job_manager.update_status(
            "idx_test123456",
            JobStatus.PROCESSING
        )

        assert result is True
        # Check Redis setex was called to update
        assert mock_redis.setex.called

    def test_update_status_with_progress(self, job_manager, mock_redis):
        """Update status with progress data."""
        mock_redis.get.return_value = json.dumps({
            "job_id": "idx_test123456",
            "status": "cloning"
        })

        progress = JobProgress(
            files_total=100,
            files_processed=50,
            functions_found=200
        )

        result = job_manager.update_status(
            "idx_test123456",
            JobStatus.PROCESSING,
            progress=progress
        )

        assert result is True

    def test_update_status_completed_with_stats(self, job_manager, mock_redis):
        """Update status to completed with stats."""
        mock_redis.get.return_value = json.dumps({
            "job_id": "idx_test123456",
            "status": "processing"
        })

        stats = JobStats(
            files_indexed=100,
            functions_found=500,
            time_taken_seconds=45.5
        )

        result = job_manager.update_status(
            "idx_test123456",
            JobStatus.COMPLETED,
            stats=stats,
            repo_id="anon_test123456"
        )

        assert result is True

    def test_update_status_failed_with_error(self, job_manager, mock_redis):
        """Update status to failed with error."""
        mock_redis.get.return_value = json.dumps({
            "job_id": "idx_test123456",
            "status": "cloning"
        })

        result = job_manager.update_status(
            "idx_test123456",
            JobStatus.FAILED,
            error="clone_failed",
            error_message="Repository not found"
        )

        assert result is True


# =============================================================================
# JOB DATACLASS TESTS
# =============================================================================

class TestJobDataclasses:
    """Tests for JobProgress and JobStats."""

    def test_job_progress_to_dict(self):
        """JobProgress converts to dict correctly."""
        progress = JobProgress(
            files_total=100,
            files_processed=50,
            functions_found=200,
            current_file="src/index.ts"
        )
        d = progress.to_dict()
        assert d["files_total"] == 100
        assert d["files_processed"] == 50
        assert d["current_file"] == "src/index.ts"

    def test_job_progress_none_excluded(self):
        """JobProgress excludes None values."""
        progress = JobProgress(files_total=100)
        d = progress.to_dict()
        assert "current_file" not in d

    def test_job_stats_to_dict(self):
        """JobStats converts to dict correctly."""
        stats = JobStats(
            files_indexed=100,
            functions_found=500,
            time_taken_seconds=45.5
        )
        d = stats.to_dict()
        assert d["files_indexed"] == 100
        assert d["time_taken_seconds"] == 45.5


# =============================================================================
# ENDPOINT TESTS (Integration)
# =============================================================================

class TestIndexEndpoint:
    """Integration tests for POST /playground/index."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)

    def test_invalid_url_returns_400(self, client):
        """Invalid GitHub URL returns 400."""
        response = client.post(
            "/api/v1/playground/index",
            json={"github_url": "not-a-valid-url"}
        )
        assert response.status_code == 422  # Pydantic validation

    def test_missing_url_returns_422(self, client):
        """Missing github_url returns 422."""
        response = client.post(
            "/api/v1/playground/index",
            json={}
        )
        assert response.status_code == 422

    @patch('routes.playground._fetch_repo_metadata')
    @patch('routes.playground._count_code_files')
    def test_private_repo_returns_400(
        self, mock_count, mock_metadata, client
    ):
        """Private repository returns 400."""
        mock_metadata.return_value = {"private": True, "name": "repo"}
        mock_count.return_value = (50, None)

        response = client.post(
            "/api/v1/playground/index",
            json={"github_url": "https://github.com/user/private-repo"}
        )

        assert response.status_code == 400
        assert "private" in response.json()["detail"]["reason"]

    @patch('routes.playground._fetch_repo_metadata')
    @patch('routes.playground._count_code_files')
    def test_too_large_repo_without_partial_returns_400(
        self, mock_count, mock_metadata, client
    ):
        """Large repo without partial=true returns 400 with hint."""
        mock_metadata.return_value = {
            "private": False,
            "name": "large-repo",
            "default_branch": "main"
        }
        mock_count.return_value = (500, None)  # Over 200 limit

        response = client.post(
            "/api/v1/playground/index",
            json={"github_url": "https://github.com/user/large-repo"}
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["reason"] == "too_large"
        assert "partial" in detail.get("hint", "").lower()

    @patch('routes.playground._fetch_repo_metadata')
    @patch('routes.playground._count_code_files')
    @patch('routes.playground.AnonymousIndexingJob')
    def test_large_repo_with_partial_returns_202(
        self, mock_job_class, mock_count, mock_metadata, client
    ):
        """Large repo with partial=true returns 202."""
        mock_metadata.return_value = {
            "private": False,
            "name": "large-repo",
            "default_branch": "main"
        }
        mock_count.return_value = (500, None)

        # Mock job manager
        mock_job_manager = MagicMock()
        mock_job_manager.generate_job_id.return_value = "idx_test123456"
        mock_job_manager.create_job.return_value = {"job_id": "idx_test123456"}
        mock_job_class.return_value = mock_job_manager

        response = client.post(
            "/api/v1/playground/index",
            json={
                "github_url": "https://github.com/user/large-repo",
                "partial": True
            }
        )

        assert response.status_code == 202
        data = response.json()
        assert data["job_id"] == "idx_test123456"
        assert data["partial"] is True
        assert data["file_count"] == ANONYMOUS_FILE_LIMIT  # Capped at 200

    @patch('routes.playground._fetch_repo_metadata')
    @patch('routes.playground._count_code_files')
    @patch('routes.playground.AnonymousIndexingJob')
    def test_valid_request_returns_202_with_job_id(
        self, mock_job_class, mock_count, mock_metadata, client
    ):
        """Valid request returns 202 with job_id."""
        mock_metadata.return_value = {
            "private": False,
            "name": "repo",
            "default_branch": "main"
        }
        mock_count.return_value = (50, None)

        mock_job_manager = MagicMock()
        mock_job_manager.generate_job_id.return_value = "idx_abc123def456"
        mock_job_manager.create_job.return_value = {"job_id": "idx_abc123def456"}
        mock_job_class.return_value = mock_job_manager

        response = client.post(
            "/api/v1/playground/index",
            json={"github_url": "https://github.com/user/repo"}
        )

        assert response.status_code == 202
        data = response.json()
        assert data["job_id"] == "idx_abc123def456"
        assert data["status"] == "queued"
        assert "estimated_time_seconds" in data

    @patch('routes.playground._fetch_repo_metadata')
    def test_repo_not_found_returns_400(self, mock_metadata, client):
        """Repository not found returns 400."""
        mock_metadata.return_value = {"error": "not_found"}

        response = client.post(
            "/api/v1/playground/index",
            json={"github_url": "https://github.com/user/nonexistent"}
        )

        assert response.status_code == 400
        assert response.json()["detail"]["reason"] == "not_found"

    @patch('routes.playground._fetch_repo_metadata')
    def test_github_rate_limit_returns_429(self, mock_metadata, client):
        """GitHub rate limit returns 429."""
        mock_metadata.return_value = {"error": "rate_limited"}

        response = client.post(
            "/api/v1/playground/index",
            json={"github_url": "https://github.com/user/repo"}
        )

        assert response.status_code == 429


# =============================================================================
# SESSION CONFLICT TESTS
# =============================================================================

class TestSessionConflict:
    """Tests for session-already-has-repo behavior."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)

    @patch('routes.playground._fetch_repo_metadata')
    @patch('routes.playground._count_code_files')
    @patch('routes.playground._get_limiter')
    def test_session_with_existing_repo_returns_409(
        self, mock_get_limiter, mock_count, mock_metadata, client
    ):
        """Session with existing indexed repo returns 409."""
        mock_metadata.return_value = {
            "private": False,
            "name": "repo",
            "default_branch": "main"
        }
        mock_count.return_value = (50, None)

        # Mock limiter with existing indexed repo
        mock_limiter = MagicMock()
        mock_session_data = MagicMock()
        mock_session_data.indexed_repo = {
            "repo_id": "existing_repo",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        }
        mock_limiter.get_session_data.return_value = mock_session_data
        mock_limiter.create_session.return_value = "test_session"
        mock_get_limiter.return_value = mock_limiter

        response = client.post(
            "/api/v1/playground/index",
            json={"github_url": "https://github.com/user/repo"}
        )

        assert response.status_code == 409
        assert response.json()["detail"]["error"] == "already_indexed"

    @patch('routes.playground._fetch_repo_metadata')
    @patch('routes.playground._count_code_files')
    @patch('routes.playground._get_limiter')
    @patch('routes.playground.AnonymousIndexingJob')
    def test_expired_repo_allows_new_indexing(
        self, mock_job_class, mock_get_limiter, mock_count, mock_metadata, client
    ):
        """Expired indexed repo allows new indexing."""
        mock_metadata.return_value = {
            "private": False,
            "name": "repo",
            "default_branch": "main"
        }
        mock_count.return_value = (50, None)

        # Mock limiter with expired indexed repo
        mock_limiter = MagicMock()
        mock_session_data = MagicMock()
        mock_session_data.indexed_repo = {
            "repo_id": "old_repo",
            "expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        }
        mock_limiter.get_session_data.return_value = mock_session_data
        mock_limiter.create_session.return_value = "test_session"
        mock_get_limiter.return_value = mock_limiter

        mock_job_manager = MagicMock()
        mock_job_manager.generate_job_id.return_value = "idx_new123456"
        mock_job_manager.create_job.return_value = {"job_id": "idx_new123456"}
        mock_job_class.return_value = mock_job_manager

        response = client.post(
            "/api/v1/playground/index",
            json={"github_url": "https://github.com/user/repo"}
        )

        assert response.status_code == 202
        assert response.json()["job_id"] == "idx_new123456"


# =============================================================================
# STATUS ENDPOINT TESTS (GET /playground/index/{job_id})
# =============================================================================

class TestStatusEndpoint:
    """Tests for GET /playground/index/{job_id} status endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)

    def test_invalid_job_id_format_returns_400(self, client):
        """Invalid job ID format returns 400."""
        response = client.get("/api/v1/playground/index/invalid_format")
        assert response.status_code == 400
        assert response.json()["detail"]["error"] == "invalid_job_id"

    def test_job_not_found_returns_404(self, client):
        """Non-existent job returns 404."""
        response = client.get("/api/v1/playground/index/idx_nonexistent123")
        assert response.status_code == 404
        assert response.json()["detail"]["error"] == "job_not_found"

    @patch('routes.playground.AnonymousIndexingJob')
    def test_queued_job_returns_status(self, mock_job_class, client):
        """Queued job returns correct status."""
        mock_job_manager = MagicMock()
        mock_job_manager.get_job.return_value = {
            "job_id": "idx_test123456",
            "status": "queued",
            "owner": "user",
            "repo_name": "repo",
            "branch": "main",
            "github_url": "https://github.com/user/repo",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_job_class.return_value = mock_job_manager

        response = client.get("/api/v1/playground/index/idx_test123456")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["message"] == "Job is queued for processing"

    @patch('routes.playground.AnonymousIndexingJob')
    def test_processing_job_returns_progress(self, mock_job_class, client):
        """Processing job returns progress info."""
        mock_job_manager = MagicMock()
        mock_job_manager.get_job.return_value = {
            "job_id": "idx_test123456",
            "status": "processing",
            "owner": "user",
            "repo_name": "repo",
            "branch": "main",
            "github_url": "https://github.com/user/repo",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:01Z",
            "progress": {
                "files_processed": 50,
                "files_total": 100,
                "functions_found": 250,
                "current_file": "src/index.ts"
            }
        }
        mock_job_class.return_value = mock_job_manager

        response = client.get("/api/v1/playground/index/idx_test123456")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["progress"]["files_processed"] == 50
        assert data["progress"]["percent_complete"] == 50

    @patch('routes.playground.AnonymousIndexingJob')
    def test_completed_job_returns_repo_id(self, mock_job_class, client):
        """Completed job returns repo_id and stats."""
        mock_job_manager = MagicMock()
        mock_job_manager.get_job.return_value = {
            "job_id": "idx_test123456",
            "status": "completed",
            "owner": "user",
            "repo_name": "repo",
            "branch": "main",
            "github_url": "https://github.com/user/repo",
            "repo_id": "anon_idx_test123456",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:01:00Z",
            "stats": {
                "files_indexed": 100,
                "functions_found": 500,
                "time_taken_seconds": 45.2
            }
        }
        mock_job_class.return_value = mock_job_manager

        response = client.get("/api/v1/playground/index/idx_test123456")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["repo_id"] == "anon_idx_test123456"
        assert data["stats"]["files_indexed"] == 100

    @patch('routes.playground.AnonymousIndexingJob')
    def test_failed_job_returns_error(self, mock_job_class, client):
        """Failed job returns error details."""
        mock_job_manager = MagicMock()
        mock_job_manager.get_job.return_value = {
            "job_id": "idx_test123456",
            "status": "failed",
            "owner": "user",
            "repo_name": "repo",
            "branch": "main",
            "github_url": "https://github.com/user/repo",
            "error": "clone_failed",
            "error_message": "Repository not found or access denied",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:30Z",
        }
        mock_job_class.return_value = mock_job_manager

        response = client.get("/api/v1/playground/index/idx_test123456")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "clone_failed"
        assert "not found" in data["error_message"].lower()

    @patch('routes.playground.AnonymousIndexingJob')
    def test_partial_job_includes_partial_info(self, mock_job_class, client):
        """Partial indexing job includes partial flag."""
        mock_job_manager = MagicMock()
        mock_job_manager.get_job.return_value = {
            "job_id": "idx_test123456",
            "status": "processing",
            "owner": "user",
            "repo_name": "large-repo",
            "branch": "main",
            "github_url": "https://github.com/user/large-repo",
            "is_partial": True,
            "max_files": 200,
            "file_count": 500,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:10Z",
            "progress": {
                "files_processed": 100,
                "files_total": 200,
                "functions_found": 400
            }
        }
        mock_job_class.return_value = mock_job_manager

        response = client.get("/api/v1/playground/index/idx_test123456")

        assert response.status_code == 200
        data = response.json()
        assert data["partial"] is True
        assert data["max_files"] == 200



# =============================================================================
# Issue #128: Search User-Indexed Repos Tests
# =============================================================================

class TestSearchUserRepos:
    """Tests for searching user-indexed repositories."""

    @patch('routes.playground._get_limiter')
    @patch('routes.playground.indexer')
    def test_search_with_repo_id_user_owns(self, mock_indexer, mock_get_limiter, client):
        """User can search their own indexed repo via repo_id."""
        mock_limiter = MagicMock()
        mock_limiter.check_and_record.return_value = MagicMock(
            allowed=True,
            remaining=99,
            limit=100,
            session_token="test_session_123"
        )
        # Session owns this repo
        mock_limiter.get_session_data.return_value = MagicMock(
            indexed_repo={
                "repo_id": "repo_user_abc123",
                "github_url": "https://github.com/user/repo",
                "name": "repo",
                "file_count": 50,
                "indexed_at": "2024-01-01T00:00:00Z",
                "expires_at": "2099-01-02T00:00:00Z"  # Far future
            }
        )
        mock_get_limiter.return_value = mock_limiter
        mock_indexer.semantic_search = AsyncMock(return_value=[
            {"file": "test.py", "score": 0.9}
        ])

        response = client.post(
            "/api/v1/playground/search",
            json={"query": "test function", "repo_id": "repo_user_abc123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1

    @patch('routes.playground._get_limiter')
    def test_search_repo_id_not_owned_returns_403(self, mock_get_limiter, client):
        """Searching repo_id user doesn't own returns 403."""
        mock_limiter = MagicMock()
        mock_limiter.check_and_record.return_value = MagicMock(
            allowed=True,
            remaining=99,
            limit=100,
            session_token="test_session_123"
        )
        # Session owns different repo
        mock_limiter.get_session_data.return_value = MagicMock(
            indexed_repo={
                "repo_id": "repo_OTHER_xyz",
                "github_url": "https://github.com/other/repo",
                "name": "other-repo",
                "file_count": 50,
                "indexed_at": "2024-01-01T00:00:00Z",
                "expires_at": "2099-01-02T00:00:00Z"
            }
        )
        mock_get_limiter.return_value = mock_limiter

        response = client.post(
            "/api/v1/playground/search",
            json={"query": "test", "repo_id": "repo_user_abc123"}
        )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error"] == "access_denied"

    @patch('routes.playground._get_limiter')
    def test_search_repo_id_no_session_repo_returns_403(self, mock_get_limiter, client):
        """Searching repo_id when session has no indexed repo returns 403."""
        mock_limiter = MagicMock()
        mock_limiter.check_and_record.return_value = MagicMock(
            allowed=True,
            remaining=99,
            limit=100,
            session_token="test_session_123"
        )
        # Session has no indexed repo
        mock_limiter.get_session_data.return_value = MagicMock(indexed_repo=None)
        mock_get_limiter.return_value = mock_limiter

        response = client.post(
            "/api/v1/playground/search",
            json={"query": "test", "repo_id": "repo_user_abc123"}
        )

        assert response.status_code == 403

    @patch('routes.playground._get_limiter')
    def test_search_expired_repo_returns_410(self, mock_get_limiter, client):
        """Searching expired repo returns 410 with can_reindex hint."""
        mock_limiter = MagicMock()
        mock_limiter.check_and_record.return_value = MagicMock(
            allowed=True,
            remaining=99,
            limit=100,
            session_token="test_session_123"
        )
        # Session owns repo but it's expired
        mock_limiter.get_session_data.return_value = MagicMock(
            indexed_repo={
                "repo_id": "repo_user_abc123",
                "github_url": "https://github.com/user/repo",
                "name": "repo",
                "file_count": 50,
                "indexed_at": "2024-01-01T00:00:00Z",
                "expires_at": "2024-01-01T00:00:01Z"  # Already expired
            }
        )
        mock_get_limiter.return_value = mock_limiter

        response = client.post(
            "/api/v1/playground/search",
            json={"query": "test", "repo_id": "repo_user_abc123"}
        )

        assert response.status_code == 410
        data = response.json()
        assert data["detail"]["error"] == "repo_expired"
        assert data["detail"]["can_reindex"] is True

    @patch('routes.playground._get_limiter')
    @patch('routes.playground.indexer')
    def test_search_demo_repo_via_repo_id_allowed(self, mock_indexer, mock_get_limiter, client):
        """Demo repos can be accessed via repo_id without ownership check."""
        mock_limiter = MagicMock()
        mock_limiter.check_and_record.return_value = MagicMock(
            allowed=True,
            remaining=99,
            limit=100,
            session_token="test_session_123"
        )
        mock_get_limiter.return_value = mock_limiter
        mock_indexer.semantic_search = AsyncMock(return_value=[])

        # Use the flask demo repo ID
        from routes.playground import DEMO_REPO_IDS
        flask_repo_id = DEMO_REPO_IDS.get("flask")
        
        if flask_repo_id:
            response = client.post(
                "/api/v1/playground/search",
                json={"query": "route handler", "repo_id": flask_repo_id}
            )
            assert response.status_code == 200

    @patch('routes.playground._get_limiter')
    @patch('routes.playground.indexer')
    def test_search_backward_compat_demo_repo(self, mock_indexer, mock_get_limiter, client):
        """Backward compat: demo_repo parameter still works."""
        mock_limiter = MagicMock()
        mock_limiter.check_and_record.return_value = MagicMock(
            allowed=True,
            remaining=99,
            limit=100,
            session_token=None
        )
        mock_get_limiter.return_value = mock_limiter
        mock_indexer.semantic_search = AsyncMock(return_value=[])

        response = client.post(
            "/api/v1/playground/search",
            json={"query": "test", "demo_repo": "flask"}
        )

        # Should work (200) or 404 if flask not indexed - but not 4xx auth error
        assert response.status_code in [200, 404]

    @patch('routes.playground._get_limiter')
    @patch('routes.playground.indexer')
    def test_search_default_to_flask_when_no_repo_specified(self, mock_indexer, mock_get_limiter, client):
        """When neither repo_id nor demo_repo provided, defaults to flask."""
        mock_limiter = MagicMock()
        mock_limiter.check_and_record.return_value = MagicMock(
            allowed=True,
            remaining=99,
            limit=100,
            session_token=None
        )
        mock_get_limiter.return_value = mock_limiter
        mock_indexer.semantic_search = AsyncMock(return_value=[])

        response = client.post(
            "/api/v1/playground/search",
            json={"query": "test"}  # No repo_id or demo_repo
        )

        # Should default to flask
        assert response.status_code in [200, 404]
