"""
Cache Management Service
"""

import logging
from typing import Dict, Any, Optional
import redis
import json
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url
        self.redis_client = None

        if redis_url:
            try:
                self.redis_client = redis.Redis.from_url(redis_url)
                # Test connection
                self.redis_client.ping()
                logger.info("[CACHE] Redis connection established")
            except Exception as e:
                logger.error(f"[CACHE] Redis connection failed: {str(e)}")
                self.redis_client = None

    def clear_search_cache(self) -> bool:
        """
        Clear all search cache entries
        """
        if not self.redis_client:
            logger.warning("[CACHE] No Redis client available")
            return False

        try:
            # Find all cache keys (pattern: cache:search:*)
            keys = self.redis_client.keys("cache:search:*")
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"[CACHE] Deleted {deleted} cache entries")
                return deleted > 0
            else:
                logger.info("[CACHE] No cache entries found to delete")
                return False
        except Exception as e:
            logger.error(f"[CACHE] Error clearing cache: {str(e)}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        """
        if not self.redis_client:
            return {
                "available": False,
                "cached_items": 0,
                "memory_usage": "N/A"
            }

        try:
            keys = self.redis_client.keys("cache:search:*")
            stats = {
                "available": True,
                "cached_items": len(keys),
                "memory_usage": self.redis_client.info("memory")["used_memory_human"]
            }
            return stats
        except Exception as e:
            logger.error(f"[CACHE] Error getting cache stats: {str(e)}")
            return {
                "available": False,
                "error": str(e)
            }

# Global cache service instance
cache_service = CacheService()

def clear_search_cache() -> bool:
    """Clear search cache"""
    return cache_service.clear_search_cache()

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    return cache_service.get_cache_stats()