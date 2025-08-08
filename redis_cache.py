#!/usr/bin/env python3
"""
Redis Caching Implementation for MCP Server
Provides multi-level caching for prompts, AI responses, and database queries
"""

import redis
import json
import pickle
import hashlib
import asyncio
from typing import Any, Optional, Dict, List
from functools import wraps
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self, redis_url: str = "redis://localhost:6379", default_ttl: int = 3600):
        """Initialize Redis cache with connection and default TTL"""
        self.redis_client = redis.from_url(redis_url, decode_responses=False)
        self.default_ttl = default_ttl

        # Test connection
        try:
            self.redis_client.ping()
            logger.info("✅ Redis cache connected successfully")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.redis_client = None

    def _serialize_key(self, key: str) -> str:
        """Create a serialized cache key with namespace"""
        return f"mcp:cache:{key}"

    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for Redis storage"""
        try:
            if isinstance(value, (dict, list)):
                return json.dumps(value).encode('utf-8')
            elif isinstance(value, str):
                return value.encode('utf-8')
            else:
                return pickle.dumps(value)
        except Exception as e:
            logger.error(f"Serialization error: {e}")
            return pickle.dumps(value)

    def _deserialize_value(self, value: bytes) -> Any:
        """Deserialize value from Redis storage"""
        try:
            # Try JSON first
            return json.loads(value.decode('utf-8'))
        except:
            try:
                # Fallback to pickle
                return pickle.loads(value)
            except:
                # Return as string
                return value.decode('utf-8')

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None

        try:
            cache_key = self._serialize_key(key)
            value = await asyncio.to_thread(self.redis_client.get, cache_key)

            if value is None:
                return None

            return self._deserialize_value(value)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL"""
        if not self.redis_client:
            return False

        try:
            cache_key = self._serialize_key(key)
            serialized_value = self._serialize_value(value)
            cache_ttl = ttl or self.default_ttl

            result = await asyncio.to_thread(
                self.redis_client.setex,
                cache_key,
                cache_ttl,
                serialized_value
            )
            return bool(result)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis_client:
            return False

        try:
            cache_key = self._serialize_key(key)
            result = await asyncio.to_thread(self.redis_client.delete, cache_key)
            return bool(result)
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis_client:
            return False

        try:
            cache_key = self._serialize_key(key)
            result = await asyncio.to_thread(self.redis_client.exists, cache_key)
            return bool(result)
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        if not self.redis_client:
            return 0

        try:
            cache_pattern = self._serialize_key(pattern)
            keys = await asyncio.to_thread(self.redis_client.keys, cache_pattern)
            if keys:
                result = await asyncio.to_thread(self.redis_client.delete, *keys)
                return result
            return 0
        except Exception as e:
            logger.error(f"Cache invalidate error for pattern {pattern}: {e}")
            return 0

# Global cache instance
cache = RedisCache()

def cache_result(ttl: int = 3600, key_prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_data = f"{key_prefix}{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()

            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            logger.debug(f"Cache miss for {func.__name__}, result cached")

            return result
        return wrapper
    return decorator

# Specialized cache functions for common use cases

class PromptCache:
    """Specialized caching for prompt operations"""

    @staticmethod
    async def get_popular_prompts(limit: int = 10) -> Optional[List[Dict]]:
        """Get cached popular prompts"""
        return await cache.get(f"popular_prompts:{limit}")

    @staticmethod
    async def set_popular_prompts(prompts: List[Dict], limit: int = 10, ttl: int = 1800):
        """Cache popular prompts for 30 minutes"""
        await cache.set(f"popular_prompts:{limit}", prompts, ttl)

    @staticmethod
    async def get_search_results(query: str, filters: Dict) -> Optional[List[Dict]]:
        """Get cached search results"""
        search_key = f"search:{hashlib.md5(f'{query}:{str(filters)}'.encode()).hexdigest()}"
        return await cache.get(search_key)

    @staticmethod
    async def set_search_results(query: str, filters: Dict, results: List[Dict], ttl: int = 600):
        """Cache search results for 10 minutes"""
        search_key = f"search:{hashlib.md5(f'{query}:{str(filters)}'.encode()).hexdigest()}"
        await cache.set(search_key, results, ttl)

class AICache:
    """Specialized caching for AI service responses"""

    @staticmethod
    async def get_ai_response(prompt: str, model: str = "default") -> Optional[str]:
        """Get cached AI response"""
        ai_key = f"ai_response:{model}:{hashlib.md5(prompt.encode()).hexdigest()}"
        return await cache.get(ai_key)

    @staticmethod
    async def set_ai_response(prompt: str, response: str, model: str = "default", ttl: int = 7200):
        """Cache AI response for 2 hours"""
        ai_key = f"ai_response:{model}:{hashlib.md5(prompt.encode()).hexdigest()}"
        await cache.set(ai_key, response, ttl)

    @staticmethod
    async def get_model_status(model: str) -> Optional[Dict]:
        """Get cached model status"""
        return await cache.get(f"model_status:{model}")

    @staticmethod
    async def set_model_status(model: str, status: Dict, ttl: int = 300):
        """Cache model status for 5 minutes"""
        await cache.set(f"model_status:{model}", status, ttl)

# Cache warming functions

async def warm_cache():
    """Warm up cache with frequently accessed data"""
    logger.info("🔥 Warming up cache...")

    try:
        # This would typically be called after database connection is established
        # Warm popular prompts, recent searches, etc.

        # Example: Cache popular domains
        popular_domains = ["Technology", "AI/ML", "Creative", "Business"]
        for domain in popular_domains:
            await cache.set(f"domain_info:{domain}", {"domain": domain, "cached_at": "startup"}, 3600)

        logger.info("✅ Cache warmed successfully")
    except Exception as e:
        logger.error(f"❌ Cache warming failed: {e}")

# Cache monitoring

class CacheMonitor:
    """Monitor cache performance and health"""

    @staticmethod
    async def get_cache_stats() -> Dict:
        """Get cache statistics"""
        if not cache.redis_client:
            return {"status": "disabled"}

        try:
            info = await asyncio.to_thread(cache.redis_client.info)

            return {
                "status": "healthy",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "total_connections": info.get("total_connections_received", 0),
                "total_commands": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": round(
                    info.get("keyspace_hits", 0) /
                    max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)) * 100,
                    2
                )
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"status": "error", "error": str(e)}

    @staticmethod
    async def clear_cache() -> bool:
        """Clear all cache entries"""
        try:
            result = await cache.invalidate_pattern("*")
            logger.info(f"Cleared {result} cache entries")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
