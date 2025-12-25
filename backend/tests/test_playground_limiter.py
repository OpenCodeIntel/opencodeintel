"""
Test Suite for Playground Session Management
Issue #127 - Anonymous session management

Tests:
- Session data retrieval
- Indexed repo storage
- Legacy session migration
- Rate limiting with hash storage
"""
import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from services.playground_limiter import (
    PlaygroundLimiter,
    SessionData,
    IndexedRepoData,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_redis():
    """Create a mock Redis client with hash support."""
    redis = MagicMock()

    # Default behaviors
    redis.type.return_value = b'hash'
    redis.hgetall.return_value = {}
    redis.hget.return_value = None
    redis.hset.return_value = 1
    redis.hincrby.return_value = 1
    redis.hexists.return_value = False
    redis.hdel.return_value = 1
    redis.ttl.return_value = 86400
    redis.expire.return_value = True
    redis.delete.return_value = 1
    redis.get.return_value = None
    redis.incr.return_value = 1

    return redis


@pytest.fixture
def limiter(mock_redis):
    """Create a PlaygroundLimiter with mocked Redis."""
    return PlaygroundLimiter(redis_client=mock_redis)


@pytest.fixture
def limiter_no_redis():
    """Create a PlaygroundLimiter without Redis (fail-open mode)."""
    return PlaygroundLimiter(redis_client=None)


@pytest.fixture
def sample_indexed_repo():
    """Sample indexed repo data."""
    return {
        "repo_id": "repo_abc123",
        "github_url": "https://github.com/pallets/flask",
        "name": "flask",
        "file_count": 198,
        "indexed_at": "2025-12-24T10:05:00Z",
        "expires_at": "2025-12-25T10:05:00Z",
    }


# =============================================================================
# DATA CLASS TESTS
# =============================================================================

class TestIndexedRepoData:
    """Tests for IndexedRepoData dataclass."""

    def test_from_dict(self, sample_indexed_repo):
        """Should create IndexedRepoData from dictionary."""
        repo = IndexedRepoData.from_dict(sample_indexed_repo)

        assert repo.repo_id == "repo_abc123"
        assert repo.name == "flask"
        assert repo.file_count == 198

    def test_to_dict(self, sample_indexed_repo):
        """Should convert to dictionary."""
        repo = IndexedRepoData.from_dict(sample_indexed_repo)
        result = repo.to_dict()

        assert result == sample_indexed_repo

    def test_is_expired_false(self):
        """Should return False for non-expired repo."""
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        repo = IndexedRepoData(
            repo_id="abc",
            github_url="https://github.com/user/repo",
            name="repo",
            file_count=100,
            indexed_at="2025-12-24T10:00:00Z",
            expires_at=future,
        )

        assert repo.is_expired() is False

    def test_is_expired_true(self):
        """Should return True for expired repo."""
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        repo = IndexedRepoData(
            repo_id="abc",
            github_url="https://github.com/user/repo",
            name="repo",
            file_count=100,
            indexed_at="2025-12-24T10:00:00Z",
            expires_at=past,
        )

        assert repo.is_expired() is True


class TestSessionData:
    """Tests for SessionData dataclass."""

    def test_to_response_empty(self):
        """Should format empty session correctly."""
        session = SessionData()
        result = session.to_response(limit=50)

        assert result["session_id"] is None
        assert result["indexed_repo"] is None
        assert result["searches"]["used"] == 0
        assert result["searches"]["limit"] == 50
        assert result["searches"]["remaining"] == 50

    def test_to_response_with_data(self, sample_indexed_repo):
        """Should format session with data correctly."""
        now = datetime.now(timezone.utc)
        session = SessionData(
            session_id="abc123def456ghi789",
            searches_used=12,
            created_at=now,
            expires_at=now + timedelta(days=1),
            indexed_repo=sample_indexed_repo,
        )
        result = session.to_response(limit=50)

        assert result["session_id"] == "abc123de..."  # Truncated (first 8 chars)
        assert result["searches"]["used"] == 12
        assert result["searches"]["remaining"] == 38
        assert result["indexed_repo"] == sample_indexed_repo

    def test_truncate_id(self):
        """Should truncate long session IDs."""
        assert SessionData._truncate_id("short") == "short"
        assert SessionData._truncate_id("verylongsessiontoken123") == "verylong..."


# =============================================================================
# GET SESSION DATA TESTS
# =============================================================================

class TestGetSessionData:
    """Tests for get_session_data() method."""

    def test_no_token_returns_empty(self, limiter):
        """Should return empty SessionData when token is None."""
        result = limiter.get_session_data(None)

        assert result.session_id is None
        assert result.searches_used == 0
        assert result.indexed_repo is None

    def test_no_redis_returns_session_id_only(self, limiter_no_redis):
        """Should return partial data when Redis unavailable."""
        result = limiter_no_redis.get_session_data("some_token")

        assert result.session_id == "some_token"
        assert result.searches_used == 0

    def test_session_not_found(self, limiter, mock_redis):
        """Should return empty SessionData for non-existent session."""
        mock_redis.hgetall.return_value = {}

        result = limiter.get_session_data("nonexistent_token")

        assert result.session_id is None

    def test_session_with_searches(self, limiter, mock_redis):
        """Should return correct search count."""
        mock_redis.hgetall.return_value = {
            b'searches_used': b'15',
            b'created_at': b'2025-12-24T10:00:00Z',
        }

        result = limiter.get_session_data("valid_token")

        assert result.session_id == "valid_token"
        assert result.searches_used == 15

    def test_session_with_indexed_repo(self, limiter, mock_redis, sample_indexed_repo):
        """Should parse indexed_repo JSON correctly."""
        mock_redis.hgetall.return_value = {
            b'searches_used': b'5',
            b'created_at': b'2025-12-24T10:00:00Z',
            b'indexed_repo': json.dumps(sample_indexed_repo).encode(),
        }

        result = limiter.get_session_data("token_with_repo")

        assert result.indexed_repo is not None
        assert result.indexed_repo["repo_id"] == "repo_abc123"
        assert result.indexed_repo["name"] == "flask"

    def test_invalid_indexed_repo_json(self, limiter, mock_redis):
        """Should handle invalid JSON gracefully."""
        mock_redis.hgetall.return_value = {
            b'searches_used': b'5',
            b'indexed_repo': b'not valid json{{{',
        }

        result = limiter.get_session_data("token")

        assert result.indexed_repo is None  # Graceful fallback
        assert result.searches_used == 5


# =============================================================================
# SET INDEXED REPO TESTS
# =============================================================================

class TestSetIndexedRepo:
    """Tests for set_indexed_repo() method."""

    def test_no_token_returns_false(self, limiter):
        """Should return False when token is None."""
        result = limiter.set_indexed_repo(None, {"repo_id": "abc"})

        assert result is False

    def test_no_redis_returns_false(self, limiter_no_redis):
        """Should return False when Redis unavailable."""
        result = limiter_no_redis.set_indexed_repo("token", {"repo_id": "abc"})

        assert result is False

    def test_successful_set(self, limiter, mock_redis, sample_indexed_repo):
        """Should store indexed repo successfully."""
        result = limiter.set_indexed_repo("valid_token", sample_indexed_repo)

        assert result is True
        mock_redis.hset.assert_called()

        # Verify the JSON was stored
        call_args = mock_redis.hset.call_args
        stored_json = call_args[0][2]  # Third argument is the value
        stored_data = json.loads(stored_json)
        assert stored_data["repo_id"] == "repo_abc123"

    def test_preserves_other_fields(self, limiter, mock_redis, sample_indexed_repo):
        """Should not overwrite other session fields."""
        # Verify we use hset (field-level) not set (full replace)
        limiter.set_indexed_repo("token", sample_indexed_repo)

        # Should call hset, not set
        assert mock_redis.hset.called
        assert not mock_redis.set.called


# =============================================================================
# HAS INDEXED REPO TESTS
# =============================================================================

class TestHasIndexedRepo:
    """Tests for has_indexed_repo() method."""

    def test_no_token_returns_false(self, limiter):
        """Should return False when token is None."""
        assert limiter.has_indexed_repo(None) is False
        assert limiter.has_indexed_repo("") is False

    def test_no_redis_returns_false(self, limiter_no_redis):
        """Should return False when Redis unavailable."""
        assert limiter_no_redis.has_indexed_repo("token") is False

    def test_repo_exists(self, limiter, mock_redis):
        """Should return True when repo exists."""
        mock_redis.hexists.return_value = True

        assert limiter.has_indexed_repo("token") is True
        mock_redis.hexists.assert_called_with(
            "playground:session:token",
            "indexed_repo"
        )

    def test_repo_not_exists(self, limiter, mock_redis):
        """Should return False when repo doesn't exist."""
        mock_redis.hexists.return_value = False

        assert limiter.has_indexed_repo("token") is False


# =============================================================================
# CLEAR INDEXED REPO TESTS
# =============================================================================

class TestClearIndexedRepo:
    """Tests for clear_indexed_repo() method."""

    def test_successful_clear(self, limiter, mock_redis):
        """Should clear indexed repo successfully."""
        result = limiter.clear_indexed_repo("valid_token")

        assert result is True
        mock_redis.hdel.assert_called_with(
            "playground:session:valid_token",
            "indexed_repo"
        )

    def test_no_token_returns_false(self, limiter):
        """Should return False when token is None."""
        assert limiter.clear_indexed_repo(None) is False


# =============================================================================
# LEGACY MIGRATION TESTS
# =============================================================================

class TestLegacyMigration:
    """Tests for legacy string format migration."""

    def test_migrate_string_to_hash(self, limiter, mock_redis):
        """Should migrate legacy string format to hash."""
        # Simulate legacy string format
        mock_redis.type.return_value = b'string'
        mock_redis.get.return_value = b'25'  # Old count
        mock_redis.ttl.return_value = 3600

        limiter._ensure_hash_format("legacy_token")

        # Verify migration happened
        mock_redis.delete.assert_called()
        mock_redis.hset.assert_called()
        mock_redis.expire.assert_called_with(
            "playground:session:legacy_token",
            3600
        )

    def test_already_hash_no_migration(self, limiter, mock_redis):
        """Should not migrate if already hash format."""
        mock_redis.type.return_value = b'hash'

        limiter._ensure_hash_format("hash_token")

        # Should NOT call delete (no migration needed)
        mock_redis.delete.assert_not_called()

    def test_nonexistent_key_no_error(self, limiter, mock_redis):
        """Should handle non-existent keys gracefully."""
        mock_redis.type.return_value = b'none'

        # Should not raise
        limiter._ensure_hash_format("new_token")


# =============================================================================
# RATE LIMITING WITH HASH STORAGE TESTS
# =============================================================================

class TestRateLimitingWithHash:
    """Tests to verify rate limiting still works with hash storage."""

    def test_check_and_record_uses_hincrby(self, limiter, mock_redis):
        """check_and_record should use HINCRBY for atomic increment."""
        mock_redis.hincrby.return_value = 5

        result = limiter.check_and_record("token", "127.0.0.1")

        assert result.allowed is True
        assert result.remaining == 45  # 50 - 5
        mock_redis.hincrby.assert_called()

    def test_session_limit_enforced(self, limiter, mock_redis):
        """Should enforce session limit with hash storage."""
        mock_redis.hincrby.return_value = 51  # Over limit

        result = limiter.check_and_record("token", "127.0.0.1")

        assert result.allowed is False
        assert result.remaining == 0

    def test_new_session_creates_hash(self, limiter, mock_redis):
        """New sessions should be created with hash structure."""
        mock_redis.type.return_value = b'none'  # Key doesn't exist

        result = limiter.check_and_record(None, "127.0.0.1")

        assert result.allowed is True
        assert result.session_token is not None
        # Should create hash with hset
        mock_redis.hset.assert_called()


# =============================================================================
# CREATE SESSION TESTS
# =============================================================================

class TestCreateSession:
    """Tests for create_session() method."""

    def test_successful_create(self, limiter, mock_redis):
        """Should create session with initial values."""
        result = limiter.create_session("new_token")

        assert result is True
        mock_redis.hset.assert_called()
        mock_redis.expire.assert_called_with(
            "playground:session:new_token",
            86400  # TTL_DAY
        )

    def test_no_token_returns_false(self, limiter):
        """Should return False for empty token."""
        assert limiter.create_session(None) is False
        assert limiter.create_session("") is False

    def test_no_redis_returns_false(self, limiter_no_redis):
        """Should return False when Redis unavailable."""
        assert limiter_no_redis.create_session("token") is False


# =============================================================================
# HELPER METHOD TESTS
# =============================================================================

class TestHelperMethods:
    """Tests for helper methods."""

    def test_decode_hash_data_bytes(self, limiter):
        """Should decode bytes from Redis."""
        raw = {b'key1': b'value1', b'key2': b'value2'}
        result = limiter._decode_hash_data(raw)

        assert result == {'key1': 'value1', 'key2': 'value2'}

    def test_decode_hash_data_strings(self, limiter):
        """Should handle already-decoded strings."""
        raw = {'key1': 'value1', 'key2': 'value2'}
        result = limiter._decode_hash_data(raw)

        assert result == {'key1': 'value1', 'key2': 'value2'}

    def test_generate_session_token(self, limiter):
        """Should generate unique tokens."""
        token1 = limiter._generate_session_token()
        token2 = limiter._generate_session_token()

        assert token1 != token2
        assert len(token1) > 20  # Should be reasonably long


# =============================================================================
# INTEGRATION-STYLE TESTS
# =============================================================================

class TestSessionWorkflow:
    """End-to-end workflow tests."""

    def test_full_session_lifecycle(self, mock_redis):
        """Test complete session lifecycle: create → search → index → search."""
        limiter = PlaygroundLimiter(redis_client=mock_redis)

        # 1. First search creates session
        mock_redis.hincrby.return_value = 1
        result = limiter.check_and_record(None, "127.0.0.1")
        assert result.allowed is True
        token = result.session_token
        assert token is not None

        # 2. Check session data
        mock_redis.hgetall.return_value = {
            b'searches_used': b'1',
            b'created_at': b'2025-12-24T10:00:00Z',
        }
        session = limiter.get_session_data(token)
        assert session.searches_used == 1
        assert session.indexed_repo is None

        # 3. User has no repo yet
        mock_redis.hexists.return_value = False
        assert limiter.has_indexed_repo(token) is False

        # 4. Index a repo
        repo_data = {
            "repo_id": "repo_123",
            "github_url": "https://github.com/user/repo",
            "name": "repo",
            "file_count": 150,
            "indexed_at": "2025-12-24T10:05:00Z",
            "expires_at": "2025-12-25T10:05:00Z",
        }
        assert limiter.set_indexed_repo(token, repo_data) is True

        # 5. Now has repo
        mock_redis.hexists.return_value = True
        assert limiter.has_indexed_repo(token) is True

        # 6. More searches
        mock_redis.hincrby.return_value = 10
        result = limiter.check_and_record(token, "127.0.0.1")
        assert result.allowed is True
        assert result.remaining == 40


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
