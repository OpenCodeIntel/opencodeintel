"""
Professional Test Configuration
Proper dependency mocking for FastAPI testing
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import os

# Set test environment BEFORE imports
os.environ["DEBUG"] = "true"
os.environ["DEV_API_KEY"] = "test-secret-key"  # New env var for dev key
os.environ["API_KEY"] = "test-secret-key"  # Legacy support
os.environ["OPENAI_API_KEY"] = "sk-test-key"
os.environ["PINECONE_API_KEY"] = "pcsk-test"
os.environ["PINECONE_INDEX_NAME"] = "test-index"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_KEY"] = "test-key"
os.environ["SUPABASE_ANON_KEY"] = "test-anon-key"
os.environ["SUPABASE_JWT_SECRET"] = "test-jwt-secret"

# =============================================================================
# EARLY PATCHING - runs during collection, before any imports
# =============================================================================
# These patches prevent external service initialization during test collection

_pinecone_patcher = patch('pinecone.Pinecone')
_mock_pinecone = _pinecone_patcher.start()
_pc_instance = MagicMock()
_pc_instance.list_indexes.return_value.names.return_value = []
_pc_instance.Index.return_value = MagicMock()
_mock_pinecone.return_value = _pc_instance

_openai_patcher = patch('openai.AsyncOpenAI')
_mock_openai = _openai_patcher.start()
_openai_client = MagicMock()
_mock_openai.return_value = _openai_client

_supabase_patcher = patch('supabase.create_client')
_mock_supabase = _supabase_patcher.start()
_supabase_client = MagicMock()
_supabase_client.table.return_value.select.return_value.execute.return_value.data = []
# Auth should reject by default - set user to None
_auth_response = MagicMock()
_auth_response.user = None
_supabase_client.auth.get_user.return_value = _auth_response
_mock_supabase.return_value = _supabase_client

# =============================================================================

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


@pytest.fixture(scope="session", autouse=True)
def mock_openai():
    """Mock OpenAI client globally"""
    with patch('openai.AsyncOpenAI') as mock:
        client = MagicMock()
        embedding_response = MagicMock()
        embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
        client.embeddings.create.return_value = embedding_response
        mock.return_value = client
        yield mock


@pytest.fixture(scope="session", autouse=True)
def mock_pinecone():
    """Mock Pinecone client globally"""
    with patch('pinecone.Pinecone') as mock:
        pc_instance = MagicMock()
        index = MagicMock()
        index.query.return_value = {"matches": []}
        index.upsert.return_value = {"upserted_count": 0}
        pc_instance.Index.return_value = index
        mock.return_value = pc_instance
        yield mock


@pytest.fixture(scope="session", autouse=True)
def mock_redis():
    """
    Mock Redis client globally.

    Includes hash operations for session management (#127).
    """
    with patch('redis.Redis') as mock:
        redis_instance = MagicMock()

        # Connection
        redis_instance.ping.return_value = True

        # String operations (legacy + IP/global limits)
        redis_instance.get.return_value = None
        redis_instance.set.return_value = True
        redis_instance.incr.return_value = 1
        redis_instance.delete.return_value = 1

        # TTL operations
        redis_instance.expire.return_value = True
        redis_instance.ttl.return_value = 86400

        # Hash operations (session management #127)
        redis_instance.type.return_value = b'hash'
        redis_instance.hset.return_value = 1
        redis_instance.hget.return_value = b'0'
        redis_instance.hgetall.return_value = {
            b'searches_used': b'0',
            b'created_at': b'2025-12-24T10:00:00Z',
        }
        redis_instance.hincrby.return_value = 1
        redis_instance.hexists.return_value = False
        redis_instance.hdel.return_value = 1

        mock.return_value = redis_instance
        yield mock


@pytest.fixture(scope="session", autouse=True)
def mock_supabase():
    """Mock Supabase client globally"""
    with patch('supabase.create_client') as mock:
        client = MagicMock()
        table = MagicMock()

        # Mock the fluent interface for tables
        execute_result = MagicMock()
        execute_result.data = []
        execute_result.count = 0

        table.select.return_value = table
        table.insert.return_value = table
        table.update.return_value = table
        table.delete.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.upsert.return_value = table
        table.execute.return_value = execute_result

        client.table.return_value = table

        # Mock auth.get_user to reject invalid tokens
        # By default, return response with user=None (invalid token)
        auth_response = MagicMock()
        auth_response.user = None
        client.auth.get_user.return_value = auth_response

        mock.return_value = client
        yield mock


@pytest.fixture(scope="session", autouse=True)
def mock_git():
    """Mock Git operations"""
    with patch('git.Repo') as mock:
        repo = MagicMock()
        repo.head.commit.hexsha = "abc123"
        repo.active_branch.name = "main"
        mock.return_value = repo
        mock.clone_from.return_value = repo
        yield mock


@pytest.fixture
def client():
    """TestClient with mocked dependencies and auth bypass for testing"""
    from fastapi.testclient import TestClient
    from main import app
    from middleware.auth import AuthContext

    # Override the require_auth dependency to always return a valid context
    async def mock_require_auth():
        return AuthContext(
            user_id="test-user-123",
            email="test@example.com",
            tier="enterprise"
        )

    from middleware.auth import require_auth
    app.dependency_overrides[require_auth] = mock_require_auth

    yield TestClient(app)

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth():
    """TestClient WITHOUT auth bypass - for testing auth behavior"""
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)


@pytest.fixture
def valid_headers():
    """Valid auth headers (kept for compatibility with mocked auth)."""
    return {"Authorization": "Bearer test-secret-key"}


@pytest.fixture
def sample_repo_payload():
    """Sample repo data"""
    return {
        "name": "test-repo",
        "git_url": "https://github.com/pmndrs/zustand",
        "branch": "main"
    }


@pytest.fixture
def malicious_payloads():
    """Collection of malicious inputs for security testing"""
    return {
        "file_urls": [
            "file:///etc/passwd",
            "file://C:/Windows/System32"
        ],
        "localhost_urls": [
            "http://localhost/repo",
            "https://127.0.0.1/repo",
            "http://0.0.0.0/repo"
        ],
        "path_traversal": [
            "../../etc/passwd",
            "../../../secret.key",
            "~/private/data"
        ],
        "sql_injection": [
            "DROP TABLE users--",
            "'; DELETE FROM repos",
            "1' OR '1'='1"
        ]
    }
