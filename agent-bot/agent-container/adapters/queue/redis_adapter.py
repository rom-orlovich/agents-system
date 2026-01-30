import asyncio
import json
from datetime import datetime, timezone

import redis.asyncio as redis
import structlog

from ports.queue import TaskQueueMessage, TaskPriority, QueuePort

logger = structlog.get_logger()

QUEUE_KEY = "agent:tasks"
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY_SECONDS = 2.0


class RedisConnectionError(Exception):
    pass


class RedisQueueAdapter:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._client: redis.Redis | None = None
        self._connected = False
        self._lock = asyncio.Lock()

    async def _ensure_connected(self) -> redis.Redis:
        if self._connected and self._client is not None:
            return self._client

        async with self._lock:
            if self._connected and self._client is not None:
                return self._client

            for attempt in range(MAX_RECONNECT_ATTEMPTS):
                try:
                    self._client = await redis.from_url(
                        self._redis_url,
                        encoding="utf-8",
                        decode_responses=True,
                        socket_timeout=5.0,
                        socket_connect_timeout=5.0,
                    )
                    await self._client.ping()
                    self._connected = True
                    logger.info(
                        "redis_connected",
                        url=self._redis_url,
                        attempt=attempt + 1,
                    )
                    return self._client
                except (redis.ConnectionError, redis.TimeoutError, Exception) as e:
                    logger.warning(
                        "redis_connection_failed",
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    if attempt < MAX_RECONNECT_ATTEMPTS - 1:
                        await asyncio.sleep(RECONNECT_DELAY_SECONDS)
                    else:
                        raise RedisConnectionError(
                            f"Failed to connect after {MAX_RECONNECT_ATTEMPTS} attempts"
                        ) from e

        raise RedisConnectionError("Unreachable code")

    async def enqueue(self, message: TaskQueueMessage) -> None:
        client = await self._ensure_connected()

        message_dict = message.model_dump(mode="json")
        message_json = json.dumps(message_dict)

        try:
            await client.zadd(
                QUEUE_KEY,
                {message_json: message.priority.value},
            )
            logger.info(
                "task_enqueued",
                task_id=message.task_id,
                priority=message.priority.name,
            )
        except (redis.ConnectionError, redis.TimeoutError) as e:
            self._connected = False
            logger.error("enqueue_failed", task_id=message.task_id, error=str(e))
            raise

    async def dequeue(
        self, timeout_seconds: float = 30.0
    ) -> TaskQueueMessage | None:
        client = await self._ensure_connected()

        try:
            result = await client.bzpopmin(QUEUE_KEY, timeout=timeout_seconds)

            if result is None:
                return None

            _, message_json, _ = result
            message_dict = json.loads(message_json)

            message_dict["created_at"] = datetime.fromisoformat(
                message_dict["created_at"]
            )
            message_dict["priority"] = TaskPriority(message_dict["priority"])

            message = TaskQueueMessage.model_validate(message_dict)

            logger.info(
                "task_dequeued",
                task_id=message.task_id,
                priority=message.priority.name,
            )
            return message

        except (redis.ConnectionError, redis.TimeoutError) as e:
            self._connected = False
            logger.error("dequeue_failed", error=str(e))
            raise

    async def ack(self, task_id: str) -> None:
        logger.info("task_acknowledged", task_id=task_id)

    async def nack(self, task_id: str) -> None:
        logger.info("task_not_acknowledged", task_id=task_id)

    async def get_queue_size(self) -> int:
        client = await self._ensure_connected()

        try:
            size = await client.zcard(QUEUE_KEY)
            return size if isinstance(size, int) else 0
        except (redis.ConnectionError, redis.TimeoutError) as e:
            self._connected = False
            logger.error("get_queue_size_failed", error=str(e))
            raise

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._connected = False
            logger.info("redis_connection_closed")
