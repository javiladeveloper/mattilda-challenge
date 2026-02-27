import json
from typing import Any, Optional

import redis.asyncio as redis

from src.config import settings


class RedisCache:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_ttl = 300  # 5 minutes

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with TTL."""
        try:
            ttl = ttl or self.default_ttl
            await self.redis.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            await self.redis.delete(key)
            return True
        except Exception:
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception:
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return await self.redis.exists(key) > 0
        except Exception:
            return False


class MockRedisCache(RedisCache):
    """In-memory mock cache for when Redis is not available."""

    def __init__(self):
        self._store: dict[str, Any] = {}

    async def get(self, key: str) -> Optional[Any]:
        return self._store.get(key)

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        self._store[key] = value
        return True

    async def delete(self, key: str) -> bool:
        self._store.pop(key, None)
        return True

    async def delete_pattern(self, pattern: str) -> int:
        import fnmatch

        pattern = pattern.replace("*", ".*")
        keys_to_delete = [k for k in self._store if fnmatch.fnmatch(k, pattern)]
        for k in keys_to_delete:
            del self._store[k]
        return len(keys_to_delete)

    async def exists(self, key: str) -> bool:
        return key in self._store


_cache_instance: Optional[RedisCache] = None


async def get_cache() -> RedisCache:
    """Get cache instance (Redis or Mock)."""
    global _cache_instance
    if _cache_instance is None:
        try:
            redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await redis_client.ping()
            _cache_instance = RedisCache(redis_client)
        except Exception:
            # Fallback to mock cache if Redis not available
            _cache_instance = MockRedisCache()
    return _cache_instance
