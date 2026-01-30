"""Rate limiting middleware using Redis."""

from typing import Callable
import time
from fastapi import Request, status
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import structlog

logger = structlog.get_logger()


class RateLimiter:
    """Redis-based rate limiter."""

    def __init__(self, app: Callable, redis_url: str, rate_limit: int) -> None:
        self.app = app
        self.redis_url = redis_url
        self.rate_limit = rate_limit
        self.redis_client: redis.Redis | None = None

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        """Process request with rate limiting."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        if request.url.path in ["/health", "/metrics"]:
            await self.app(scope, receive, send)
            return

        if not self.redis_client:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)

        client_id = request.client.host if request.client else "unknown"
        key = f"rate_limit:slack:{client_id}"
        current_time = int(time.time())

        async with self.redis_client.pipeline() as pipe:
            pipe.zadd(key, {str(current_time): current_time})
            pipe.zremrangebyscore(key, 0, current_time - 1)
            pipe.zcard(key)
            pipe.expire(key, 2)
            results = await pipe.execute()

        request_count = results[2]

        if request_count > self.rate_limit:
            logger.warning(
                "rate_limit_exceeded",
                client_id=client_id,
                request_count=request_count,
                limit=self.rate_limit,
            )
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": "1"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
