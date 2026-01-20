"""Redis queue operations.

Provides Pydantic-aware queue operations for type-safe task processing.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, Union
import redis.asyncio as redis

from pydantic import BaseModel

from types.enums import TaskStatus, TaskSource
from models.tasks import (
    AnyTask,
    JiraTask,
    SentryTask,
    GitHubTask,
    SlackTask,
)
from config.settings import settings


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



    # =========================================================================
    # PYDANTIC-AWARE METHODS (Type-safe task operations)
    # =========================================================================

    async def push_task(self, queue_name: str, task: BaseModel) -> str:
        """Push a Pydantic task to the queue.

        This is the preferred method for pushing tasks. Uses Pydantic's
        serialization for type safety.

        Args:
            queue_name: Name of the queue
            task: Pydantic model instance (JiraTask, SentryTask, etc.)

        Returns:
            Task ID
        """
        await self.connect()

        # Serialize using Pydantic v2
        data = task.model_dump_json()

        # Push to queue
        await self.redis.lpush(queue_name, data)

        # Store task metadata
        task_id = getattr(task, "task_id", f"task-{datetime.now().timestamp()}")
        status = getattr(task, "status", TaskStatus.QUEUED)

        await self.redis.hset(
            f"tasks:{task_id}",
            mapping={
                "data": data,
                "status": status.value if hasattr(status, "value") else str(status),
                "queue": queue_name
            }
        )
        return task_id

    async def pop_task(self, queue_name: str, timeout: int = 0) -> Optional[AnyTask]:
        """Pop a validated Pydantic task from the queue.

        This is the preferred method for popping tasks. Automatically
        validates and returns the correct task type based on source.

        Args:
            queue_name: Name of the queue
            timeout: Blocking timeout in seconds (0 = indefinite)

        Returns:
            Validated Pydantic task (JiraTask, SentryTask, etc.) or None
        """
        await self.connect()
        result = await self.redis.brpop(queue_name, timeout=timeout)

        if result:
            _, data = result
            return self._parse_task(data)
        return None

    def _parse_task(self, json_str: str) -> AnyTask:
        """Parse JSON string to appropriate task type.

        Uses discriminated union pattern based on the 'source' field.

        Args:
            json_str: JSON string from Redis

        Returns:
            Validated task of correct type

        Raises:
            ValueError: If source is unknown or validation fails
        """
        raw = json.loads(json_str)
        source = raw.get("source", "")

        # Handle both string and enum values
        if isinstance(source, str):
            source_value = source
        else:
            source_value = source.value if hasattr(source, "value") else str(source)

        if source_value == TaskSource.JIRA.value:
            return JiraTask.model_validate(raw)
        elif source_value == TaskSource.SENTRY.value:
            return SentryTask.model_validate(raw)
        elif source_value == TaskSource.GITHUB.value:
            return GitHubTask.model_validate(raw)
        elif source_value == TaskSource.SLACK.value:
            return SlackTask.model_validate(raw)
        else:
            raise ValueError(f"Unknown task source: {source_value}")

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

    async def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get full task metadata from Redis.

        Args:
            task_id: Task identifier

        Returns:
            Dictionary containing all task fields (status, queue, etc.)
        """
        await self.connect()
        return await self.redis.hgetall(f"tasks:{task_id}")

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
                    # Extract task_id from key (tasks:task-id)
                    current_task_id = key.split(":", 1)[1] if ":" in key else key
                    # Only calculate if not already present in data
                    if "task_id" not in task_data:
                        task_data["task_id"] = current_task_id
                    
                    # Also ensure it matches if present but maybe inside 'data' blob
                    if "data" in task_data and isinstance(task_data["data"], dict):
                        if "task_id" not in task_data["data"]:
                            task_data["data"]["task_id"] = current_task_id
                            
                    tasks.append(task_data)

        return tasks

    async def delete_task(self, task_id: str) -> None:
        """Delete task data.

        Args:
            task_id: Task identifier
        """
        await self.connect()
        await self.redis.delete(f"tasks:{task_id}")

    # =========================================================================
    # PR-TO-TASK MAPPING (For GitHub approval flow)
    # =========================================================================

    async def register_pr_task(
        self,
        pr_url: str,
        task_id: str,
        repository: str,
        pr_number: int
    ) -> None:
        """Register a PR URL to task mapping.
        
        This enables looking up tasks by PR URL for GitHub approvals.

        Args:
            pr_url: Full PR URL (e.g., https://github.com/owner/repo/pull/123)
            task_id: Task identifier
            repository: Repository full name (owner/repo)
            pr_number: PR number
        """
        await self.connect()
        
        # Store mapping: pr:<pr_url> -> task_id
        await self.redis.hset(
            f"pr:{pr_url}",
            mapping={
                "task_id": task_id,
                "repository": repository,
                "pr_number": str(pr_number),
                "registered_at": datetime.utcnow().isoformat()
            }
        )
        
        # Also create reverse index: task -> pr_url
        await self.redis.hset(f"tasks:{task_id}", "pr_url", pr_url)

    async def get_task_by_pr_url(self, pr_url: str) -> Optional[Dict[str, Any]]:
        """Get task by PR URL.

        Args:
            pr_url: Full PR URL

        Returns:
            Task data dict or None if not found
        """
        await self.connect()
        
        # Look up task ID from PR URL
        pr_data = await self.redis.hgetall(f"pr:{pr_url}")
        
        if not pr_data or "task_id" not in pr_data:
            return None
        
        task_id = pr_data["task_id"]
        return await self.get_task(task_id)


    async def get_task_id_by_pr(
        self,
        pr_number: int,
        repository: str
    ) -> Optional[str]:
        """Get task ID by PR number and repository.
        
        Searches for task associated with a specific PR.

        Args:
            pr_number: PR number
            repository: Repository full name (owner/repo)

        Returns:
            Task ID or None if not found
        """
        await self.connect()
        
        # Construct expected PR URL pattern
        pr_url_pattern = f"https://github.com/{repository}/pull/{pr_number}"
        
        # Try direct lookup first
        pr_data = await self.redis.hgetall(f"pr:{pr_url_pattern}")
        if pr_data and "task_id" in pr_data:
            return pr_data["task_id"]
        
        # Fall back to scanning all PRs (expensive but works)
        async for key in self.redis.scan_iter("pr:*"):
            data = await self.redis.hgetall(key)
            if (
                data.get("repository") == repository
                and data.get("pr_number") == str(pr_number)
            ):
                return data.get("task_id")
        
        return None

    # =========================================================================
    # SENTRY REPO MAPPING (For Jira Enrichment)
    # =========================================================================

    async def store_sentry_repo_mapping(self, sentry_issue_id: str, repository: str) -> None:
        """Store mapping between Sentry Issue ID and Repository.
        
        This allows us to look up the repository when we receive a Jira webhook
        that lacks this information (but has the Sentry Issue ID).
        
        Args:
            sentry_issue_id: Sentry Issue ID (e.g., "JAVASCRIPT-123")
            repository: Repository name (e.g., "owner/repo")
        """
        if not sentry_issue_id or not repository:
            return
            
        await self.connect()
        # Set with 24h expiry
        await self.redis.set(f"sentry_repo:{sentry_issue_id}", repository, ex=86400)

    async def get_repository_by_sentry_issue(self, sentry_issue_id: str) -> Optional[str]:
        """Get repository name for a Sentry Issue.
        
        Args:
            sentry_issue_id: Sentry Issue ID
            
        Returns:
            Repository name or None
        """
        if not sentry_issue_id:
            return None
            
        await self.connect()
        return await self.redis.get(f"sentry_repo:{sentry_issue_id}")
