import redis.asyncio as redis
import structlog

logger = structlog.get_logger()


class RedisCacheAdapter:
    """Redis implementation of CacheProtocol."""

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._client: redis.Redis | None = None

    async def initialize(self) -> None:
        """Initialize Redis connection."""
        logger.info("redis_cache_initializing", url=self._redis_url)
        self._client = redis.from_url(self._redis_url)
        logger.info("redis_cache_initialized")

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            logger.info("redis_cache_closed")

    async def get(self, key: str) -> str | None:
        """Get cached value."""
        if not self._client:
            return None

        try:
            value = await self._client.get(f"llamaindex:cache:{key}")
            if value:
                logger.debug("cache_hit", key=key[:16])
                return value.decode() if isinstance(value, bytes) else value
            logger.debug("cache_miss", key=key[:16])
            return None
        except Exception as e:
            logger.warning("cache_get_error", key=key[:16], error=str(e))
            return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """Set cached value with TTL."""
        if not self._client:
            return

        try:
            await self._client.setex(
                f"llamaindex:cache:{key}",
                ttl_seconds,
                value,
            )
            logger.debug("cache_set", key=key[:16], ttl=ttl_seconds)
        except Exception as e:
            logger.warning("cache_set_error", key=key[:16], error=str(e))

    async def delete(self, key: str) -> None:
        """Delete cached value."""
        if not self._client:
            return

        try:
            await self._client.delete(f"llamaindex:cache:{key}")
            logger.debug("cache_delete", key=key[:16])
        except Exception as e:
            logger.warning("cache_delete_error", key=key[:16], error=str(e))

    async def health_check(self) -> bool:
        """Check if Redis is healthy."""
        if not self._client:
            return False

        try:
            await self._client.ping()
            return True
        except Exception:
            return False


class InMemoryCacheAdapter:
    """In-memory cache for testing or single-instance deployments."""

    def __init__(self):
        self._cache: dict[str, tuple[str, float]] = {}

    async def get(self, key: str) -> str | None:
        """Get cached value."""
        import time

        entry = self._cache.get(key)
        if entry:
            value, expires_at = entry
            if time.time() < expires_at:
                return value
            del self._cache[key]
        return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """Set cached value with TTL."""
        import time

        expires_at = time.time() + ttl_seconds
        self._cache[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        """Delete cached value."""
        self._cache.pop(key, None)

    async def health_check(self) -> bool:
        """In-memory cache is always healthy."""
        return True
