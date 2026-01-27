"""Webhook command execution engine."""

import uuid
import json
import re
import os
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import httpx
import hashlib

from core.database.models import WebhookCommandDB, TaskDB, SessionDB, WebhookEventDB, ConversationDB, ConversationMessageDB
from core.database.redis_client import redis_client
from shared import TaskStatus, AgentType

logger = structlog.get_logger()




def generate_external_id(webhook_source: str, payload: dict) -> Optional[str]:
    """Generate a stable external ID from webhook payload (for dynamic webhooks)."""
    # Generic extraction - look for common ID fields
    if "issue" in payload:
        issue = payload.get("issue", {})
        issue_key = issue.get("key") or issue.get("number")
        if issue_key:
            return f"{webhook_source}:{issue_key}"
    
    if "event" in payload:
        event = payload.get("event", {})
        event_id = event.get("event_id") or event.get("id")
        if event_id:
            return f"{webhook_source}:{event_id}"
    
    # Try to find any ID-like field
    for key in ["id", "key", "number", "external_id"]:
        if key in payload and payload[key]:
            return f"{webhook_source}:{payload[key]}"
    
    return None


def generate_flow_id(external_id: Optional[str]) -> str:
    """Generate a stable flow_id from external_id for end-to-end task flow tracking."""
    if external_id:
        # Create a stable hash-based ID from external_id
        hash_obj = hashlib.md5(external_id.encode())
        hash_hex = hash_obj.hexdigest()[:16]  # Longer hash for flow_id
        return f"flow-{hash_hex}"
    else:
        # Fallback to UUID if no external_id
        return f"flow-{uuid.uuid4().hex[:16]}"


def should_start_new_conversation(prompt: str, metadata: dict) -> bool:
    """
    Detect if user explicitly wants to start a new conversation.
    
    Checks for:
    - Keywords: "new conversation", "start fresh", "new context", "reset conversation"
    - Metadata flag: new_conversation: true
    
    Args:
        prompt: User prompt text
        metadata: Task metadata dictionary
        
    Returns:
        True if new conversation should be started, False otherwise
    """
    # Check metadata flag first (takes precedence)
    if "new_conversation" in metadata:
        return bool(metadata["new_conversation"])
    
    # Check for keywords in prompt (case-insensitive)
    prompt_lower = prompt.lower()
    keywords = [
        "new conversation",
        "start fresh",
        "new context",
        "reset conversation"
    ]
    
    for keyword in keywords:
        if keyword in prompt_lower:
            return True
    
    return False


def generate_webhook_conversation_id(external_id: Optional[str]) -> str:
    """Generate a stable conversation_id from external_id."""
    if external_id:
        # Create a stable hash-based ID from external_id
        hash_obj = hashlib.md5(external_id.encode())
        hash_hex = hash_obj.hexdigest()[:12]
        return f"conv-{hash_hex}"
    else:
        # Fallback to UUID if no external_id
        return f"conv-{uuid.uuid4().hex[:12]}"


def generate_webhook_conversation_title(webhook_source: str, payload: dict, command: str) -> str:
    """Generate conversation title based on webhook source and payload (for dynamic webhooks)."""
    webhook_name = payload.get("webhook_name", webhook_source)
    
    # Try to extract a meaningful identifier
    identifier = None
    if "issue" in payload:
        issue = payload.get("issue", {})
        identifier = issue.get("key") or issue.get("number")
        title_text = issue.get("title") or issue.get("fields", {}).get("summary")
    elif "event" in payload:
        event = payload.get("event", {})
        identifier = event.get("event_id") or event.get("id")
        title_text = event.get("title")
    else:
        title_text = payload.get("title") or payload.get("summary")
        identifier = payload.get("id") or payload.get("key") or payload.get("number")
    
    if identifier:
        title = f"{webhook_name.title()}: {identifier} - {command}"
        if title_text:
            title += f" ({str(title_text)[:40]})"
        return title
    
    return f"{webhook_name.title()} Webhook - {command}"


