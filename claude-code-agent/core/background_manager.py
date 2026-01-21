"""Asyncio-based background task manager."""

import asyncio
from typing import Dict, AsyncIterator, Callable, Awaitable, Any
import structlog

from shared import Task, TaskStatus

logger = structlog.get_logger()


class BackgroundTaskManager:
    """Manages sub-agents as asyncio background tasks."""

    def __init__(self, max_workers: int = 5):
        self._semaphore = asyncio.Semaphore(max_workers)
        self._tasks: Dict[str, asyncio.Task] = {}
        self._output_queues: Dict[str, asyncio.Queue] = {}
        self._input_queues: Dict[str, asyncio.Queue] = {}

    async def submit(
        self,
        task: Task,
        runner_coro: Callable[..., Awaitable[Any]]
    ) -> str:
        """Submit task to run in background."""
        async def wrapped():
            async with self._semaphore:
                logger.info("Task started", task_id=task.task_id)
                try:
                    result = await runner_coro
                    logger.info("Task completed", task_id=task.task_id)
                    return result
                except Exception as e:
                    logger.error("Task failed", task_id=task.task_id, error=str(e))
                    raise

        self._output_queues[task.task_id] = asyncio.Queue()
        self._input_queues[task.task_id] = asyncio.Queue()

        asyncio_task = asyncio.create_task(wrapped())
        self._tasks[task.task_id] = asyncio_task

        return task.task_id

    async def stream_output(self, task_id: str) -> AsyncIterator[str]:
        """Yield output chunks as they're produced."""
        queue = self._output_queues.get(task_id)
        if not queue:
            logger.warning("No output queue for task", task_id=task_id)
            return

        while True:
            try:
                chunk = await asyncio.wait_for(queue.get(), timeout=30.0)
                if chunk is None:  # End of stream
                    break
                yield chunk
            except asyncio.TimeoutError:
                continue

    async def send_input(self, task_id: str, message: str) -> bool:
        """Send user input to running task."""
        queue = self._input_queues.get(task_id)
        if queue:
            await queue.put(message)
            logger.info("Input sent to task", task_id=task_id)
            return True
        logger.warning("No input queue for task", task_id=task_id)
        return False

    async def stop(self, task_id: str) -> bool:
        """Stop a running task."""
        task = self._tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            logger.info("Task cancelled", task_id=task_id)
            return True
        logger.warning("Task not found or already done", task_id=task_id)
        return False

    def get_task_status(self, task_id: str) -> str:
        """Get status of a background task."""
        task = self._tasks.get(task_id)
        if not task:
            return "not_found"
        if task.done():
            if task.cancelled():
                return "cancelled"
            if task.exception():
                return "failed"
            return "completed"
        return "running"

    def cleanup_completed(self) -> int:
        """Clean up completed tasks. Returns count of cleaned up tasks."""
        completed = [
            task_id for task_id, task in self._tasks.items()
            if task.done()
        ]

        for task_id in completed:
            del self._tasks[task_id]
            self._output_queues.pop(task_id, None)
            self._input_queues.pop(task_id, None)

        if completed:
            logger.info("Cleaned up completed tasks", count=len(completed))

        return len(completed)

    def active_count(self) -> int:
        """Get count of active (non-completed) tasks."""
        return sum(1 for task in self._tasks.values() if not task.done())
