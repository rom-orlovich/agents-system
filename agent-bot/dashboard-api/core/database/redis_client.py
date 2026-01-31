"""Redis client for task queue and caching."""

import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import redis.asyncio as redis
import structlog

from core.config import settings

logger = structlog.get_logger()


class RedisKeys:
    """Redis key patterns for various data types."""

    # Task management
    TASK_QUEUE = "task_queue"
    TASK_STATUS = "task:{id}:status"
    TASK_PID = "task:{id}:pid"
    TASK_OUTPUT = "task:{id}:output"

    # Session management
    SESSION_TASKS = "session:{id}:tasks"

    # Subagent management
    ACTIVE_SUBAGENTS = "subagents:active"  # Set of active subagent IDs
    SUBAGENT_STATUS = "subagent:{id}:status"  # Hash with status details
    SUBAGENT_CONTEXT = "subagent:{id}:context"  # Context window state
    SUBAGENT_OUTPUT = "subagent:{id}:output"  # Streaming output

    # Parallel execution tracking
    PARALLEL_GROUP = "parallel:{group_id}:agents"  # Set of agents in group
    PARALLEL_RESULTS = "parallel:{group_id}:results"  # Hash of results
    PARALLEL_STATUS = "parallel:{group_id}:status"  # Group status

    # Machine management
    MACHINE_STATUS = "machine:{id}:status"  # Hash: status, last_heartbeat
    MACHINE_METRICS = "machine:{id}:metrics"  # Hash: cpu, memory, tasks_running
    ACTIVE_MACHINES = "machines:active"  # Set of online machine IDs
    MACHINE_ACCOUNT = "machine:{id}:account"  # String: linked account_id

    # Container state
    CONTAINER_PROCESSES = "container:processes"  # Hash of running processes
    CONTAINER_RESOURCES = "container:resources"  # Hash of resource usage

    # Skill execution queue
    SKILL_QUEUE = "skills:queue"  # List of pending skill executions

    # GitHub comment tracking (prevent infinite loops)
    GITHUB_POSTED_COMMENT = (
        "github:posted_comment:{id}"  # Track comment IDs posted by agent
    )

    # Slack message tracking (prevent infinite loops)
    SLACK_POSTED_MESSAGE = (
        "slack:posted_message:{ts}"  # Track message timestamps posted by agent
    )

    # Jira comment tracking (prevent infinite loops)
    JIRA_POSTED_COMMENT = (
        "jira:posted_comment:{id}"  # Track comment IDs posted by agent
    )