async def get_or_create_flow_conversation(
    flow_id: str,
    external_id: Optional[str],
    task_db: TaskDB,
    db: AsyncSession
) -> ConversationDB:
    """
    Get or create conversation for a flow.
    
    If conversation with flow_id exists, reuse it.
    Otherwise, create new conversation with flow_id and initiated_task_id.
    
    Args:
        flow_id: Flow ID for end-to-end tracking
        external_id: External ID (e.g., Jira ticket key)
        task_db: Task database model
        db: Database session
        
    Returns:
        ConversationDB instance
    """
    # Check if conversation with this flow_id already exists
    result = await db.execute(
        select(ConversationDB).where(ConversationDB.flow_id == flow_id)
    )
    existing_conversation = result.scalar_one_or_none()
    
    if existing_conversation:
        # Reuse existing conversation
        logger.info(
            "flow_conversation_reused",
            flow_id=flow_id,
            conversation_id=existing_conversation.conversation_id,
            task_id=task_db.task_id
        )
        return existing_conversation
    
    # Create new conversation for this flow
    conversation_id = generate_webhook_conversation_id(external_id)
    
    # Flush any pending changes to ensure we see the latest state
    await db.flush()
    
    # Check if conversation with this conversation_id already exists (may have been created by another flow)
    result = await db.execute(
        select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
    )
    existing_by_id = result.scalar_one_or_none()
    
    if existing_by_id:
        # Conversation exists but may not have this flow_id - update it
        if existing_by_id.flow_id != flow_id:
            existing_by_id.flow_id = flow_id
            existing_by_id.initiated_task_id = task_db.task_id
            db.add(existing_by_id)
        logger.info(
            "flow_conversation_reused_by_id",
            flow_id=flow_id,
            conversation_id=conversation_id,
            task_id=task_db.task_id
        )
        return existing_by_id
    
    # Parse source_metadata for title generation
    source_metadata = json.loads(task_db.source_metadata or "{}")
    webhook_source = source_metadata.get("webhook_source", "unknown")
    command = source_metadata.get("command", "task")
    payload = source_metadata.get("payload", {})
    
    conversation_title = generate_webhook_conversation_title(
        webhook_source, payload, command
    )
    
    conversation = ConversationDB(
        conversation_id=conversation_id,
        user_id=task_db.user_id,
        title=conversation_title,
        flow_id=flow_id,
        initiated_task_id=task_db.task_id,
        metadata_json=json.dumps({
            "webhook_source": webhook_source,
            "external_id": external_id,
            "command": command
        }),
    )
    db.add(conversation)
    
    try:
        await db.flush()
    except Exception as flush_error:
        # If UNIQUE constraint violation, conversation may have been created concurrently
        from sqlalchemy.exc import IntegrityError
        if isinstance(flush_error, IntegrityError) or "UNIQUE constraint" in str(flush_error):
            # SQLAlchemy auto-rolls back on exception
            # Check again if conversation exists (may have been created by concurrent request)
            # Check by conversation_id first (the UNIQUE constraint)
            result = await db.execute(
                select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
            )
            existing_conversation = result.scalar_one_or_none()
            
            if existing_conversation:
                # Update flow_id if needed
                if existing_conversation.flow_id != flow_id:
                    existing_conversation.flow_id = flow_id
                    existing_conversation.initiated_task_id = task_db.task_id
                    db.add(existing_conversation)
                logger.info(
                    "flow_conversation_reused_after_conflict",
                    flow_id=flow_id,
                    conversation_id=conversation_id,
                    task_id=task_db.task_id
                )
                return existing_conversation
        
        # If not a UNIQUE constraint error, or conversation still doesn't exist, re-raise
        logger.error(
            "failed_to_create_flow_conversation",
            flow_id=flow_id,
            conversation_id=conversation_id,
            task_id=task_db.task_id,
            error=str(flush_error)
        )
        raise
    
    logger.info(
        "flow_conversation_created",
        flow_id=flow_id,
        conversation_id=conversation_id,
        task_id=task_db.task_id,
        external_id=external_id
    )
    
    return conversation


