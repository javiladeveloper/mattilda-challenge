"""Cache decorator for API endpoints."""

import functools
import hashlib
import json
from typing import Callable, Any

from src.infrastructure.cache import get_cache
from src.config import settings


def cache_response(prefix: str, ttl: int = None):
    """
    Decorator to cache endpoint responses.

    Args:
        prefix: Cache key prefix (e.g., "school", "student")
        ttl: Time to live in seconds (default from settings)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Build cache key from function args
            cache = await get_cache()

            # Create unique key based on function name and arguments
            key_data = {
                "func": func.__name__,
                "args": str(args),
                "kwargs": {k: str(v) for k, v in kwargs.items() if k != "service"},
            }
            key_hash = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
            cache_key = f"{prefix}:{key_hash}"

            # Try to get from cache
            cached = await cache.get(cache_key)
            if cached is not None:
                return cached

            # Execute function
            result = await func(*args, **kwargs)

            # Cache the result
            cache_ttl = ttl or settings.cache_ttl

            # Convert Pydantic models to dict for caching
            if hasattr(result, "model_dump"):
                cache_data = result.model_dump(mode="json")
            elif hasattr(result, "dict"):
                cache_data = result.dict()
            else:
                cache_data = result

            await cache.set(cache_key, cache_data, cache_ttl)

            return result

        return wrapper

    return decorator


async def invalidate_cache(prefix: str, entity_id: str = None):
    """
    Invalidate cache entries for a given prefix.

    Args:
        prefix: Cache key prefix
        entity_id: Optional specific entity ID to invalidate
    """
    cache = await get_cache()
    if entity_id:
        pattern = f"{prefix}:*{entity_id}*"
    else:
        pattern = f"{prefix}:*"
    await cache.delete_pattern(pattern)
