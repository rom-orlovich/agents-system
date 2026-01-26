"""Task worker that processes tasks from Redis queue."""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional
import structlog
import httpx

from core import settings, run_claude_cli
from core.database import async_session_factory
from core.database.models import TaskDB, SessionDB, ConversationDB, ConversationMessageDB
from core.database.redis_client import redis_client
from core.websocket_hub import WebSocketHub
from core.webhook_engine import (
    generate_external_id,
    generate_webhook_conversation_id,
    generate_webhook_conversation_title,
    action_comment
)
from core.github_client import github_client
from core.jira_client import jira_client
from core.slack_client import slack_client
from core.sentry_client import sentry_client
from shared import TaskStatus, TaskOutputMessage, TaskCompletedMessage, TaskFailedMessage
from sqlalchemy import select, update
from datetime import datetime, timezone
import uuid

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
            task_db.started_at = datetime.now(timezone.utc)
            
            # Check if conversation already exists (created when task was created)
            source_metadata = json.loads(task_db.source_metadata or "{}")
            conversation_id = source_metadata.get("conversation_id")
            if not conversation_id and task_db.source == "webhook":
                # Fallback: create conversation if it wasn't created earlier
                await self._create_webhook_conversation(task_db, session)
            
            await session.commit()

            # Determine agent directory
            agent_dir = self._get_agent_dir(task_db.assigned_agent)

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
                # Send pre-job Slack notification for webhook tasks
                if task_db.source == "webhook":
                    await self._send_slack_job_start_notification(task_db)

                # Put initial log message in Redis for dashboard to show immediately
                init_log = f"[SYSTEM] Task {task_id} started at {datetime.now(timezone.utc).isoformat()}\n"
                init_log += f"[SYSTEM] Agent: {task_db.assigned_agent} | Model: {model}\n"
                init_log += f"[SYSTEM] Starting Claude CLI...\n"
                await redis_client.append_output(task_id, init_log)
                
                result, _ = await asyncio.gather(
                    run_claude_cli(
                        prompt=task_db.input_message,
                        working_dir=agent_dir,
                        output_queue=output_queue,
                        task_id=task_id,
                        timeout_seconds=settings.task_timeout_seconds,
                        model=model,
                        allowed_tools=settings.default_allowed_tools,
                        agents=None,  # Claude Code auto-discovers agents from .claude/agents/
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
                    clean_result_output = result.clean_output if hasattr(result, 'clean_output') and result.clean_output else result.output
                    task_db.completed_at = datetime.now(timezone.utc)
                    task_db.duration_seconds = (
                        (task_db.completed_at - task_db.started_at).total_seconds()
                        if task_db.started_at and task_db.completed_at
                        else 0.0
                    )

                    # Update conversation metrics if task has conversation_id
                    await self._update_conversation_metrics(task_db, session)

                    # Update Claude Code Task status if synced
                    await self._update_claude_task_status(task_db)

                    # Add response to conversation if task has one
                    await self._add_task_response_to_conversation(
                        task_db=task_db,
                        result=clean_result_output,
                        cost_usd=result.cost_usd,
                        session=session
                    )

                    # Send completion message
                    await self.ws_hub.send_to_session(
                        task_db.session_id,
                        TaskCompletedMessage(
                            task_id=task_id,
                            result=clean_result_output,
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
                        
                        await self._post_webhook_comment(
                            task_db=task_db,
                            message=clean_result_output,
                            success=True
                        )
                else:
                    # ✅ Update Redis first (fast)
                    await redis_client.set_task_status(task_id, TaskStatus.FAILED)

                    task_db.status = TaskStatus.FAILED
                    
                    error_text = ""
                    if result.error:
                        error_text += result.error
                    if result.output:
                        if error_text:
                            error_text += "\n" + result.output
                        else:
                            error_text = result.output
                    
                    task_db.error = error_text if error_text else None
                    task_db.completed_at = datetime.now(timezone.utc)
                    task_db.duration_seconds = (
                        (task_db.completed_at - task_db.started_at).total_seconds()
                        if task_db.started_at and task_db.completed_at
                        else 0.0
                    )

                    await self._update_conversation_metrics(task_db, session)
                    await self._update_claude_task_status(task_db)

                    if error_text:
                        error_lower = error_text.lower()
                        error_type = "unknown"
                        should_mark_inactive = False
                        
                        if "executive limit" in error_lower or "out of extra usage" in error_lower:
                            error_type = "executive_limit"
                            should_mark_inactive = True
                        elif "rate limit" in error_lower:
                            error_type = "rate_limit"
                            should_mark_inactive = True
                        elif "invalid api key" in error_lower or "please run /login" in error_lower or "authentication" in error_lower:
                            error_type = "authentication"
                            should_mark_inactive = True
                        elif "chunk is longer than limit" in error_lower or "separator is found, but chunk" in error_lower:
                            error_type = "chunk_size_limit"
                            if "Note: This error occurs" not in error_text:
                                error_text = f"{error_text}\n\nNote: This error occurs when processing very large files or responses. Try breaking the task into smaller parts or processing files individually."
                                task_db.error = error_text
                        
                        if should_mark_inactive:
                            session_result = await session.execute(
                                select(SessionDB).where(SessionDB.user_id == task_db.user_id)
                            )
                            sessions = session_result.scalars().all()
                            
                            if sessions:
                                updated_count = 0
                                for session_db in sessions:
                                    if session_db.active:
                                        session_db.active = False
                                        session.add(session_db)
                                        updated_count += 1
                                        
                                        from shared.machine_models import CLIStatusUpdateMessage
                                        await self.ws_hub.broadcast(
                                            CLIStatusUpdateMessage(session_id=session_db.session_id, active=False)
                                        )
                                
                                logger.warning(
                                    "CLI error detected - sessions marked inactive",
                                    task_id=task_id,
                                    user_id=task_db.user_id,
                                    sessions_updated=updated_count,
                                    error_type=error_type,
                                    error_preview=result.error[:200] if result.error else None,
                                    output_preview=result.output[:200] if result.output else None
                                )
                        else:
                            log_level = logger.warning
                            if error_type == "chunk_size_limit":
                                log_level = logger.info
                            
                            log_level(
                                "CLI error detected - session remains active",
                                task_id=task_id,
                                session_id=task_db.session_id,
                                error_type=error_type,
                                error_preview=result.error[:200] if result.error else None,
                                output_preview=result.output[:200] if result.output else None
                            )

                    # Log failure details
                    logger.warning(
                        "Task failed",
                        task_id=task_id,
                        error=result.error,
                        output_length=len(result.output) if result.output else 0,
                        output_preview=result.output[:200] if result.output else None
                    )

                    # Add error to conversation if task has one
                    await self._add_task_response_to_conversation(
                        task_db=task_db,
                        result=None,
                        error=result.error,
                        cost_usd=result.cost_usd,
                        session=session
                    )

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
                        error_message = f"❌ Task failed: {result.error}" if result.error else "❌ Task failed"
                        logger.info(
                            "Posting webhook comment for failed task",
                            task_id=task_id,
                            error_message=error_message[:100]
                        )
                        await self._post_webhook_comment(
                            task_db=task_db,
                            message=error_message,
                            success=False
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
                        
                        error_message = f"❌ Task error: {str(e)}"
                        await self._post_webhook_comment(
                            task_db=task_db,
                            message=error_message,
                            success=False
                        )
                except Exception as notify_error:
                    logger.error("Slack notification error", error=str(notify_error))

                # ✅ Update Redis first (fast)
                await redis_client.set_task_status(task_id, TaskStatus.FAILED)

                # Then update database
                task_db.status = TaskStatus.FAILED
                task_db.error = str(e)
                task_db.completed_at = datetime.now(timezone.utc)
                task_db.duration_seconds = (
                    (task_db.completed_at - task_db.started_at).total_seconds()
                    if task_db.started_at and task_db.completed_at
                    else 0.0
                )

                # Update conversation metrics if task has conversation_id
                await self._update_conversation_metrics(task_db, session)

                # Update Claude Code Task status if synced
                await self._update_claude_task_status(task_db)

                # Add error to conversation if task has one
                await self._add_task_response_to_conversation(
                    task_db=task_db,
                    result=None,
                    error=str(e),
                    cost_usd=0.0,
                    session=session
                )

                # Send failure message
                await self.ws_hub.send_to_session(
                    task_db.session_id,
                    TaskFailedMessage(task_id=task_id, error=str(e))
                )

                await session.commit()

    async def _create_webhook_conversation(
        self,
        task_db: TaskDB,
        session
    ) -> None:
        """Create or reuse conversation for webhook task based on external ID (fallback if not created earlier)."""
        try:
            # Parse source_metadata
            source_metadata = json.loads(task_db.source_metadata or "{}")
            webhook_source = source_metadata.get("webhook_source", "unknown")
            command = source_metadata.get("command", "unknown")
            payload = source_metadata.get("payload", {})
            
            # Generate external ID (Jira ticket key, PR number, etc.)
            external_id = generate_external_id(webhook_source, payload)
            
            # Generate stable conversation_id from external_id
            conversation_id = generate_webhook_conversation_id(external_id)
            
            # Flush any pending changes to ensure we see the latest state
            await session.flush()
            
            # Check if conversation already exists
            result = await session.execute(
                select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
            )
            existing_conversation = result.scalar_one_or_none()
            
            if existing_conversation:
                # Reuse existing conversation
                logger.info(
                    "webhook_conversation_reused_fallback",
                    task_id=task_db.task_id,
                    conversation_id=conversation_id,
                    external_id=external_id,
                    webhook_source=webhook_source
                )
                conversation_title = existing_conversation.title
            else:
                # Create new conversation
                conversation_title = generate_webhook_conversation_title(
                    webhook_source, payload, command
                )
                
                conversation = ConversationDB(
                    conversation_id=conversation_id,
                    user_id=task_db.user_id,
                    title=conversation_title,
                    metadata_json=json.dumps({
                        "webhook_source": webhook_source,
                        "external_id": external_id,
                        "command": command
                    }),
                )
                session.add(conversation)
                # Flush immediately to catch any IntegrityError
                try:
                    await session.flush()
                except Exception as flush_error:
                    # If UNIQUE constraint violation, conversation may have been created concurrently
                    from sqlalchemy.exc import IntegrityError
                    if isinstance(flush_error, IntegrityError) or "UNIQUE constraint" in str(flush_error):
                        # SQLAlchemy auto-rolls back on exception
                        # Check again if conversation exists
                        result = await session.execute(
                            select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
                        )
                        existing_conversation = result.scalar_one_or_none()
                        if existing_conversation:
                            conversation_title = existing_conversation.title
                            logger.info(
                                "webhook_conversation_reused_fallback_after_conflict",
                                task_id=task_db.task_id,
                                conversation_id=conversation_id,
                                external_id=external_id,
                                webhook_source=webhook_source
                            )
                        else:
                            raise
                    else:
                        raise
                else:
                    logger.info(
                        "webhook_conversation_created_fallback",
                        task_id=task_db.task_id,
                        conversation_id=conversation_id,
                        external_id=external_id,
                        webhook_source=webhook_source
                    )
            
            # Only add message if not already added by webhook handler
            # Check if a message with this task_id already exists
            existing_message_result = await session.execute(
                select(ConversationMessageDB)
                .where(ConversationMessageDB.task_id == task_db.task_id)
                .where(ConversationMessageDB.conversation_id == conversation_id)
            )
            existing_message = existing_message_result.scalar_one_or_none()

            if not existing_message:
                user_message_id = f"msg-{uuid.uuid4().hex[:12]}"
                user_message = ConversationMessageDB(
                    message_id=user_message_id,
                    conversation_id=conversation_id,
                    role="user",
                    content=task_db.input_message,
                    task_id=task_db.task_id,
                    metadata_json=json.dumps({
                        "webhook_source": webhook_source,
                        "command": command
                    }),
                )
                session.add(user_message)
                logger.info(
                    "webhook_conversation_message_added",
                    task_id=task_db.task_id,
                    conversation_id=conversation_id
                )
            else:
                logger.info(
                    "webhook_conversation_message_already_exists",
                    task_id=task_db.task_id,
                    conversation_id=conversation_id
                )
            
            # Update task metadata with conversation_id
            source_metadata["conversation_id"] = conversation_id
            task_db.source_metadata = json.dumps(source_metadata)
            
        except Exception as e:
            logger.error(
                "failed_to_create_webhook_conversation",
                task_id=task_db.task_id,
                error=str(e)
            )
            # Don't fail the task if conversation creation fails

    async def _add_task_response_to_conversation(
        self,
        task_db: TaskDB,
        result: Optional[str] = None,
        error: Optional[str] = None,
        cost_usd: float = 0.0,
        session = None
    ) -> None:
        """Add task response to conversation if task has a conversation_id."""
        try:
            # Parse source_metadata to get conversation_id
            source_metadata = json.loads(task_db.source_metadata or "{}")
            conversation_id = source_metadata.get("conversation_id")
            
            logger.debug(
                "checking_conversation_for_task",
                task_id=task_db.task_id,
                has_conversation_id=bool(conversation_id),
                source_metadata_keys=list(source_metadata.keys())
            )
            
            if not conversation_id:
                logger.debug("no_conversation_id_for_task", task_id=task_db.task_id, source=task_db.source)
                return  # No conversation associated with this task
            
            # Use provided session or create new one
            if session is None:
                async with async_session_factory() as db_session:
                    await self._add_message_to_conversation(
                        db_session, conversation_id, task_db.task_id, result, error, cost_usd
                    )
                    await db_session.commit()
            else:
                await self._add_message_to_conversation(
                    session, conversation_id, task_db.task_id, result, error, cost_usd
                )
            
            logger.info(
                "task_response_added_to_conversation",
                task_id=task_db.task_id,
                conversation_id=conversation_id,
                has_result=result is not None,
                has_error=error is not None
            )
        except Exception as e:
            logger.error(
                "failed_to_add_task_response_to_conversation",
                task_id=task_db.task_id,
                error=str(e)
            )
    
    async def _add_message_to_conversation(
        self,
        db_session,
        conversation_id: str,
        task_id: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
        cost_usd: float = 0.0
    ) -> None:
        """Helper to add a message to a conversation."""
        # Check if conversation exists
        conv_result = await db_session.execute(
            select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
        )
        conversation = conv_result.scalar_one_or_none()
        
        if not conversation:
            logger.warning("conversation_not_found", conversation_id=conversation_id)
            return
        
        # Build assistant message content from Claude CLI response
        if error:
            content = f"❌ Task failed: {error}"
        elif result:
            # Use the full Claude CLI output as the response
            content = result
            if cost_usd > 0:
                content += f"\n\n---\n✅ Task completed. Cost: ${cost_usd:.4f}"
        else:
            content = "Task completed (no output)"
        
        # Create assistant message
        message_id = f"msg-{uuid.uuid4().hex[:12]}"
        assistant_message = ConversationMessageDB(
            message_id=message_id,
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            task_id=task_id,
            metadata_json=json.dumps({
                "cost_usd": cost_usd,
                "has_error": error is not None
            }),
        )
        db_session.add(assistant_message)
        
        # Update conversation timestamp
        conversation.updated_at = datetime.now(timezone.utc)

    def _clean_error_message(self, error: str) -> str:
        """Clean error message by removing noise and extracting actual error text."""
        if not error:
            return error
        
        lines = error.split("\n")
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove [LOG] prefixes
            if line.startswith("[LOG]"):
                line = line[5:].strip()
            
            # Skip lines that are just noise
            if line.startswith("Exit code:") and len(cleaned_lines) > 0:
                # Exit code info - keep it but don't add if we already have error text
                continue
            
            # Skip empty lines after cleaning
            if line:
                cleaned_lines.append(line)
        
        if cleaned_lines:
            return "\n".join(cleaned_lines)
        return error
    
    def _format_error_for_platform(self, error: str, platform: str) -> str:
        """Format error message based on platform."""
        cleaned_error = self._clean_error_message(error)
        
        if platform == "github":
            # GitHub: Error emoji + clean message
            return f"❌ {cleaned_error}"
        elif platform == "jira":
            # Jira: Clean error message
            return cleaned_error
        elif platform == "slack":
            # Slack: Clean error message
            return cleaned_error
        else:
            # Default: Include status prefix
            return f"❌ {cleaned_error}"

    async def _post_webhook_comment(
        self,
        task_db: TaskDB,
        message: str,
        success: bool
    ) -> bool:
        try:
            source_metadata = json.loads(task_db.source_metadata or "{}")
            payload = source_metadata.get("payload", {})
            webhook_source = source_metadata.get("webhook_source", "unknown").lower()

            if not payload:
                logger.debug("no_payload_for_webhook_comment", task_id=task_db.task_id)
                return False

            if success:
                formatted_message = f"✅ {message}"
            else:
                formatted_message = self._format_error_for_platform(message, webhook_source)

            max_length = 8000 if not success else 4000
            if len(formatted_message) > max_length:
                truncated_message = formatted_message[:max_length]
                last_period = truncated_message.rfind(".")
                last_newline = truncated_message.rfind("\n")
                truncate_at = max(last_period, last_newline)
                if truncate_at > max_length * 0.8:
                    truncated_message = truncated_message[:truncate_at + 1]
                formatted_message = truncated_message + "\n\n... (message truncated)"

            if success and task_db.cost_usd > 0:
                formatted_message += f"\n\n💰 Cost: ${task_db.cost_usd:.4f}"

            posted = False

            if webhook_source == "github":
                repo = payload.get("repository", {})
                owner = repo.get("owner", {}).get("login", "")
                repo_name = repo.get("name", "")

                if owner and repo_name:
                    pr = payload.get("pull_request", {})
                    issue = payload.get("issue", {})

                    if pr and pr.get("number"):
                        pr_number = pr.get("number")
                        await github_client.post_pr_comment(owner, repo_name, pr_number, formatted_message)
                        logger.info("github_pr_comment_posted", pr_number=pr_number, task_id=task_db.task_id)
                        posted = True
                    elif issue and issue.get("number"):
                        issue_number = issue.get("number")
                        await github_client.post_issue_comment(owner, repo_name, issue_number, formatted_message)
                        logger.info("github_issue_comment_posted", issue_number=issue_number, task_id=task_db.task_id)
                        posted = True
                    else:
                        logger.warning("github_no_issue_or_pr_found", task_id=task_db.task_id)

            elif webhook_source == "jira":
                issue = payload.get("issue", {})
                issue_key = issue.get("key")

                if issue_key:
                    await jira_client.post_comment(issue_key, formatted_message)
                    logger.info("jira_comment_posted", issue_key=issue_key, task_id=task_db.task_id)
                    posted = True
                else:
                    logger.warning("jira_no_issue_key_found", task_id=task_db.task_id)

            elif webhook_source == "slack":
                event = payload.get("event", {})
                channel = event.get("channel")
                thread_ts = event.get("ts")

                if channel:
                    await slack_client.post_message(
                        channel=channel,
                        text=formatted_message,
                        thread_ts=thread_ts
                    )
                    logger.info("slack_message_posted", channel=channel, task_id=task_db.task_id)
                    posted = True
                else:
                    logger.warning("slack_no_channel_found", task_id=task_db.task_id)

            elif webhook_source == "sentry":
                issue_data = payload.get("data", {}).get("issue", {})
                issue_id = issue_data.get("id")

                if issue_id:
                    await sentry_client.add_comment(issue_id, formatted_message)
                    logger.info("sentry_comment_posted", issue_id=issue_id, task_id=task_db.task_id)
                    posted = True
                else:
                    logger.warning("sentry_no_issue_id_found", task_id=task_db.task_id)
            else:
                logger.warning("unknown_webhook_source", webhook_source=webhook_source, task_id=task_db.task_id)

            if posted:
                logger.info(
                    "webhook_comment_posted",
                    task_id=task_db.task_id,
                    webhook_source=webhook_source,
                    success=success
                )
            return posted

        except Exception as e:
            logger.error(
                "webhook_comment_error",
                task_id=task_db.task_id,
                webhook_source=source_metadata.get("webhook_source", "unknown") if 'source_metadata' in dir() else "unknown",
                error=str(e)
            )
            return False

    async def _send_slack_job_start_notification(
        self,
        task_db: TaskDB
    ) -> bool:
        """Send Slack notification when webhook task starts."""
        if not os.getenv("SLACK_NOTIFICATIONS_ENABLED", "true").lower() == "true":
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
        message = {
            "channel": os.getenv("SLACK_NOTIFICATION_CHANNEL", "#ai-agent-activity"),
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🚀 *Job Started*\n*Source:* {webhook_source.title()}\n*Command:* {command}\n*Task ID:* `{task_db.task_id}`\n*Agent:* {task_db.assigned_agent}"
                    }
                }
            ]
        }

        # Get Slack bot token
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        if not slack_token:
            logger.debug("slack_bot_token_not_configured", task_id=task_db.task_id)
            return False

        # Send to Slack using API
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {slack_token}",
                        "Content-Type": "application/json"
                    },
                    json=message,
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()
                if not result.get("ok"):
                    logger.error("slack_api_error", task_id=task_db.task_id, error=result.get("error"))
                    return False
                logger.info("slack_job_start_notification_sent", task_id=task_db.task_id)
                return True
        except Exception as e:
            logger.error("slack_job_start_notification_failed", task_id=task_db.task_id, error=str(e))
            return False

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
        
        # Get Slack bot token (use Slack API, not webhook URL)
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        if not slack_token:
            logger.debug("slack_bot_token_not_configured", task_id=task_db.task_id)
            return False
        
        # Send to Slack using API
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {slack_token}",
                        "Content-Type": "application/json"
                    },
                    json=message,
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()
                if not result.get("ok"):
                    logger.error("slack_api_error", task_id=task_db.task_id, error=result.get("error"))
                    return False
                logger.info("slack_notification_sent", task_id=task_db.task_id, success=success)
                return True
        except Exception as e:
            logger.error("slack_notification_failed", task_id=task_db.task_id, error=str(e))
            return False

    async def _update_conversation_metrics(
        self,
        task_db: TaskDB,
        session
    ) -> None:
        """Update conversation metrics when task completes."""
        try:
            # Extract conversation_id from source_metadata
            source_metadata = json.loads(task_db.source_metadata or "{}")
            conversation_id = source_metadata.get("conversation_id")
            
            if not conversation_id:
                return  # No conversation associated with this task
            
            # Update conversation metrics
            from core.database.models import update_conversation_metrics
            await update_conversation_metrics(conversation_id, task_db, session)
            
            logger.info(
                "conversation_metrics_updated",
                task_id=task_db.task_id,
                conversation_id=conversation_id,
                cost_usd=task_db.cost_usd,
                duration_seconds=task_db.duration_seconds
            )
        except Exception as e:
            logger.warning(
                "failed_to_update_conversation_metrics",
                task_id=task_db.task_id,
                error=str(e)
            )
            # Don't fail the task if metrics update fails
    
    async def _update_claude_task_status(
        self,
        task_db: TaskDB
    ) -> None:
        """Update Claude Code Task status when orchestration task completes."""
        try:
            from core.claude_tasks_sync import update_claude_task_status
            
            # Extract claude_task_id from source_metadata
            source_metadata = json.loads(task_db.source_metadata or "{}")
            claude_task_id = source_metadata.get("claude_task_id")
            
            if not claude_task_id:
                return  # Task not synced to Claude Code Tasks
            
            # Map TaskStatus to Claude Code task status
            status_map = {
                TaskStatus.COMPLETED: "completed",
                TaskStatus.FAILED: "failed",
            }
            claude_status = status_map.get(task_db.status)
            
            if claude_status:
                update_claude_task_status(
                    claude_task_id=claude_task_id,
                    status=claude_status,
                    result=task_db.result
                )
                
                logger.info(
                    "claude_task_status_updated",
                    task_id=task_db.task_id,
                    claude_task_id=claude_task_id,
                    status=claude_status
                )
        except Exception as e:
            logger.warning(
                "failed_to_update_claude_task_status",
                task_id=task_db.task_id,
                error=str(e)
            )
            # Don't fail the task if Claude Code Task update fails

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
