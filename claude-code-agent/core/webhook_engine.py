"""Webhook command execution engine."""

import uuid
import json
import re
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import httpx
import hashlib

from core.database.models import WebhookCommandDB, TaskDB, SessionDB, WebhookEventDB, ConversationDB, ConversationMessageDB
from core.database.redis_client import redis_client
from core.github_client import github_client
from shared import TaskStatus, AgentType

logger = structlog.get_logger()


def extract_repo_info(payload: dict) -> tuple[str, str]:
    """Extract repository owner and name from GitHub payload."""
    repo = payload.get("repository", {})
    full_name = repo.get("full_name", "")
    if "/" in full_name:
        owner, name = full_name.split("/", 1)
        return owner, name
    return "", ""


def generate_external_id(webhook_source: str, payload: dict) -> Optional[str]:
    """Generate a stable external ID from webhook payload (Jira ticket key, PR number, etc.)."""
    if webhook_source == "jira":
        issue = payload.get("issue", {})
        issue_key = issue.get("key")
        if issue_key:
            return f"jira:{issue_key}"
    
    elif webhook_source == "github":
        issue = payload.get("issue", {})
        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {}).get("full_name", "")
        if pr:
            pr_number = pr.get("number")
            if pr_number and repo:
                return f"github:pr:{repo}#{pr_number}"
        elif issue:
            issue_number = issue.get("number")
            if issue_number and repo:
                return f"github:issue:{repo}#{issue_number}"
    
    elif webhook_source == "slack":
        event = payload.get("event", {})
        channel = event.get("channel")
        thread_ts = event.get("thread_ts") or event.get("ts")
        if channel and thread_ts:
            return f"slack:{channel}:{thread_ts}"
        elif channel:
            return f"slack:{channel}"
    
    elif webhook_source == "sentry":
        event = payload.get("event", {})
        event_id = event.get("event_id")
        if event_id:
            return f"sentry:{event_id}"
    
    return None


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
    """Generate conversation title based on webhook source and payload."""
    if webhook_source == "jira":
        issue = payload.get("issue", {})
        issue_key = issue.get("key", "Unknown")
        fields = issue.get("fields", {})
        issue_summary = fields.get("summary", "")
        if issue_key != "Unknown":
            title = f"Jira: {issue_key} - {command}"
            if issue_summary:
                title += f" ({issue_summary[:40]})"
            return title
        return f"Jira Webhook - {command}"
    
    elif webhook_source == "github":
        issue = payload.get("issue", {})
        pr = payload.get("pull_request", {})
        if issue:
            issue_number = issue.get("number", "")
            issue_title = issue.get("title", "")
            repo = payload.get("repository", {}).get("full_name", "")
            if issue_number:
                title = f"GitHub: {repo}#{issue_number} - {command}"
                if issue_title:
                    title += f" ({issue_title[:40]})"
                return title
        elif pr:
            pr_number = pr.get("number", "")
            pr_title = pr.get("title", "")
            repo = payload.get("repository", {}).get("full_name", "")
            if pr_number:
                title = f"GitHub PR: {repo}#{pr_number} - {command}"
                if pr_title:
                    title += f" ({pr_title[:40]})"
                return title
        return f"GitHub Webhook - {command}"
    
    elif webhook_source == "slack":
        event = payload.get("event", {})
        channel = event.get("channel", "unknown")
        return f"Slack: #{channel} - {command}"
    
    elif webhook_source == "sentry":
        event = payload.get("event", {})
        title_text = event.get("title", "")
        if title_text:
            return f"Sentry: {title_text[:40]} - {command}"
        return f"Sentry Webhook - {command}"
    
    else:
        # Generic or dynamic webhook
        webhook_name = payload.get("webhook_name", webhook_source)
        return f"{webhook_name.title()} Webhook - {command}"


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


