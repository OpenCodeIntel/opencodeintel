"""
Professional Test Configuration
Proper dependency mocking for FastAPI testing
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import os

# Set test environment BEFORE imports
os.environ["DEBUG"] = "true"
os.environ["API_KEY"] = "test-secret-key"
os.environ["OPENAI_API_KEY"] = "sk-test-key"
os.environ["PINECONE_API_KEY"] = "pcsk-test"
os.environ["PINECONE_INDEX_NAME"] = "test-index"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_KEY"] = "test-key"

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
    """Mock Redis client globally"""
    with patch('redis.Redis') as mock:
        redis_instance = MagicMock()
        redis_instance.ping.return_value = True
        redis_instance.get.return_value = None
        redis_instance.set.return_value = True
        redis_instance.incr.return_value = 1
        redis_instance.expire.return_value = True
        mock.return_value = redis_instance
        yield mock


@pytest.fixture(scope="session", autouse=True)
def mock_supabase():
    """Mock Supabase client globally"""
    with patch('supabase.create_client') as mock:
        client = MagicMock()
        table = MagicMock()
        
        # Mock the fluent interface
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
    """TestClient with mocked dependencies"""
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)


@pytest.fixture
def valid_headers():
    """Valid authentication headers"""
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
