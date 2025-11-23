"""
Performance Metrics Tracker
Tracks indexing performance, cache hits, and API latency
"""
from typing import Dict, List
from datetime import datetime
from collections import deque
import time


class PerformanceMetrics:
    """Track performance metrics for monitoring"""
    
    def __init__(self):
        # Store recent metrics (last 100 operations)
        self.indexing_times = deque(maxlen=100)
        self.search_times = deque(maxlen=100)
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_searches = 0
        
        print("✅ PerformanceMetrics initialized!")
    
    def record_indexing(self, repo_id: str, duration: float, function_count: int):
        """Record indexing performance"""
        self.indexing_times.append({
            "repo_id": repo_id,
            "duration": duration,
            "function_count": function_count,
            "speed": function_count / duration if duration > 0 else 0,
            "timestamp": datetime.now().isoformat()
        })
    
    def record_search(self, duration: float, cached: bool):
        """Record search performance"""
        self.search_times.append({
            "duration": duration,
            "cached": cached,
            "timestamp": datetime.now().isoformat()
        })
        
        self.total_searches += 1
        if cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    def get_metrics(self) -> Dict:
        """Get current performance metrics"""
        # Calculate statistics
        indexing_speeds = [m["speed"] for m in self.indexing_times]
        search_durations = [m["duration"] for m in self.search_times]
        
        cache_hit_rate = (self.cache_hits / self.total_searches * 100) if self.total_searches > 0 else 0
        
        return {
            "indexing": {
                "total_operations": len(self.indexing_times),
                "avg_speed_functions_per_sec": sum(indexing_speeds) / len(indexing_speeds) if indexing_speeds else 0,
                "max_speed": max(indexing_speeds) if indexing_speeds else 0,
                "min_speed": min(indexing_speeds) if indexing_speeds else 0,
                "recent_operations": list(self.indexing_times)[-10:]
            },
            "search": {
                "total_searches": self.total_searches,
                "cache_hit_rate": f"{cache_hit_rate:.1f}%",
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "avg_duration_ms": sum(search_durations) / len(search_durations) * 1000 if search_durations else 0,
                "recent_searches": list(self.search_times)[-10:]
            },
            "summary": {
                "health": "healthy",
                "cache_working": cache_hit_rate > 0,
                "indexing_performance": "good" if (sum(indexing_speeds) / len(indexing_speeds) if indexing_speeds else 0) > 10 else "needs_improvement"
            }
        }
