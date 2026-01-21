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
    """Processes tasks from Redis queue."""

    def __init__(self, ws_hub: WebSocketHub):
        self.ws_hub = ws_hub
        self.running = False

    async def run(self) -> None:
        """Main worker loop."""
        self.running = True
        logger.info("Task worker started")

        while self.running:
            try:
                # Pop task from queue (blocking with timeout)
                task_id = await redis_client.pop_task(timeout=5)

                if task_id:
                    logger.info("Processing task", task_id=task_id)
                    await self._process_task(task_id)
                else:
                    # No task available, continue loop
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error("Worker error", error=str(e))
                await asyncio.sleep(5)

        logger.info("Task worker stopped")

    async def stop(self) -> None:
        """Stop the worker."""
        self.running = False

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

            # Update status to running
            task_db.status = TaskStatus.RUNNING
            await session.commit()

            # Update Redis status
            await redis_client.set_task_status(task_id, TaskStatus.RUNNING)

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
                    task_db.status = TaskStatus.COMPLETED
                    task_db.result = result.output
                    await redis_client.set_task_status(task_id, TaskStatus.COMPLETED)

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
                    task_db.status = TaskStatus.FAILED
                    task_db.error = result.error
                    await redis_client.set_task_status(task_id, TaskStatus.FAILED)

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
                task_db.status = TaskStatus.FAILED
                task_db.error = str(e)
                await redis_client.set_task_status(task_id, TaskStatus.FAILED)

                # Send failure message
                await self.ws_hub.send_to_session(
                    task_db.session_id,
                    TaskFailedMessage(task_id=task_id, error=str(e))
                )

                await session.commit()

    def _get_agent_dir(self, agent_name: str | None) -> Path:
        """Get directory for agent."""
        if not agent_name or agent_name == "brain":
            return settings.app_dir

        agent_dir = settings.agents_dir / agent_name
        if agent_dir.exists():
            return agent_dir

        logger.warning(
            "Agent directory not found, using brain",
            agent_name=agent_name,
            agent_dir=str(agent_dir)
        )
        return settings.app_dir
