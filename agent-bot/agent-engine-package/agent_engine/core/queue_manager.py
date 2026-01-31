from enum import Enum
from typing import Any, TYPE_CHECKING
import redis.asyncio as aioredis

if TYPE_CHECKING:
    from redis.asyncio import Redis


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class QueueManager:
    TASK_QUEUE_KEY = "agent:tasks:queue"
    TASK_STATUS_PREFIX = "agent:task:status:"
    TASK_OUTPUT_PREFIX = "agent:task:output:"
    TASK_DATA_PREFIX = "agent:task:data:"

    def __init__(
        self,
        redis_client: Any = None,
        redis_url: str | None = None,
    ) -> None:
        if redis_client:
            self._client = redis_client
        elif redis_url:
            self._client = aioredis.from_url(redis_url)
        else:
            from agent_engine.core.config import settings
            self._client = aioredis.from_url(settings.redis_url)

    async def push_task(self, task_id: str) -> None:
        await self._client.lpush(self.TASK_QUEUE_KEY, task_id)

    async def pop_task(self, timeout: int = 5) -> str | None:
        result = await self._client.brpop(self.TASK_QUEUE_KEY, timeout=timeout)
        if result:
            return result[1].decode()
        return None

    async def set_task_status(self, task_id: str, status: TaskStatus) -> None:
        key = f"{self.TASK_STATUS_PREFIX}{task_id}"
        await self._client.set(key, status.value)

    async def get_task_status(self, task_id: str) -> TaskStatus | None:
        key = f"{self.TASK_STATUS_PREFIX}{task_id}"
        value = await self._client.get(key)
        if value:
            return TaskStatus(value.decode())
        return None

    async def append_output(self, task_id: str, chunk: str) -> None:
        key = f"{self.TASK_OUTPUT_PREFIX}{task_id}"
        await self._client.append(key, chunk)

    async def get_output(self, task_id: str) -> str:
        key = f"{self.TASK_OUTPUT_PREFIX}{task_id}"
        value = await self._client.get(key)
        return value.decode() if value else ""

    async def set_task_data(self, task_id: str, data: str) -> None:
        key = f"{self.TASK_DATA_PREFIX}{task_id}"
        await self._client.set(key, data)

    async def get_task_data(self, task_id: str) -> str | None:
        key = f"{self.TASK_DATA_PREFIX}{task_id}"
        value = await self._client.get(key)
        return value.decode() if value else None

    async def delete_task_data(self, task_id: str) -> None:
        keys = [
            f"{self.TASK_STATUS_PREFIX}{task_id}",
            f"{self.TASK_OUTPUT_PREFIX}{task_id}",
            f"{self.TASK_DATA_PREFIX}{task_id}",
        ]
        await self._client.delete(*keys)

    async def get_queue_length(self) -> int:
        return await self._client.llen(self.TASK_QUEUE_KEY)

    async def close(self) -> None:
        await self._client.close()
