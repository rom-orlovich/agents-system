import redis.asyncio as redis
from typing import Dict, Any
import json
import structlog
from core.models import TaskQueueMessage

logger = structlog.get_logger()


class TaskQueue:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client: redis.Redis | None = None
        self.queue_name = "tasks"

    async def connect(self) -> None:
        self.redis_client = await redis.from_url(
            self.redis_url, encoding="utf-8", decode_responses=True
        )
        logger.info("task_queue_connected", redis_url=self.redis_url)

    async def disconnect(self) -> None:
        if self.redis_client:
            await self.redis_client.close()
            logger.info("task_queue_disconnected")

    async def enqueue(
        self, task: TaskQueueMessage, priority: int = 0
    ) -> Dict[str, str | int]:
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")

        task_data = task.model_dump_json()
        score = priority

        await self.redis_client.zadd(self.queue_name, {task_data: score})

        logger.info(
            "task_enqueued",
            task_id=task.task_id,
            priority=priority,
            queue=self.queue_name,
        )

        return {"task_id": task.task_id, "queue": self.queue_name, "priority": priority}

    async def dequeue(self, worker_id: str) -> TaskQueueMessage | None:
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")

        result = await self.redis_client.zpopmin(self.queue_name, count=1)

        if not result:
            return None

        task_data, score = result[0]
        task = TaskQueueMessage.model_validate_json(task_data)

        logger.info(
            "task_dequeued",
            task_id=task.task_id,
            worker_id=worker_id,
            queue=self.queue_name,
        )

        return task

    async def get_queue_length(self) -> int:
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")

        length = await self.redis_client.zcard(self.queue_name)
        return length

    async def peek(self, count: int = 1) -> list[TaskQueueMessage]:
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")

        results = await self.redis_client.zrange(self.queue_name, 0, count - 1)

        tasks = []
        for task_data in results:
            task = TaskQueueMessage.model_validate_json(task_data)
            tasks.append(task)

        return tasks
