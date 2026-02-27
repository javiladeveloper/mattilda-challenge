"""
Rate limiter for AI endpoints using Redis.

Protects against abuse by limiting requests per IP/user.
"""

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, Request, status
import redis.asyncio as redis

from src.config import settings


class AIRateLimiter:
    """
    Redis-based rate limiter for AI endpoints.

    Implements a sliding window rate limit to prevent abuse.
    """

    def __init__(
        self,
        requests_per_minute: int = 10,
        requests_per_hour: int = 100,
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    def _get_client_id(self, request: Request) -> str:
        """Get unique identifier for the client."""
        # Use X-Forwarded-For if behind proxy, otherwise use client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        return client_ip

    async def check_rate_limit(self, request: Request) -> dict:
        """
        Check if request is within rate limits.

        Raises HTTPException 429 if rate limit exceeded.
        Returns rate limit info dict if allowed.
        """
        client_id = self._get_client_id(request)
        now = datetime.utcnow()

        try:
            r = await self._get_redis()

            # Keys for minute and hour windows
            minute_key = f"ai_rate:{client_id}:minute:{now.strftime('%Y%m%d%H%M')}"
            hour_key = f"ai_rate:{client_id}:hour:{now.strftime('%Y%m%d%H')}"

            # Get current counts
            minute_count = await r.get(minute_key) or 0
            hour_count = await r.get(hour_key) or 0

            minute_count = int(minute_count)
            hour_count = int(hour_count)

            # Check limits
            if minute_count >= self.requests_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "message": f"Máximo {self.requests_per_minute} solicitudes por minuto para el agente AI",
                        "retry_after_seconds": 60 - now.second,
                        "limit_type": "per_minute",
                    },
                )

            if hour_count >= self.requests_per_hour:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "message": f"Máximo {self.requests_per_hour} solicitudes por hora para el agente AI",
                        "retry_after_seconds": 3600 - (now.minute * 60 + now.second),
                        "limit_type": "per_hour",
                    },
                )

            # Increment counters
            pipe = r.pipeline()
            pipe.incr(minute_key)
            pipe.expire(minute_key, 120)  # 2 minutes TTL
            pipe.incr(hour_key)
            pipe.expire(hour_key, 7200)  # 2 hours TTL
            await pipe.execute()

            return {
                "requests_remaining_minute": self.requests_per_minute - minute_count - 1,
                "requests_remaining_hour": self.requests_per_hour - hour_count - 1,
                "reset_minute": 60 - now.second,
                "reset_hour": 3600 - (now.minute * 60 + now.second),
            }

        except redis.RedisError:
            # If Redis is unavailable, allow the request but log warning
            return {
                "warning": "Rate limiter unavailable",
                "requests_remaining_minute": -1,
                "requests_remaining_hour": -1,
            }

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


# Global rate limiter instance
ai_rate_limiter = AIRateLimiter(
    requests_per_minute=10,  # 10 requests per minute
    requests_per_hour=100,   # 100 requests per hour
)
