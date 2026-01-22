"""Task worker that processes tasks from Redis queue."""

import asyncio
from pathlib import Path
import structlog

from core import settings, run_claude_cli
from core.database import async_session_factory
from core.database.models import TaskDB
from core.database.redis_client import redis_client
from core.websocket_hub import WebSocketHub
from shared import TaskStatus, TaskOutputMessage, TaskCompletedMessage, TaskFailedMessage
from sqlalchemy import select, update

logger = structlog.get_logger()


class TaskWorker:
    """Processes tasks from Redis queue with concurrent execution."""

    def __init__(self, ws_hub: WebSocketHub):
        self.ws_hub = ws_hub
        self.running = False
        # Semaphore to limit concurrent tasks
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_tasks)
        # Track active tasks for graceful shutdown
        self.active_tasks: set[asyncio.Task] = set()

    async def run(self) -> None:
        """
        Main worker loop - processes tasks concurrently up to max_concurrent_tasks limit.

        Each task is launched in parallel without blocking the queue popping.
        The semaphore ensures we don't exceed the concurrency limit.
        """
        self.running = True
        logger.info(
            "Task worker started",
            max_concurrent_tasks=settings.max_concurrent_tasks
        )

        while self.running:
            try:
                # Pop task from queue (blocking with timeout)
                task_id = await redis_client.pop_task(timeout=5)

                if task_id:
                    logger.info("Queueing task for processing", task_id=task_id)

                    # ✅ Launch task concurrently (don't await)
                    task = asyncio.create_task(self._process_with_semaphore(task_id))

                    # Track active tasks
                    self.active_tasks.add(task)

                    # Remove from set when done (auto-cleanup)
                    task.add_done_callback(self.active_tasks.discard)

                else:
                    # No task available, continue loop
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error("Worker error", error=str(e))
                await asyncio.sleep(5)

        logger.info("Task worker stopped")

    async def stop(self) -> None:
        """Stop the worker gracefully."""
        logger.info("Stopping task worker")
        self.running = False

    async def wait_for_active_tasks(self, timeout: int = 30) -> None:
        """
        Wait for all active tasks to complete (for graceful shutdown).

        Args:
            timeout: Maximum seconds to wait for tasks to complete
        """
        if not self.active_tasks:
            return

        logger.info(
            "Waiting for active tasks to complete",
            active_count=len(self.active_tasks),
            timeout=timeout
        )

        try:
            await asyncio.wait_for(
                asyncio.gather(*self.active_tasks, return_exceptions=True),
                timeout=timeout
            )
            logger.info("All active tasks completed")
        except asyncio.TimeoutError:
            logger.warning(
                "Active tasks did not complete in time",
                remaining=len(self.active_tasks)
            )

    async def _process_with_semaphore(self, task_id: str) -> None:
        """
        Process task with semaphore-controlled concurrency.

        This ensures max_concurrent_tasks limit is respected.
        """
        async with self.semaphore:
            logger.debug(
                "Task acquired semaphore slot",
                task_id=task_id,
                active_tasks=settings.max_concurrent_tasks - self.semaphore._value
            )
            await self._process_task(task_id)

    async def _process_task(self, task_id: str) -> None:
        """Process a single task."""
        async with async_session_factory() as session:
            # Get task from database
            result = await session.execute(
                select(TaskDB).where(TaskDB.task_id == task_id)
            )
            task_db = result.scalar_one_or_none()

            if not task_db:
                logger.error("Task not found in database", task_id=task_id)
                return

            # ✅ Update Redis first (fast ~1ms) to minimize inconsistency window
            await redis_client.set_task_status(task_id, TaskStatus.RUNNING)

            # Then update database (slow ~10-100ms)
            task_db.status = TaskStatus.RUNNING
            await session.commit()

            # Determine agent directory
            agent_dir = self._get_agent_dir(task_db.assigned_agent)

            # Create output queue
            output_queue = asyncio.Queue()

            # Start CLI runner
            cli_task = asyncio.create_task(
                run_claude_cli(
                    prompt=task_db.input_message,
                    working_dir=agent_dir,
                    output_queue=output_queue,
                    task_id=task_id,
                    timeout_seconds=settings.task_timeout_seconds,
                )
            )

            # Stream output to WebSocket and accumulate
            output_chunks = []
            try:
                while True:
                    chunk = await output_queue.get()
                    if chunk is None:  # End of stream
                        break

                    output_chunks.append(chunk)

                    # Stream to WebSocket
                    await self.ws_hub.send_to_session(
                        task_db.session_id,
                        TaskOutputMessage(task_id=task_id, chunk=chunk)
                    )

                    # Append to Redis
                    await redis_client.append_output(task_id, chunk)

                # Wait for CLI to complete
                result = await cli_task

                # Update task with result
                task_db.output_stream = "".join(output_chunks)
                task_db.cost_usd = result.cost_usd
                task_db.input_tokens = result.input_tokens
                task_db.output_tokens = result.output_tokens

                if result.success:
                    # ✅ Update Redis first (fast)
                    await redis_client.set_task_status(task_id, TaskStatus.COMPLETED)

                    # Then update database
                    task_db.status = TaskStatus.COMPLETED
                    task_db.result = result.output

                    # Send completion message
                    await self.ws_hub.send_to_session(
                        task_db.session_id,
                        TaskCompletedMessage(
                            task_id=task_id,
                            result=result.output,
                            cost_usd=result.cost_usd
                        )
                    )
                else:
                    # ✅ Update Redis first (fast)
                    await redis_client.set_task_status(task_id, TaskStatus.FAILED)

                    # Then update database
                    task_db.status = TaskStatus.FAILED
                    task_db.error = result.error

                    # Send failure message
                    await self.ws_hub.send_to_session(
                        task_db.session_id,
                        TaskFailedMessage(task_id=task_id, error=result.error or "Unknown error")
                    )

                await session.commit()

                logger.info(
                    "Task completed",
                    task_id=task_id,
                    status=task_db.status,
                    cost_usd=result.cost_usd
                )

            except Exception as e:
                logger.error("Task processing error", task_id=task_id, error=str(e))

                # ✅ Update Redis first (fast)
                await redis_client.set_task_status(task_id, TaskStatus.FAILED)

                # Then update database
                task_db.status = TaskStatus.FAILED
                task_db.error = str(e)

                # Send failure message
                await self.ws_hub.send_to_session(
                    task_db.session_id,
                    TaskFailedMessage(task_id=task_id, error=str(e))
                )

                await session.commit()

    def _get_agent_dir(self, agent_name: str | None) -> Path:
        """
        Get directory for agent.

        Priority:
        1. User-uploaded agents in /data/config/agents (PERSISTED)
        2. Built-in agents in /app/agents (read-only from image)
        3. Brain (default)
        """
        if not agent_name or agent_name == "brain":
            return settings.app_dir

        # Check user-uploaded agents FIRST (persisted in /data volume)
        user_agent_dir = settings.user_agents_dir / agent_name
        if user_agent_dir.exists():
            logger.debug("Using user-uploaded agent", agent_name=agent_name)
            return user_agent_dir

        # Fall back to built-in agents (from Docker image)
        builtin_agent_dir = settings.agents_dir / agent_name
        if builtin_agent_dir.exists():
            logger.debug("Using built-in agent", agent_name=agent_name)
            return builtin_agent_dir

        logger.warning(
            "Agent directory not found in user or built-in directories, using brain",
            agent_name=agent_name,
            user_dir=str(user_agent_dir),
            builtin_dir=str(builtin_agent_dir)
        )
        return settings.app_dir
