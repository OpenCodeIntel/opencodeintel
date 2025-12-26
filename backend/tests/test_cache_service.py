"""
Tests for CacheService - specifically the generic get/set methods.
"""
import pytest
from unittest.mock import MagicMock, patch
import json


class TestCacheServiceGenericMethods:
    """Test the generic get() and set() methods added for #134."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        return MagicMock()
    
    @pytest.fixture
    def cache_service(self, mock_redis):
        """Create CacheService with mocked Redis."""
        with patch('services.cache.redis.Redis', return_value=mock_redis):
            with patch('services.cache.redis.from_url', return_value=mock_redis):
                mock_redis.ping.return_value = True
                from services.cache import CacheService
                service = CacheService()
                service.redis = mock_redis
                return service
    
    def test_get_returns_cached_value(self, cache_service, mock_redis):
        """get() returns parsed JSON when key exists."""
        test_data = {"valid": True, "repo_name": "flask"}
        mock_redis.get.return_value = json.dumps(test_data).encode()
        
        result = cache_service.get("validate:https://github.com/pallets/flask")
        
        assert result == test_data
        mock_redis.get.assert_called_once()
    
    def test_get_returns_none_when_key_missing(self, cache_service, mock_redis):
        """get() returns None when key doesn't exist."""
        mock_redis.get.return_value = None
        
        result = cache_service.get("validate:nonexistent")
        
        assert result is None
    
    def test_get_returns_none_when_redis_unavailable(self, cache_service):
        """get() returns None when Redis is not available."""
        cache_service.redis = None
        
        result = cache_service.get("any_key")
        
        assert result is None
    
    def test_get_handles_redis_error(self, cache_service, mock_redis):
        """get() returns None and logs error on Redis exception."""
        mock_redis.get.side_effect = Exception("Redis connection error")
        
        result = cache_service.get("validate:test")
        
        assert result is None
    
    def test_set_stores_value_with_ttl(self, cache_service, mock_redis):
        """set() stores JSON value with TTL."""
        test_data = {"valid": True, "can_index": True}
        
        result = cache_service.set("validate:test", test_data, ttl=300)
        
        assert result is True
        mock_redis.setex.assert_called_once_with(
            "validate:test",
            300,
            json.dumps(test_data)
        )
    
    def test_set_uses_default_ttl(self, cache_service, mock_redis):
        """set() uses 300s (5 min) as default TTL."""
        test_data = {"valid": True}
        
        cache_service.set("validate:test", test_data)
        
        # Check that TTL is 300 (default)
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 300  # TTL is second positional arg
    
    def test_set_returns_false_when_redis_unavailable(self, cache_service):
        """set() returns False when Redis is not available."""
        cache_service.redis = None
        
        result = cache_service.set("any_key", {"data": "value"})
        
        assert result is False
    
    def test_set_handles_redis_error(self, cache_service, mock_redis):
        """set() returns False on Redis exception."""
        mock_redis.setex.side_effect = Exception("Redis write error")
        
        result = cache_service.set("validate:test", {"data": "value"})
        
        assert result is False
