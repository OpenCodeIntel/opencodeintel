"""
Cache Service
Redis-based caching for search results and embeddings
"""
import redis
import json
import hashlib
from typing import Optional, List, Dict
import os
from dotenv import load_dotenv

from services.observability import logger, metrics

load_dotenv()

# Configuration
REDIS_URL = os.getenv("REDIS_URL")  # Railway/Cloud Redis URL
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))


class CacheService:
    """Redis cache for search results and embeddings"""
    
    def __init__(self):
        try:
            # Use REDIS_URL if available (Railway/Cloud), otherwise use host/port
            if REDIS_URL:
                self.redis = redis.from_url(
                    REDIS_URL,
                    decode_responses=False,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                logger.info("Redis connected via URL")
            else:
                self.redis = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=0,
                    decode_responses=False,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                logger.info("Redis connected", host=REDIS_HOST, port=REDIS_PORT)
            
            # Test connection
            self.redis.ping()
        except redis.ConnectionError as e:
            logger.warning("Redis not available - running without cache", error=str(e))
            self.redis = None
    
    def _make_key(self, prefix: str, *args) -> str:
        """Generate cache key"""
        parts = [str(arg) for arg in args]
        hash_input = ":".join(parts)
        hash_val = hashlib.md5(hash_input.encode()).hexdigest()[:12]
        return f"{prefix}:{hash_val}"
    
    def get_search_results(self, query: str, repo_id: str) -> Optional[List[Dict]]:
        """Get cached search results"""
        if not self.redis:
            return None
        
        try:
            key = self._make_key("search", repo_id, query)
            cached = self.redis.get(key)
            if cached:
                metrics.increment("cache_hits")
                return json.loads(cached)
            metrics.increment("cache_misses")
        except Exception as e:
            logger.error("Cache read error", operation="get_search_results", error=str(e))
            metrics.increment("cache_errors")
        
        return None
    
    def set_search_results(
        self, 
        query: str, 
        repo_id: str, 
        results: List[Dict],
        ttl: int = 3600
    ):
        """Cache search results"""
        if not self.redis:
            return
        
        try:
            key = self._make_key("search", repo_id, query)
            self.redis.setex(key, ttl, json.dumps(results))
        except Exception as e:
            logger.error("Cache write error", operation="set_search_results", error=str(e))
            metrics.increment("cache_errors")
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding"""
        if not self.redis:
            return None
        
        try:
            key = self._make_key("emb", text[:100])
            cached = self.redis.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error("Cache read error", operation="get_embedding", error=str(e))
            metrics.increment("cache_errors")
        
        return None
    
    def set_embedding(self, text: str, embedding: List[float], ttl: int = 86400):
        """Cache embedding"""
        if not self.redis:
            return
        
        try:
            key = self._make_key("emb", text[:100])
            self.redis.setex(key, ttl, json.dumps(embedding))
        except Exception as e:
            logger.error("Cache write error", operation="set_embedding", error=str(e))
            metrics.increment("cache_errors")
    
    def invalidate_repo(self, repo_id: str):
        """Invalidate all cache for a repository"""
        if not self.redis:
            return
        
        try:
            pattern = f"search:*{repo_id}*"
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
                logger.info("Cache invalidated", repo_id=repo_id, keys_removed=len(keys))
        except Exception as e:
            logger.error("Cache invalidation error", repo_id=repo_id, error=str(e))
