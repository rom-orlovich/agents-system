"""Redis queue operations."""

import json
from datetime import datetime
from typing import Optional, Dict, Any
import redis.asyncio as redis
from models import Task, TaskStatus
from config import settings


class RedisQueue:
    """Redis-based queue for task processing."""

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis connection."""
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        """Establish Redis connection."""
        if not self.redis:
            self.redis = await redis.from_url(
                self.redis_url,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True
            )

    async def disconnect(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()

    async def push(self, queue_name: str, data: Dict[str, Any]) -> str:
        """Push a task to the queue.

        Args:
            queue_name: Name of the queue
            data: Task data dictionary

        Returns:
            Task ID
        """
        await self.connect()

        # Add metadata
        data["queued_at"] = datetime.utcnow().isoformat()

        if "task_id" not in data:
            data["task_id"] = f"task-{datetime.now().timestamp()}"

        # Push to queue
        await self.redis.lpush(queue_name, json.dumps(data))

        # Store task metadata
        await self.redis.hset(
            f"tasks:{data['task_id']}",
            mapping={
                "data": json.dumps(data),
                "status": "queued",
                "queue": queue_name
            }
        )

        return data["task_id"]

    async def pop(self, queue_name: str, timeout: int = 0) -> Optional[Dict[str, Any]]:
        """Pop a task from the queue (blocking).

        Args:
            queue_name: Name of the queue
            timeout: Blocking timeout in seconds (0 = indefinite)

        Returns:
            Task data or None
        """
        await self.connect()

        result = await self.redis.brpop(queue_name, timeout=timeout)

        if result:
            _, data = result
            return json.loads(data)

        return None

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task data by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task data or None
        """
        await self.connect()

        data = await self.redis.hget(f"tasks:{task_id}", "data")

        if data:
            return json.loads(data)

        return None

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        **extra
    ) -> None:
        """Update task status and metadata.

        Args:
            task_id: Task identifier
            status: New status
            **extra: Additional fields to update
        """
        await self.connect()

        updates = {
            "status": status.value if isinstance(status, TaskStatus) else status,
            "updated_at": datetime.utcnow().isoformat()
        }
        updates.update(extra)

        # Convert complex objects to JSON
        for key, value in updates.items():
            if isinstance(value, (dict, list)):
                updates[key] = json.dumps(value)
            elif not isinstance(value, str):
                updates[key] = str(value)

        await self.redis.hset(f"tasks:{task_id}", mapping=updates)

    async def get_queue_length(self, queue_name: str) -> int:
        """Get current queue length.

        Args:
            queue_name: Name of the queue

        Returns:
            Number of items in queue
        """
        await self.connect()
        return await self.redis.llen(queue_name)

    async def get_all_tasks(self, status: Optional[TaskStatus] = None) -> list[Dict[str, Any]]:
        """Get all tasks, optionally filtered by status.

        Args:
            status: Filter by status (optional)

        Returns:
            List of task data
        """
        await self.connect()

        # Get all task keys
        task_keys = []
        async for key in self.redis.scan_iter("tasks:*"):
            task_keys.append(key)

        tasks = []
        for key in task_keys:
            task_data = await self.redis.hgetall(key)
            if task_data:
                # Parse JSON data
                if "data" in task_data:
                    task_data["data"] = json.loads(task_data["data"])

                # Filter by status if specified
                if status is None or task_data.get("status") == (
                    status.value if isinstance(status, TaskStatus) else status
                ):
                    tasks.append(task_data)

        return tasks

    async def get_tasks_by_filter(
        self,
        agent: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        source: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50
    ) -> list[Dict[str, Any]]:
        """Get tasks with advanced filtering.

        Args:
            agent: Filter by agent name
            status: Filter by task status
            source: Filter by task source
            start_date: Filter tasks created after this date
            end_date: Filter tasks created before this date
            limit: Maximum number of tasks to return

        Returns:
            List of task data matching filters
        """
        await self.connect()

        # Get all task keys
        task_keys = []
        async for key in self.redis.scan_iter("tasks:*"):
            task_keys.append(key)

        tasks = []
        for key in task_keys:
            task_data = await self.redis.hgetall(key)
            if not task_data:
                continue

            # Parse JSON data
            if "data" in task_data:
                parsed_data = json.loads(task_data["data"])
                task_data.update(parsed_data)

            # Apply filters
            # Filter by status
            if status is not None:
                task_status = task_data.get("status")
                expected_status = status.value if isinstance(status, TaskStatus) else status
                if task_status != expected_status:
                    continue

            # Filter by agent
            if agent is not None:
                task_agent = task_data.get("agent_name") or task_data.get("agent")
                if task_agent != agent:
                    continue

            # Filter by source
            if source is not None:
                task_source = task_data.get("source")
                if task_source != source:
                    continue

            # Filter by start_date
            if start_date is not None:
                created_at_str = task_data.get("created_at") or task_data.get("queued_at")
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        if created_at < start_date:
                            continue
                    except (ValueError, AttributeError):
                        continue

            # Filter by end_date
            if end_date is not None:
                created_at_str = task_data.get("created_at") or task_data.get("queued_at")
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        if created_at > end_date:
                            continue
                    except (ValueError, AttributeError):
                        continue

            tasks.append(task_data)

            # Respect limit
            if len(tasks) >= limit:
                break

        return tasks

    async def delete_task(self, task_id: str) -> None:
        """Delete task data.

        Args:
            task_id: Task identifier
        """
        await self.connect()
        await self.redis.delete(f"tasks:{task_id}")
