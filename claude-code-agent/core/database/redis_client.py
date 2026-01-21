"""Redis client for task queue and caching."""

import json
from typing import Optional, List
import redis.asyncio as redis
import structlog

from core.config import settings

logger = structlog.get_logger()


class RedisClient:
    """Async Redis client wrapper."""

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Connect to Redis."""
        self._client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info("Connected to Redis", url=settings.redis_url)

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            logger.info("Disconnected from Redis")

    async def push_task(self, task_id: str) -> None:
        """Add task to queue."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.rpush("task_queue", task_id)
        logger.debug("Task pushed to queue", task_id=task_id)

    async def pop_task(self, timeout: int = 30) -> Optional[str]:
        """Pop task from queue (blocking)."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        result = await self._client.blpop("task_queue", timeout=timeout)
        if result:
            _, task_id = result
            logger.debug("Task popped from queue", task_id=task_id)
            return task_id
        return None

    async def set_task_status(self, task_id: str, status: str) -> None:
        """Set task status."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.set(f"task:{task_id}:status", status, ex=3600)

    async def get_task_status(self, task_id: str) -> Optional[str]:
        """Get task status."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.get(f"task:{task_id}:status")

    async def set_task_pid(self, task_id: str, pid: int) -> None:
        """Set task process ID."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.set(f"task:{task_id}:pid", str(pid), ex=3600)

    async def get_task_pid(self, task_id: str) -> Optional[int]:
        """Get task process ID."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        pid_str = await self._client.get(f"task:{task_id}:pid")
        return int(pid_str) if pid_str else None

    async def append_output(self, task_id: str, chunk: str) -> None:
        """Append output chunk to task."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.append(f"task:{task_id}:output", chunk)
        await self._client.expire(f"task:{task_id}:output", 3600)

    async def get_output(self, task_id: str) -> Optional[str]:
        """Get accumulated output."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.get(f"task:{task_id}:output")

    async def add_session_task(self, session_id: str, task_id: str) -> None:
        """Add task to session."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.sadd(f"session:{session_id}:tasks", task_id)
        await self._client.expire(f"session:{session_id}:tasks", 86400)

    async def get_session_tasks(self, session_id: str) -> List[str]:
        """Get all tasks for session."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return list(await self._client.smembers(f"session:{session_id}:tasks"))

    async def set_json(self, key: str, data: dict, ex: Optional[int] = None) -> None:
        """Set JSON data."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.set(key, json.dumps(data), ex=ex)

    async def get_json(self, key: str) -> Optional[dict]:
        """Get JSON data."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        data = await self._client.get(key)
        return json.loads(data) if data else None

    async def delete(self, key: str) -> None:
        """Delete key."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.delete(key)

    async def queue_length(self) -> int:
        """Get task queue length."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.llen("task_queue")


# Global Redis client instance
redis_client = RedisClient()