class RedisClient:
    """Async Redis client wrapper."""

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Connect to Redis."""
        self._client = redis.from_url(
            settings.redis_url, encoding="utf-8", decode_responses=True
        )
        logger.info("Connected to Redis", url=settings.redis_url)

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            logger.info("Disconnected from Redis")

    async def push_task(self, task_id: str) -> None:
        """Add task to queue."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.rpush("task_queue", task_id)
        logger.debug("Task pushed to queue", task_id=task_id)

    async def pop_task(self, timeout: int = 30) -> Optional[str]:
        """Pop task from queue (blocking)."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        result = await self._client.blpop("task_queue", timeout=timeout)
        if result:
            _, task_id = result
            logger.debug("Task popped from queue", task_id=task_id)
            return task_id
        return None

    async def set_task_status(self, task_id: str, status: str) -> None:
        """Set task status."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.set(f"task:{task_id}:status", status, ex=3600)

    async def get_task_status(self, task_id: str) -> Optional[str]:
        """Get task status."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.get(f"task:{task_id}:status")

    async def set_task_pid(self, task_id: str, pid: int) -> None:
        """Set task process ID."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.set(f"task:{task_id}:pid", str(pid), ex=3600)

    async def get_task_pid(self, task_id: str) -> Optional[int]:
        """Get task process ID."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        pid_str = await self._client.get(f"task:{task_id}:pid")
        return int(pid_str) if pid_str else None

    async def append_output(self, task_id: str, chunk: str) -> None:
        """Append output chunk to task."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.append(f"task:{task_id}:output", chunk)
        await self._client.expire(f"task:{task_id}:output", 3600)

    async def get_output(self, task_id: str) -> Optional[str]:
        """Get accumulated output."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.get(f"task:{task_id}:output")

    async def add_session_task(self, session_id: str, task_id: str) -> None:
        """Add task to session."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.sadd(f"session:{session_id}:tasks", task_id)
        await self._client.expire(f"session:{session_id}:tasks", 86400)

    async def get_session_tasks(self, session_id: str) -> List[str]:
        """Get all tasks for session."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return list(await self._client.smembers(f"session:{session_id}:tasks"))

    async def set_json(self, key: str, data: dict, ex: Optional[int] = None) -> None:
        """Set JSON data."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.set(key, json.dumps(data), ex=ex)

    async def get_json(self, key: str) -> Optional[dict]:
        """Get JSON data."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        data = await self._client.get(key)
        return json.loads(data) if data else None

    async def delete(self, key: str) -> None:
        """Delete key."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.delete(key)

    async def queue_length(self) -> int:
        """Get task queue length."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.llen("task_queue")

    # ==================== Subagent Management ====================

    async def add_active_subagent(
        self, subagent_id: str, status_data: Dict[str, Any]
    ) -> None:
        """Add subagent to active set and set its status."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.sadd(RedisKeys.ACTIVE_SUBAGENTS, subagent_id)
        await self._client.hset(
            RedisKeys.SUBAGENT_STATUS.format(id=subagent_id),
            mapping={
                "status": status_data.get("status", "running"),
                "mode": status_data.get("mode", "foreground"),
                "agent_name": status_data.get("agent_name", ""),
                "started_at": status_data.get(
                    "started_at", datetime.now(timezone.utc).isoformat()
                ),
                "permission_mode": status_data.get("permission_mode", "default"),
            },
        )
        await self._client.expire(
            RedisKeys.SUBAGENT_STATUS.format(id=subagent_id), 86400
        )
        logger.debug("Subagent added to active set", subagent_id=subagent_id)

    async def remove_active_subagent(self, subagent_id: str) -> None:
        """Remove subagent from active set."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.srem(RedisKeys.ACTIVE_SUBAGENTS, subagent_id)
        await self._client.delete(RedisKeys.SUBAGENT_STATUS.format(id=subagent_id))
        await self._client.delete(RedisKeys.SUBAGENT_OUTPUT.format(id=subagent_id))
        logger.debug("Subagent removed from active set", subagent_id=subagent_id)

    async def get_active_subagents(self) -> List[str]:
        """Get all active subagent IDs."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return list(await self._client.smembers(RedisKeys.ACTIVE_SUBAGENTS))

    async def get_active_subagent_count(self) -> int:
        """Get count of active subagents."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.scard(RedisKeys.ACTIVE_SUBAGENTS)

    async def get_subagent_status(self, subagent_id: str) -> Optional[Dict[str, str]]:
        """Get subagent status details."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        data = await self._client.hgetall(
            RedisKeys.SUBAGENT_STATUS.format(id=subagent_id)
        )
        return data if data else None

    async def update_subagent_status(self, subagent_id: str, status: str) -> None:
        """Update subagent status."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.hset(
            RedisKeys.SUBAGENT_STATUS.format(id=subagent_id), "status", status
        )

    async def append_subagent_output(self, subagent_id: str, chunk: str) -> None:
        """Append output chunk to subagent."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.append(
            RedisKeys.SUBAGENT_OUTPUT.format(id=subagent_id), chunk
        )
        await self._client.expire(
            RedisKeys.SUBAGENT_OUTPUT.format(id=subagent_id), 3600
        )

    async def get_subagent_output(self, subagent_id: str) -> Optional[str]:
        """Get accumulated subagent output."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.get(RedisKeys.SUBAGENT_OUTPUT.format(id=subagent_id))

    # ==================== Parallel Execution ====================

    async def create_parallel_group(
        self, group_id: str, subagent_ids: List[str]
    ) -> None:
        """Create a parallel execution group."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.sadd(
            RedisKeys.PARALLEL_GROUP.format(group_id=group_id), *subagent_ids
        )
        await self._client.hset(
            RedisKeys.PARALLEL_STATUS.format(group_id=group_id),
            mapping={
                "status": "running",
                "total": str(len(subagent_ids)),
                "completed": "0",
            },
        )
        await self._client.expire(
            RedisKeys.PARALLEL_GROUP.format(group_id=group_id), 86400
        )
        await self._client.expire(
            RedisKeys.PARALLEL_STATUS.format(group_id=group_id), 86400
        )

    async def get_parallel_group_agents(self, group_id: str) -> List[str]:
        """Get all subagent IDs in a parallel group."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return list(
            await self._client.smembers(
                RedisKeys.PARALLEL_GROUP.format(group_id=group_id)
            )
        )

    async def set_parallel_result(
        self, group_id: str, subagent_id: str, result: Dict[str, Any]
    ) -> None:
        """Set result for a subagent in parallel group."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.hset(
            RedisKeys.PARALLEL_RESULTS.format(group_id=group_id),
            subagent_id,
            json.dumps(result),
        )
        # Increment completed count
        await self._client.hincrby(
            RedisKeys.PARALLEL_STATUS.format(group_id=group_id), "completed", 1
        )
        await self._client.expire(
            RedisKeys.PARALLEL_RESULTS.format(group_id=group_id), 86400
        )

    async def get_parallel_results(self, group_id: str) -> Dict[str, Any]:
        """Get all results from parallel group."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        raw = await self._client.hgetall(
            RedisKeys.PARALLEL_RESULTS.format(group_id=group_id)
        )
        return {k: json.loads(v) for k, v in raw.items()}

    async def get_parallel_status(self, group_id: str) -> Optional[Dict[str, str]]:
        """Get parallel group status."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.hgetall(
            RedisKeys.PARALLEL_STATUS.format(group_id=group_id)
        )

    # ==================== Machine Management ====================

    async def register_machine(
        self, machine_id: str, account_id: Optional[str] = None
    ) -> None:
        """Register a machine as active."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.sadd(RedisKeys.ACTIVE_MACHINES, machine_id)
        await self._client.hset(
            RedisKeys.MACHINE_STATUS.format(id=machine_id),
            mapping={
                "status": "online",
                "heartbeat": datetime.now(timezone.utc).isoformat(),
            },
        )
        if account_id:
            await self._client.set(
                RedisKeys.MACHINE_ACCOUNT.format(id=machine_id), account_id
            )
        logger.debug("Machine registered", machine_id=machine_id)

    async def update_machine_heartbeat(self, machine_id: str) -> None:
        """Update machine heartbeat timestamp."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.hset(
            RedisKeys.MACHINE_STATUS.format(id=machine_id),
            "heartbeat",
            datetime.now(timezone.utc).isoformat(),
        )

    async def set_machine_status(self, machine_id: str, status: str) -> None:
        """Set machine status."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.hset(
            RedisKeys.MACHINE_STATUS.format(id=machine_id), "status", status
        )

    async def get_machine_status(self, machine_id: str) -> Optional[Dict[str, str]]:
        """Get machine status."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.hgetall(
            RedisKeys.MACHINE_STATUS.format(id=machine_id)
        )

    async def get_active_machines(self) -> List[str]:
        """Get all active machine IDs."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return list(await self._client.smembers(RedisKeys.ACTIVE_MACHINES))

    async def unregister_machine(self, machine_id: str) -> None:
        """Unregister a machine."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.srem(RedisKeys.ACTIVE_MACHINES, machine_id)
        await self._client.delete(RedisKeys.MACHINE_STATUS.format(id=machine_id))
        await self._client.delete(RedisKeys.MACHINE_METRICS.format(id=machine_id))
        await self._client.delete(RedisKeys.MACHINE_ACCOUNT.format(id=machine_id))

    async def set_machine_metrics(
        self, machine_id: str, metrics: Dict[str, Any]
    ) -> None:
        """Set machine resource metrics."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.hset(
            RedisKeys.MACHINE_METRICS.format(id=machine_id),
            mapping={k: str(v) for k, v in metrics.items()},
        )
        await self._client.expire(
            RedisKeys.MACHINE_METRICS.format(id=machine_id), 300
        )  # 5 min TTL

    async def get_machine_metrics(self, machine_id: str) -> Optional[Dict[str, str]]:
        """Get machine resource metrics."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.hgetall(
            RedisKeys.MACHINE_METRICS.format(id=machine_id)
        )

    # ==================== Container Management ====================

    async def set_container_resources(self, resources: Dict[str, Any]) -> None:
        """Set container resource usage."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.hset(
            RedisKeys.CONTAINER_RESOURCES,
            mapping={k: str(v) for k, v in resources.items()},
        )
        await self._client.expire(RedisKeys.CONTAINER_RESOURCES, 60)  # 1 min TTL

    async def get_container_resources(self) -> Optional[Dict[str, str]]:
        """Get container resource usage."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.hgetall(RedisKeys.CONTAINER_RESOURCES)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.exists(key) > 0

    # ==================== Task Event Publishing ====================

    async def publish_task_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        task_id: Optional[str] = None,
        webhook_event_id: Optional[str] = None,
    ) -> None:
        if not self._client:
            raise RuntimeError("Redis not connected")
        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": json.dumps(data),
        }
        if task_id:
            event["task_id"] = task_id
        if webhook_event_id:
            event["webhook_event_id"] = webhook_event_id
        await self._client.xadd("task_events", event)
        logger.debug("Task event published", event_type=event_type, task_id=task_id)


# Global Redis client instance
redis_client = RedisClient()