async def create_webhook_conversation(
    task_db: TaskDB,
    db: AsyncSession
) -> str:
    """Create or reuse conversation for webhook task based on external ID (Jira ticket, PR number, etc.)."""
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
        await db.flush()
        
        # Check if conversation already exists
        result = await db.execute(
            select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
        )
        existing_conversation = result.scalar_one_or_none()
        
        if existing_conversation:
            # Reuse existing conversation
            logger.info(
                "webhook_conversation_reused",
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
            db.add(conversation)
            # Flush immediately to catch any IntegrityError
            try:
                await db.flush()
            except Exception as flush_error:
                # If UNIQUE constraint violation, conversation may have been created concurrently
                from sqlalchemy.exc import IntegrityError
                if isinstance(flush_error, IntegrityError) or "UNIQUE constraint" in str(flush_error):
                    # SQLAlchemy auto-rolls back on exception
                    # Check again if conversation exists (may have been created by concurrent request)
                    result = await db.execute(
                        select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
                    )
                    existing_conversation = result.scalar_one_or_none()
                    if existing_conversation:
                        conversation_title = existing_conversation.title
                        logger.info(
                            "webhook_conversation_reused_after_conflict",
                            task_id=task_db.task_id,
                            conversation_id=conversation_id,
                            external_id=external_id,
                            webhook_source=webhook_source
                        )
                    else:
                        # Re-raise if conversation still doesn't exist
                        raise
                else:
                    # Re-raise if it's not a duplicate issue
                    raise
            else:
                logger.info(
                    "webhook_conversation_created",
                    task_id=task_db.task_id,
                    conversation_id=conversation_id,
                    external_id=external_id,
                    webhook_source=webhook_source
                )
        
        # Always add a new message to the conversation (even if reusing conversation)
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
        db.add(user_message)
        
        # Update task metadata with conversation_id
        source_metadata["conversation_id"] = conversation_id
        task_db.source_metadata = json.dumps(source_metadata)
        
        # Mark task_db as modified in the session
        db.add(task_db)
        
        logger.info(
            "webhook_conversation_created",
            task_id=task_db.task_id,
            conversation_id=conversation_id,
            webhook_source=webhook_source,
            title=conversation_title,
            source_metadata_updated=True
        )
        
        return conversation_id
        
    except Exception as e:
        logger.error(
            "failed_to_create_webhook_conversation",
            task_id=task_db.task_id,
            error=str(e)
        )
        return None


def truncate_content_intelligently(content: Optional[str], max_size: int) -> str:
    """
    Truncate content intelligently, preserving structure when possible.
    
    Args:
        content: Content to truncate (can be None)
        max_size: Maximum size in characters
        
    Returns:
        Truncated content with "... (truncated)" indicator if truncated
    """
    if not content:
        return ""
    
    if len(content) <= max_size:
        return content
    
    truncated = content[:max_size]
    
    # Try to truncate at sentence boundary
    last_period = truncated.rfind(".")
    last_newline = truncated.rfind("\n")
    last_exclamation = truncated.rfind("!")
    last_question = truncated.rfind("?")
    
    sentence_end = max(last_period, last_newline, last_exclamation, last_question)
    
    # If we found a good boundary (within 80% of max_size), use it
    if sentence_end > max_size * 0.8:
        truncated = truncated[:sentence_end + 1]
    
    # Try to preserve markdown structure - don't truncate in middle of code block
    if "```" in truncated:
        code_blocks = truncated.count("```")
        if code_blocks % 2 == 1:
            # Unclosed code block - remove it
            last_code_start = truncated.rfind("```")
            truncated = truncated[:last_code_start]
    
    return truncated + "\n\n... (truncated)"


def render_template(template: str, payload: dict, task_id: Optional[str] = None) -> str:
    """
    Render template with payload data using {{variable}} syntax.
    Supports nested access like {{user.profile.name}} and array access {{labels.0.name}}.
    Also supports {{task_id}} and {{task_file}} variables for task directory references.
    """
    def get_nested_value(obj: Any, path: str) -> Any:
        """Get nested value from object using dot notation."""
        parts = path.split('.')
        current = obj
        
        for part in parts:
            if current is None:
                return None
            
            # Handle array access
            if part.isdigit() and isinstance(current, list):
                index = int(part)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return None
            # Handle dict access
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        
        return current
    
    if task_id:
        payload = {**payload, "task_id": task_id}
        claude_task_id = f"claude-task-{task_id}"
        task_file = f"~/.claude/tasks/{claude_task_id}.json"
        payload["task_file"] = task_file
    
    # Find all {{variable}} patterns
    pattern = r'\{\{([^}]+)\}\}'
    
    def replace_var(match):
        var_path = match.group(1).strip()
        value = get_nested_value(payload, var_path)
        
        if value is None:
            return match.group(0)  # Keep original if not found
        
        value_str = str(value)
        
        # Apply truncation for large content fields
        from core.config import settings
        
        # Truncate comment.body and issue.body if they exceed limits
        if var_path in ["comment.body", "issue.body"] and len(value_str) > settings.max_comment_body_size:
            value_str = truncate_content_intelligently(value_str, settings.max_comment_body_size)
        
        return value_str
    
    return re.sub(pattern, replace_var, template)


def wrap_prompt_with_brain_instructions(template: str, task_id: Optional[str] = None) -> str:
    """
    Wrap a prompt template with brain agent instructions for automatic subagent execution.
    
    Args:
        template: Original prompt template
        task_id: Optional task ID to include in instructions
        
    Returns:
        Wrapped prompt with brain instructions
    """
    task_id_part = f"\nTask ID: {task_id}" if task_id else ""
    task_file_part = f"\nTask file: ~/.claude/tasks/claude-task-{task_id}.json" if task_id else ""
    task_ref_part = f"~/.claude/tasks/claude-task-{task_id}.json" if task_id else "the tasks directory"
    
    brain_instructions = f"""You are the brain agent. Review this task and automatically select and execute the appropriate subagent(s) to handle it.{task_id_part}{task_file_part}

Instructions:
1. Analyze the task content and determine complexity
2. Select relevant skills for this task (e.g., webhook-management, testing, refactoring-advisor)
3. Decide which subagent(s) are needed:
   - Single subagent for simple tasks (planning for analysis, executor for implementation, etc.)
   - Multiple subagents for complex tasks (e.g., planning → executor → testing)
4. Reference this task in the tasks directory: {task_ref_part}
5. Automatically invoke the selected subagent(s) with full task context
6. Tell each subagent to select relevant skills for their part of the task
7. For multi-subagent workflows, coordinate them sequentially or in parallel as needed
8. Each subagent should execute their part, not just analyze
9. Use the tasks directory to track dependencies and results between subagents

Task:
{template}"""
    
    return brain_instructions


def match_commands(
    commands: List[WebhookCommandDB],
    event_type: str,
    payload: dict
) -> List[WebhookCommandDB]:
    """
    Match commands based on trigger and conditions.
    Returns matched commands sorted by priority (lowest first).
    """
    matched = []
    
    for command in commands:
        # Check if trigger matches
        if command.trigger != event_type:
            continue
        
        # Check conditions if present
        if command.conditions_json:
            try:
                conditions = json.loads(command.conditions_json)
                if not check_conditions(conditions, payload):
                    continue
            except json.JSONDecodeError:
                logger.warning("invalid_conditions_json", command_id=command.command_id)
                continue
        
        matched.append(command)
    
    # Sort by priority (lowest number = highest priority)
    matched.sort(key=lambda c: c.priority)
    
    return matched


def check_conditions(conditions: dict, payload: dict) -> bool:
    """Check if payload matches all conditions."""
    for key, expected_value in conditions.items():
        # Handle nested keys like "label.name"
        parts = key.split('.')
        current = payload
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return False
        
        # Special handling for label conditions
        if key == "label" and isinstance(current, dict):
            current = current.get("name")
        
        if current != expected_value:
            return False
    
    return True


async def execute_command(
    command: WebhookCommandDB,
    payload: dict,
    db: Optional[AsyncSession]
) -> dict:
    """Execute a webhook command based on its action type."""
    try:
        # Render template with payload data
        message = render_template(command.template, payload)
        
        # Execute action based on type
        if command.action == "create_task":
            return await action_create_task(command.agent, message, payload, db)
        
        elif command.action == "comment":
            return await action_comment(payload, message)
        
        elif command.action == "ask":
            return await action_ask(command.agent, message, payload, db)
        
        elif command.action == "respond":
            return await action_respond(payload, message)
        
        elif command.action == "forward":
            return await action_forward(payload, message)
        
        else:
            logger.error("unknown_action", action=command.action)
            return {"action": "error", "error": f"Unknown action: {command.action}"}
    
    except Exception as e:
        logger.error("execute_command_error", error=str(e), command_id=command.command_id)
        return {"action": "error", "error": str(e)}


async def action_create_task(
    agent: str,
    message: str,
    payload: dict,
    db: AsyncSession
) -> dict:
    """Create a task for an agent."""
    try:
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        
        if payload.get("webhook_source") or payload.get("provider"):
            if "{{task_id}}" in message or "{{task_file}}" in message:
                message = render_template(message, payload, task_id=task_id)
            message = wrap_prompt_with_brain_instructions(message, task_id=task_id)
            agent = "brain"
        
        webhook_session_id = f"webhook-{uuid.uuid4().hex[:12]}"
        session_db = SessionDB(
            session_id=webhook_session_id,
            user_id="webhook-system",
            machine_id="claude-agent-001",
            connected_at=datetime.now(timezone.utc),
        )
        db.add(session_db)
        
        # Map agent name to AgentType
        agent_type_map = {
            "planning": AgentType.PLANNING,
            "executor": AgentType.EXECUTOR,
            "brain": AgentType.PLANNING,
        }
        agent_type = agent_type_map.get(agent, AgentType.PLANNING)
        
        if "webhook_source" not in payload:
            payload["webhook_source"] = payload.get("provider", "unknown")
        
        external_id = generate_external_id(payload.get("webhook_source", "unknown"), payload)
        flow_id = generate_flow_id(external_id)
        
        task_db = TaskDB(
            task_id=task_id,
            session_id=webhook_session_id,
            user_id="webhook-system",
            assigned_agent=agent,
            agent_type=agent_type,
            status=TaskStatus.QUEUED,
            input_message=message,
            source="webhook",
            source_metadata=json.dumps({**payload, "original_agent": agent}),
            flow_id=flow_id,
            initiated_task_id=task_id,  # Root task - self-reference
        )
        db.add(task_db)
        await db.flush()
        
        conversation = await get_or_create_flow_conversation(
            flow_id=flow_id,
            external_id=external_id,
            task_db=task_db,
            db=db
        )
        conversation_id = conversation.conversation_id
        
        source_metadata = json.loads(task_db.source_metadata or "{}")
        source_metadata["flow_id"] = flow_id
        source_metadata["conversation_id"] = conversation_id
        source_metadata["initiated_task_id"] = task_id
        task_db.source_metadata = json.dumps(source_metadata)
        
        try:
            from core.claude_tasks_sync import sync_task_to_claude_tasks
            claude_task_id = sync_task_to_claude_tasks(
                task_db=task_db,
                flow_id=flow_id,
                conversation_id=conversation_id
            )
            if claude_task_id:
                source_metadata["claude_task_id"] = claude_task_id
                task_db.source_metadata = json.dumps(source_metadata)
        except Exception as sync_error:
            logger.warning(
                "claude_tasks_sync_failed",
                task_id=task_id,
                error=str(sync_error)
            )
        
        # Add message to conversation
        from core.database.models import ConversationMessageDB
        user_message_id = f"msg-{uuid.uuid4().hex[:12]}"
        user_message = ConversationMessageDB(
            message_id=user_message_id,
            conversation_id=conversation_id,
            role="user",
            content=message,
            task_id=task_id,
            metadata_json=json.dumps({
                "webhook_source": payload.get("webhook_source", "unknown"),
                "command": payload.get("command", "create_task")
            }),
        )
        db.add(user_message)
        
        logger.info(
            "webhook_task_created_with_flow",
            task_id=task_id,
            flow_id=flow_id,
            conversation_id=conversation_id,
            external_id=external_id
        )
        
        await db.commit()
        
        try:
            await redis_client.push_task(task_id)
        except Exception as redis_error:
            logger.warning(
                "task_queue_push_failed",
                task_id=task_id,
                error=str(redis_error)
            )
        
        logger.info("task_created_from_webhook", task_id=task_id, agent=agent)
        
        return {
            "action": "create_task",
            "task_id": task_id,
            "agent": agent,
            "status": "queued"
        }
    
    except Exception as e:
        logger.error("action_create_task_error", error=str(e))
        raise


async def action_comment(payload: dict, message: str) -> dict:
    """Post a comment back to the source (for dynamic webhooks)."""
    try:
        provider = payload.get("provider", "unknown")
        logger.info("comment_action_for_dynamic_webhook", provider=provider, message=message[:100])
        
        # For dynamic webhooks, comment action is a placeholder
        # Actual implementation would depend on the webhook's API configuration
        return {"action": "comment", "status": "sent", "provider": provider}
    
    except Exception as e:
        logger.error("action_comment_error", error=str(e))
        return {"action": "comment", "status": "error", "error": str(e)}


async def action_ask(
    agent: str,
    message: str,
    payload: dict,
    db: AsyncSession
) -> dict:
    """Ask for clarification (creates interactive task)."""
    try:
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        
        # Create webhook session
        webhook_session_id = f"webhook-{uuid.uuid4().hex[:12]}"
        session_db = SessionDB(
            session_id=webhook_session_id,
            user_id="webhook-system",
            machine_id="claude-agent-001",
            connected_at=datetime.now(timezone.utc),
        )
        db.add(session_db)
        
        # Map agent name to AgentType
        agent_type_map = {
            "planning": AgentType.PLANNING,
            "executor": AgentType.EXECUTOR,
            "brain": AgentType.PLANNING,  # Brain uses PLANNING type
        }
        agent_type = agent_type_map.get(agent, AgentType.PLANNING)
        
        # Create interactive task
        task_db = TaskDB(
            task_id=task_id,
            session_id=webhook_session_id,
            user_id="webhook-system",
            assigned_agent=agent,
            agent_type=agent_type,
            status=TaskStatus.QUEUED,
            input_message=f"[INTERACTIVE] {message}",
            source="webhook",
            source_metadata=json.dumps({**payload, "interactive": True}),
        )
        db.add(task_db)
        await db.commit()
        
        # Push to queue (non-blocking - task already created)
        try:
            await redis_client.push_task(task_id)
        except Exception as redis_error:
            logger.warning(
                "task_queue_push_failed",
                task_id=task_id,
                error=str(redis_error)
            )
        
        logger.info("interactive_task_created", task_id=task_id, agent=agent)
        
        return {
            "action": "ask",
            "task_id": task_id,
            "agent": agent,
            "interactive": True,
            "status": "queued"
        }
    
    except Exception as e:
        logger.error("action_ask_error", error=str(e))
        raise


async def action_respond(payload: dict, message: str) -> dict:
    """Send immediate response to webhook source."""
    try:
        provider = payload.get("provider")
        
        # For now, just log the response
        logger.info("webhook_response", provider=provider, message=message)
        
        return {"action": "respond", "status": "sent", "message": message}
    
    except Exception as e:
        logger.error("action_respond_error", error=str(e))
        return {"action": "respond", "status": "error", "error": str(e)}


async def action_forward(payload: dict, message: str) -> dict:
    """Forward to another webhook/service."""
    try:
        logger.info("webhook_forward", message=message)
        return {"action": "forward", "status": "sent"}
    
    except Exception as e:
        logger.error("action_forward_error", error=str(e))
        return {"action": "forward", "status": "error", "error": str(e)}


