"""Task worker that processes tasks from Redis queue."""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional
import structlog
import httpx

from core import settings, run_claude_cli
from core.subagent_config import load_subagent_config, get_default_subagents
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

            # Load sub-agent configuration (if enabled)
            subagents_json = None
            if settings.enable_subagents:
                # Try to load from agent directory
                subagents_json = load_subagent_config(agent_dir)
                # Fall back to default sub-agents if not found
                if not subagents_json:
                    subagents_json = get_default_subagents()
                    logger.debug("Using default sub-agent configuration")

            # Create output queue
            output_queue = asyncio.Queue()

            # Get appropriate model for agent type
            model = settings.get_model_for_agent(task_db.assigned_agent)
            
            logger.info(
                "selected_model_for_task",
                task_id=task_id,
                agent=task_db.assigned_agent,
                model=model
            )
            
            # Stream output to WebSocket and accumulate
            output_chunks = []
            
            async def stream_output():
                """Read from queue and stream to WebSocket/Redis."""
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

            # Execute CLI and stream output concurrently
            try:
                result, _ = await asyncio.gather(
                    run_claude_cli(
                        prompt=task_db.input_message,
                        working_dir=agent_dir,
                        output_queue=output_queue,
                        task_id=task_id,
                        timeout_seconds=settings.task_timeout_seconds,
                        model=model,
                        allowed_tools=settings.default_allowed_tools,
                        agents=subagents_json,
                    ),
                    stream_output()
                )

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
                    
                    # Send Slack notification if task came from webhook
                    if task_db.source == "webhook":
                        await self._send_slack_notification(
                            task_db=task_db,
                            success=True,
                            result=result.output,
                            error=None
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
                    
                    # Send Slack notification if task came from webhook
                    if task_db.source == "webhook":
                        await self._send_slack_notification(
                            task_db=task_db,
                            success=False,
                            result=None,
                            error=result.error
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
                
                # Send Slack notification for errors if task came from webhook
                try:
                    if task_db.source == "webhook":
                        await self._send_slack_notification(
                            task_db=task_db,
                            success=False,
                            result=None,
                            error=str(e)
                        )
                except Exception as notify_error:
                    logger.error("Slack notification error", error=str(notify_error))

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

    async def _send_slack_notification(
        self,
        task_db: TaskDB,
        success: bool,
        result: Optional[str] = None,
        error: Optional[str] = None
    ) -> bool:
        """Send Slack notification when webhook task completes."""
        if not os.getenv("SLACK_NOTIFICATIONS_ENABLED", "true").lower() == "true":
            return False
        
        slack_url = os.getenv("SLACK_WEBHOOK_URL")
        if not slack_url:
            logger.warning("SLACK_WEBHOOK_URL not configured, skipping notification")
            return False
        
        # Extract webhook metadata
        try:
            source_metadata = json.loads(task_db.source_metadata or "{}")
            webhook_source = source_metadata.get("webhook_source", "unknown")
            command = source_metadata.get("command", "unknown")
        except json.JSONDecodeError:
            webhook_source = "unknown"
            command = "unknown"
        
        # Build notification message
        status_emoji = "✅" if success else "❌"
        status_text = "Completed" if success else "Failed"
        
        message = {
            "channel": os.getenv("SLACK_NOTIFICATION_CHANNEL", "#ai-agent-activity"),
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{status_emoji} *Task {status_text}*\n*Source:* {webhook_source.title()}\n*Command:* {command}\n*Task ID:* `{task_db.task_id}`\n*Agent:* {task_db.assigned_agent}"
                    }
                }
            ]
        }
        
        if success and result:
            result_preview = result[:500] + "..." if len(result) > 500 else result
            message["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Result:*\n```{result_preview}```"
                }
            })
        
        if error:
            message["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Error:*\n```{error}```"
                }
            })
        
        # Add cost if available
        if task_db.cost_usd > 0:
            message["blocks"].append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Cost:* ${task_db.cost_usd:.4f}"
                    }
                ]
            })
        
        # Send to Slack
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(slack_url, json=message, timeout=10.0)
                response.raise_for_status()
                logger.info("slack_notification_sent", task_id=task_db.task_id, success=success)
                return True
        except Exception as e:
            logger.error("slack_notification_failed", task_id=task_db.task_id, error=str(e))
            return False

    def _get_agent_dir(self, agent_name: str | None) -> Path:
        """
        Get the directory for a given agent.
        
        Note: Sub-agents (planning, executor, orchestration) are now defined in 
        .claude/agents/*.md and invoked natively by Claude Code. This method 
        primarily handles user-uploaded custom agents.
        
        Priority:
        1. User-uploaded agents in /data/config/agents (persisted)
        2. Built-in sub-agents in .claude/agents/*.md (native Claude Code)
        3. Brain (default)
        """
        if not agent_name or agent_name == "brain":
            return settings.app_dir

        # Check user-uploaded agents FIRST (persisted in /data volume)
        user_agent_dir = settings.user_agents_dir / agent_name
        if user_agent_dir.exists():
            logger.debug("Using user-uploaded agent", agent_name=agent_name)
            return user_agent_dir

        # Check if it's a built-in sub-agent defined in .claude/agents/*.md
        builtin_subagent_file = settings.agents_dir / f"{agent_name}.md"
        if builtin_subagent_file.exists():
            logger.debug("Using built-in sub-agent (native Claude Code)", agent_name=agent_name)
            # Return app_dir - Claude Code will use the .claude/agents/*.md file
            return settings.app_dir

        logger.warning(
            "Agent not found in user or built-in directories, using brain",
            agent_name=agent_name,
            user_dir=str(user_agent_dir),
            builtin_subagent=str(builtin_subagent_file)
        )
        return settings.app_dir
