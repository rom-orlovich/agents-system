"""Worker that processes tasks from queue."""

import asyncio
from typing import Any
import structlog
from .queue_manager import QueueManager
from .cli.executor import get_executor

logger = structlog.get_logger()


class Worker:
    """Task processing worker."""

    def __init__(self, queue_manager: QueueManager, queue_name: str = "planning_tasks") -> None:
        self.queue_manager = queue_manager
        self.queue_name = queue_name
        self.executor = get_executor()
        self.running = False

    async def start(self) -> None:
        """Start worker loop."""
        self.running = True
        logger.info("worker_started", queue=self.queue_name)

        while self.running:
            try:
                task = await self.queue_manager.pop_task(self.queue_name, timeout=5)

                if task:
                    await self.process_task(task)

            except Exception as e:
                logger.error("worker_error", error=str(e))
                await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop worker loop."""
        self.running = False
        logger.info("worker_stopped")

    async def process_task(self, task: dict[str, Any]) -> None:
        """Process a single task."""
        task_id = task.get("task_id", "unknown")
        logger.info("processing_task", task_id=task_id)

        await self.queue_manager.set_task_status(task_id, "in_progress")

        try:
            result = await self.executor.execute(task)

            await self.queue_manager.set_task_status(
                task_id, result["status"], result.get("result")
            )

            logger.info("task_completed", task_id=task_id, status=result["status"])

        except Exception as e:
            logger.error("task_failed", task_id=task_id, error=str(e))
            await self.queue_manager.set_task_status(
                task_id, "failed", {"error": str(e)}
            )
