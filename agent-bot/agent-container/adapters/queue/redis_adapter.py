import redis.asyncio as redis
import structlog
from ports import QueuePort, TaskQueueMessage

logger = structlog.get_logger()


class RedisQueueAdapter:
    def __init__(self, redis_url: str, queue_name: str = "tasks"):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        if not self._client:
            self._client = await redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
        return self._client

    async def enqueue(self, message: TaskQueueMessage) -> None:
        logger.info("enqueuing_task", task_id=message.task_id)

        client = await self._get_client()
        await client.zadd(
            self.queue_name,
            {message.model_dump_json(): message.priority},
        )

        logger.info("task_enqueued", task_id=message.task_id)

    async def dequeue(self, timeout: float) -> TaskQueueMessage | None:
        client = await self._get_client()

        result = await client.bzpopmin(self.queue_name, timeout)

        if not result:
            return None

        queue_name, message_json, score = result
        message = TaskQueueMessage.model_validate_json(message_json)

        logger.info("task_dequeued", task_id=message.task_id)

        return message

    async def acknowledge(self, message_id: str) -> None:
        logger.info("acknowledging_message", message_id=message_id)

    async def get_queue_length(self) -> int:
        client = await self._get_client()
        length = await client.zcard(self.queue_name)
        return length

    async def close(self) -> None:
        if self._client:
            await self._client.close()
