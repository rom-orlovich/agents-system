import redis.asyncio as redis
import structlog
from ports.queue import QueuePort, TaskQueueMessage

logger = structlog.get_logger()


class RedisQueueAdapter:
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        queue_name: str = "agent_tasks",
    ):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        if not self._client:
            self._client = await redis.from_url(self.redis_url)
        return self._client

    async def enqueue(self, message: TaskQueueMessage) -> None:
        client = await self._get_client()
        await client.zadd(
            self.queue_name,
            {message.model_dump_json(): message.priority},
        )
        logger.info("message_enqueued", task_id=message.task_id)

    async def dequeue(self, timeout: float) -> TaskQueueMessage | None:
        client = await self._get_client()
        result = await client.bzpopmax(self.queue_name, timeout=timeout)

        if not result:
            return None

        queue_name, message_json, priority = result
        return TaskQueueMessage.model_validate_json(message_json)

    async def get_queue_length(self) -> int:
        client = await self._get_client()
        return await client.zcard(self.queue_name)

    async def close(self) -> None:
        if self._client:
            await self._client.close()
