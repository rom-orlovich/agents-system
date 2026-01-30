import asyncio
from datetime import datetime, timedelta

import structlog

logger = structlog.get_logger()


class CacheEntry:
    def __init__(self, value: str, expires_at: datetime | None):
        self.value = value
        self.expires_at = expires_at

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class InMemoryCacheAdapter:
    def __init__(self) -> None:
        self._storage: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> str | None:
        async with self._lock:
            entry = self._storage.get(key)
            if entry is None:
                return None
            if entry.is_expired():
                del self._storage[key]
                return None
            return entry.value

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        expires_at = None
        if ttl_seconds is not None:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

        async with self._lock:
            self._storage[key] = CacheEntry(value, expires_at)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._storage:
                del self._storage[key]
                return True
            return False

    async def exists(self, key: str) -> bool:
        value = await self.get(key)
        return value is not None

    async def clear(self) -> None:
        async with self._lock:
            self._storage.clear()
