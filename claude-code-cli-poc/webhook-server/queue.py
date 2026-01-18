"""
Redis Queue Integration
=======================
Simple Redis-based task queue for agent communication.
"""

import json
from typing import Any

import redis
import structlog

from shared.config import get_settings

logger = structlog.get_logger(__name__)

# Queue names
PLANNING_QUEUE = "planning:tasks"
EXECUTOR_QUEUE = "executor:tasks"


class TaskQueue:
    """Redis-based task queue."""

    def __init__(self):
        settings = get_settings()
        self.client = redis.from_url(settings.redis.url)

    def enqueue_planning_task(self, task_data: dict) -> str:
        """Add a task to the planning agent queue."""
        task_id = task_data.get("ticket_id", "unknown")
        self.client.rpush(PLANNING_QUEUE, json.dumps(task_data))
        logger.info("Enqueued planning task", task_id=task_id)
        return task_id

    def enqueue_executor_task(self, task_data: dict) -> str:
        """Add a task to the executor agent queue."""
        task_id = task_data.get("pr_number", "unknown")
        self.client.rpush(EXECUTOR_QUEUE, json.dumps(task_data))
        logger.info("Enqueued executor task", task_id=task_id)
        return task_id

    def dequeue_planning_task(self, timeout: int = 5) -> dict | None:
        """Get next task from planning queue (blocking)."""
        result = self.client.blpop(PLANNING_QUEUE, timeout=timeout)
        if result:
            return json.loads(result[1])
        return None

    def dequeue_executor_task(self, timeout: int = 5) -> dict | None:
        """Get next task from executor queue (blocking)."""
        result = self.client.blpop(EXECUTOR_QUEUE, timeout=timeout)
        if result:
            return json.loads(result[1])
        return None

    def get_queue_length(self, queue_name: str) -> int:
        """Get the number of items in a queue."""
        return self.client.llen(queue_name)

    def store_result(self, task_id: str, result: Any, expire_seconds: int = 86400):
        """Store task result with expiration."""
        key = f"result:{task_id}"
        self.client.setex(key, expire_seconds, json.dumps(result))

    def get_result(self, task_id: str) -> dict | None:
        """Get stored task result."""
        key = f"result:{task_id}"
        result = self.client.get(key)
        if result:
            return json.loads(result)
        return None


# Singleton instance
_queue: TaskQueue | None = None


def get_queue() -> TaskQueue:
    """Get singleton TaskQueue instance."""
    global _queue
    if _queue is None:
        _queue = TaskQueue()
    return _queue
