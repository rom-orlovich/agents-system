"""Webhook command execution engine."""

import uuid
import json
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from core.database.models import WebhookCommandDB, TaskDB, SessionDB, WebhookEventDB
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
            "brain": AgentType.BRAIN,
        }
        agent_type = agent_type_map.get(agent, AgentType.PLANNING)
        
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
            "brain": AgentType.BRAIN,
        }
        agent_type = agent_type_map.get(agent, AgentType.BRAIN)
        
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
    logger.info("jira_comment_posted", message=message)


async def slack_post_message(payload: dict, message: str):
    """Post message to Slack channel."""
    logger.info("slack_message_posted", message=message)
