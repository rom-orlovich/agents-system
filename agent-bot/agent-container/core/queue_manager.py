"""Redis queue manager."""

import json
from typing import Any
import redis.asyncio as redis
import structlog

logger = structlog.get_logger()


class QueueManager:
    """Manages task queues using Redis."""

    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self.client: redis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        self.client = redis.from_url(self.redis_url, decode_responses=True)
        logger.info("queue_manager_connected", redis_url=self.redis_url)

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.client:
            await self.client.aclose()
            logger.info("queue_manager_disconnected")

    async def pop_task(self, queue_name: str, timeout: int = 0) -> dict[str, Any] | None:
        """Pop task from queue (blocking)."""
        if not self.client:
            raise RuntimeError("Queue manager not connected")

        result = await self.client.blpop(queue_name, timeout=timeout)
        if not result:
            return None

        _, task_data = result
        task = json.loads(task_data)
        logger.info("task_popped", task_id=task.get("task_id"), queue=queue_name)
        return task

    async def push_task(self, queue_name: str, task: dict[str, Any]) -> None:
        """Push task to queue."""
        if not self.client:
            raise RuntimeError("Queue manager not connected")

        task_data = json.dumps(task)
        await self.client.rpush(queue_name, task_data)
        logger.info("task_pushed", task_id=task.get("task_id"), queue=queue_name)

    async def set_task_status(self, task_id: str, status: str, result: dict[str, Any] | None = None) -> None:
        """Set task status in Redis."""
        if not self.client:
            raise RuntimeError("Queue manager not connected")

        key = f"task:{task_id}:status"
        value = {"status": status, "result": result}
        await self.client.set(key, json.dumps(value), ex=86400)
        logger.info("task_status_updated", task_id=task_id, status=status)

    async def get_queue_size(self, queue_name: str) -> int:
        """Get current queue size."""
        if not self.client:
            raise RuntimeError("Queue manager not connected")

        return await self.client.llen(queue_name)