def render_template(template: str, payload: dict) -> str:
    """
    Render template with payload data using {{variable}} syntax.
    Supports nested access like {{user.profile.name}} and array access {{labels.0.name}}.
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
    
    # Find all {{variable}} patterns
    pattern = r'\{\{([^}]+)\}\}'
    
    def replace_var(match):
        var_path = match.group(1).strip()
        value = get_nested_value(payload, var_path)
        
        if value is None:
            return match.group(0)  # Keep original if not found
        
        return str(value)
    
    return re.sub(pattern, replace_var, template)


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
        
        # GitHub-specific actions
        elif command.action == "github_reaction":
            # Extract reaction from template or use default
            reaction = message.strip() if message.strip() in ["eyes", "+1", "-1", "laugh", "confused", "heart", "hooray", "rocket"] else "eyes"
            return await action_github_reaction(payload, reaction)
        
        elif command.action == "github_label":
            # Parse labels from template (comma-separated)
            labels = [label.strip() for label in message.split(",") if label.strip()]
            return await action_github_label(payload, labels)
        
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
        
        # Create webhook session
        webhook_session_id = f"webhook-{uuid.uuid4().hex[:12]}"
        session_db = SessionDB(
            session_id=webhook_session_id,
            user_id="webhook-system",
            machine_id="claude-agent-001",
            connected_at=datetime.utcnow(),
        )
        db.add(session_db)
        
        # Map agent name to AgentType
        agent_type_map = {
            "planning": AgentType.PLANNING,
            "executor": AgentType.EXECUTOR,
            "brain": AgentType.PLANNING,  # Brain uses PLANNING type
        }
        agent_type = agent_type_map.get(agent, AgentType.PLANNING)
        
        # Ensure payload has webhook_source for conversation creation
        if "webhook_source" not in payload:
            payload["webhook_source"] = payload.get("provider", "unknown")
        
        # Create task
        task_db = TaskDB(
            task_id=task_id,
            session_id=webhook_session_id,
            user_id="webhook-system",
            assigned_agent=agent,
            agent_type=agent_type,
            status=TaskStatus.QUEUED,
            input_message=message,
            source="webhook",
            source_metadata=json.dumps(payload),
        )
        db.add(task_db)
        await db.flush()  # Flush to get task_db.id if needed
        
        # Create conversation immediately when task is created
        conversation_id = await create_webhook_conversation(task_db, db)
        if conversation_id:
            logger.info("webhook_conversation_created_in_action", conversation_id=conversation_id, task_id=task_id)
        
        await db.commit()
        
        # Push to queue
        await redis_client.push_task(task_id)
        
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
    """Post a comment back to the source."""
    try:
        provider = payload.get("provider")
        
        if provider == "github":
            # Extract repo info and issue/PR number
            repo_owner, repo_name = extract_repo_info(payload)
            
            # Get issue or PR number
            issue_number = None
            if "issue" in payload:
                issue_number = payload["issue"].get("number")
            elif "pull_request" in payload:
                issue_number = payload["pull_request"].get("number")
            
            if repo_owner and repo_name and issue_number:
                await github_client.post_issue_comment(
                    repo_owner,
                    repo_name,
                    issue_number,
                    message
                )
                logger.info("github_comment_posted_via_engine", issue=issue_number)
            else:
                logger.warning("missing_github_info_for_comment", payload_keys=list(payload.keys()))
                
        elif provider == "jira":
            await jira_post_comment(payload, message)
        elif provider == "slack":
            await slack_post_message(payload, message)
        else:
            logger.warning("unsupported_comment_provider", provider=provider)
        
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
            connected_at=datetime.utcnow(),
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
        
        # Push to queue
        await redis_client.push_task(task_id)
        
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


async def action_github_reaction(payload: dict, reaction: str = "eyes") -> dict:
    """Add reaction to GitHub comment/issue/PR."""
    try:
        repo_owner, repo_name = extract_repo_info(payload)
        
        # Get comment ID if available
        comment_id = None
        if "comment" in payload:
            comment_id = payload["comment"].get("id")
        
        if repo_owner and repo_name and comment_id:
            await github_client.add_reaction(
                repo_owner,
                repo_name,
                comment_id,
                reaction
            )
            logger.info("github_reaction_added_via_engine", reaction=reaction)
            return {"action": "github_reaction", "status": "sent", "reaction": reaction}
        else:
            logger.warning("missing_github_info_for_reaction")
            return {"action": "github_reaction", "status": "skipped", "reason": "missing_info"}
    
    except Exception as e:
        logger.error("action_github_reaction_error", error=str(e))
        return {"action": "github_reaction", "status": "error", "error": str(e)}


async def action_github_label(payload: dict, labels: list[str]) -> dict:
    """Add labels to GitHub issue/PR."""
    try:
        repo_owner, repo_name = extract_repo_info(payload)
        
        # Get issue or PR number
        issue_number = None
        if "issue" in payload:
            issue_number = payload["issue"].get("number")
        elif "pull_request" in payload:
            issue_number = payload["pull_request"].get("number")
        
        if repo_owner and repo_name and issue_number:
            await github_client.update_issue_labels(
                repo_owner,
                repo_name,
                issue_number,
                labels
            )
            logger.info("github_labels_added_via_engine", labels=labels)
            return {"action": "github_label", "status": "sent", "labels": labels}
        else:
            logger.warning("missing_github_info_for_labels")
            return {"action": "github_label", "status": "skipped", "reason": "missing_info"}
    
    except Exception as e:
        logger.error("action_github_label_error", error=str(e))
        return {"action": "github_label", "status": "error", "error": str(e)}


async def github_post_comment(payload: dict, message: str):
    """Post comment to GitHub issue/PR (legacy)."""
    logger.info("github_comment_posted", message=message)


async def jira_post_comment(payload: dict, message: str):
    """Post comment to Jira issue."""
    try:
        from core.config import settings
        import base64
        
        # Get Jira credentials
        jira_url = settings.jira_url or os.getenv("JIRA_URL")
        jira_email = settings.jira_email or os.getenv("JIRA_EMAIL")
        jira_api_token = settings.jira_api_token or os.getenv("JIRA_API_TOKEN")
        
        if not jira_url or not jira_api_token or not jira_email:
            logger.warning("jira_credentials_missing", message="Jira API credentials not configured")
            return
        
        # Extract issue key from payload
        issue = payload.get("issue", {})
        issue_key = issue.get("key")
        
        if not issue_key:
            logger.warning("jira_issue_key_missing", payload_keys=list(payload.keys()))
            return
        
        # Build API URL
        api_url = f"{jira_url.rstrip('/')}/rest/api/3/issue/{issue_key}/comment"
        
        # Create auth header (Basic auth with email:token)
        auth_string = f"{jira_email}:{jira_api_token}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        # Post comment
        async with httpx.AsyncClient() as client:
            response = await client.post(
                api_url,
                headers={
                    "Authorization": f"Basic {auth_b64}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json={
                    "body": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": message
                                    }
                                ]
                            }
                        ]
                    }
                },
                timeout=30.0
            )
            response.raise_for_status()
            
            logger.info(
                "jira_comment_posted",
                issue_key=issue_key,
                comment_id=response.json().get("id")
            )
            
    except httpx.HTTPStatusError as e:
        logger.error(
            "jira_comment_failed",
            status_code=e.response.status_code,
            error=str(e),
            response_text=e.response.text[:500] if e.response.text else None
        )
    except Exception as e:
        logger.error("jira_api_error", error=str(e), error_type=type(e).__name__)


async def slack_post_message(payload: dict, message: str):
    """Post message to Slack channel using Slack API."""
    try:
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        if not slack_token:
            logger.warning("slack_bot_token_not_configured_for_comment")
            return
        
        # Extract channel from payload
        channel = None
        event = payload.get("event", {})
        if event:
            channel = event.get("channel")
        
        # Fallback to notification channel if not in event
        if not channel:
            channel = os.getenv("SLACK_NOTIFICATION_CHANNEL", "#ai-agent-activity")
        
        # Send message using Slack API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {slack_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "channel": channel,
                    "text": message
                },
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            if not result.get("ok"):
                logger.error("slack_api_error", error=result.get("error"))
            else:
                logger.info("slack_message_posted", channel=channel, message=message[:100])
    except Exception as e:
        logger.error("slack_post_message_error", error=str(e))
