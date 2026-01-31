from typing import Any
import json
import redis.asyncio as redis
import structlog

from config import get_settings

logger = structlog.get_logger(__name__)


class TaskManager:
    def __init__(self):
        self._settings = get_settings()
        self._redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self._settings.redis_url)
        return self._redis

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        client = await self._get_redis()
        data = await client.hget(f"task:{task_id}", "data")
        if data:
            return json.loads(data)
        return None

    async def list_tasks(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        client = await self._get_redis()
        tasks = []

        cursor = 0
        pattern = "task:*"
        count = 0
        skipped = 0

        while True:
            cursor, keys = await client.scan(cursor, match=pattern, count=100)
            for key in keys:
                if count >= limit:
                    break

                task_data = await client.hget(key, "data")
                if task_data:
                    task = json.loads(task_data)
                    if status and task.get("status") != status:
                        continue

                    if skipped < offset:
                        skipped += 1
                        continue

                    task["task_id"] = key.decode().split(":")[1]
                    tasks.append(task)
                    count += 1

            if cursor == 0 or count >= limit:
                break

        return tasks

    async def get_queue_length(self) -> int:
        client = await self._get_redis()
        return await client.llen("agent:tasks")

    async def get_task_stats(self) -> dict[str, int]:
        client = await self._get_redis()

        stats = {
            "queued": await client.llen("agent:tasks"),
            "completed": 0,
            "failed": 0,
            "in_progress": 0,
        }

        cursor = 0
        pattern = "task:*"

        while True:
            cursor, keys = await client.scan(cursor, match=pattern, count=100)
            for key in keys:
                task_data = await client.hget(key, "data")
                if task_data:
                    task = json.loads(task_data)
                    status = task.get("status", "unknown")
                    if status in stats:
                        stats[status] += 1

            if cursor == 0:
                break

        return stats

    async def cancel_task(self, task_id: str) -> bool:
        client = await self._get_redis()
        task_data = await client.hget(f"task:{task_id}", "data")

        if not task_data:
            return False

        task = json.loads(task_data)
        task["status"] = "cancelled"
        await client.hset(f"task:{task_id}", "data", json.dumps(task))

        return True
