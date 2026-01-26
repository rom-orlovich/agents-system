"""
GitHub webhook utility functions.
Signature verification, command matching, task creation, and immediate responses.
"""

import hmac
import hashlib
import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional
import structlog
import httpx

from fastapi import Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database.models import SessionDB, TaskDB
from core.database.redis_client import redis_client
from core.webhook_configs import GITHUB_WEBHOOK
from core.webhook_engine import render_template, create_webhook_conversation
from core.github_client import github_client
from core.routing_metadata import extract_github_metadata
from shared.machine_models import WebhookCommand
from shared import TaskStatus, AgentType

logger = structlog.get_logger()


async def verify_github_signature(request: Request, body: bytes) -> None:
    """Verify GitHub webhook signature."""
    signature = request.headers.get("X-Hub-Signature-256", "")
    secret = os.getenv("GITHUB_WEBHOOK_SECRET") or settings.github_webhook_secret
    
    if signature:
        if not secret:
            raise HTTPException(status_code=401, detail="Webhook secret not configured but signature provided")
        
        if signature.startswith("sha256="):
            signature = signature[7:]
        
        expected_signature = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
    elif secret:
        logger.warning("GITHUB_WEBHOOK_SECRET configured but no signature header provided")


async def send_github_immediate_response(
    payload: dict,
    command: WebhookCommand,
    event_type: str
) -> bool:
    """Send immediate response to GitHub (reaction or comment)."""
    try:
        repo = payload.get("repository", {})
        owner = repo.get("owner", {}).get("login", "")
        repo_name = repo.get("name", "")
        
        if not owner or not repo_name:
            logger.warning("github_immediate_response_no_repo", payload=payload)
            return False
        
        if event_type.startswith("issue_comment"):
            comment = payload.get("comment", {})
            comment_id = comment.get("id")
            
            if comment_id:
                import os
                github_client.token = github_client.token or os.getenv("GITHUB_TOKEN")
                if github_client.token:
                    github_client.headers["Authorization"] = f"token {github_client.token}"
                
                if not github_client.token:
                    logger.warning(
                        "github_reaction_skipped_no_token",
                        comment_id=comment_id,
                        event_type=event_type,
                        message="GITHUB_TOKEN not configured - reaction not sent. Set GITHUB_TOKEN environment variable."
                    )
                    return False
                
                try:
                    reaction_response = await github_client.add_reaction(
                        owner,
                        repo_name,
                        comment_id,
                        reaction="eyes"
                    )
                    logger.info(
                        "github_reaction_sent",
                        comment_id=comment_id,
                        event_type=event_type,
                        reaction_id=reaction_response.get("id") if reaction_response else None,
                        reaction_content=reaction_response.get("content") if reaction_response else None
                    )
                    return True
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 401:
                        logger.error(
                            "github_reaction_auth_failed",
                            comment_id=comment_id,
                            status_code=401,
                            event_type=event_type,
                            message="GitHub authentication failed. Ensure GITHUB_TOKEN is valid and has required scopes: 'repo' (for classic tokens) or 'Metadata: read' (for fine-grained tokens). Reactions require repository access."
                        )
                    else:
                        logger.warning(
                            "github_reaction_failed",
                            comment_id=comment_id,
                            status_code=e.response.status_code,
                            error=str(e),
                            event_type=event_type
                        )
                    return False
                except ValueError as e:
                    logger.warning(
                        "github_reaction_skipped_no_token",
                        comment_id=comment_id,
                        error=str(e),
                        event_type=event_type,
                        message="GITHUB_TOKEN not configured - reaction not sent"
                    )
                    return False
                except Exception as e:
                    logger.warning(
                        "github_reaction_failed",
                        comment_id=comment_id,
                        error=str(e),
                        event_type=event_type
                    )
                    return False
        
        elif event_type.startswith("issues"):
            issue = payload.get("issue", {})
            issue_number = issue.get("number")
            
            if issue_number:
                import os
                github_client.token = github_client.token or os.getenv("GITHUB_TOKEN")
                if github_client.token:
                    github_client.headers["Authorization"] = f"token {github_client.token}"
                
                if not github_client.token:
                    logger.warning(
                        "github_comment_skipped_no_token",
                        issue_number=issue_number,
                        event_type=event_type,
                        message="GITHUB_TOKEN not configured - comment not sent"
                    )
                    return False
                
                try:
                    message = "👀 I'll analyze this issue and get back to you shortly."
                    await github_client.post_issue_comment(
                        owner,
                        repo_name,
                        issue_number,
                        message
                    )
                    logger.info("github_comment_sent", issue_number=issue_number)
                    return True
                except Exception as e:
                    logger.warning(
                        "github_comment_failed",
                        issue_number=issue_number,
                        error=str(e),
                        event_type=event_type
                    )
                    return False
        
        elif event_type.startswith("pull_request"):
            pr = payload.get("pull_request", {})
            pr_number = pr.get("number")
            
            if pr_number:
                import os
                github_client.token = github_client.token or os.getenv("GITHUB_TOKEN")
                if github_client.token:
                    github_client.headers["Authorization"] = f"token {github_client.token}"
                
                if not github_client.token:
                    logger.warning(
                        "github_pr_comment_skipped_no_token",
                        pr_number=pr_number,
                        event_type=event_type,
                        message="GITHUB_TOKEN not configured - comment not sent"
                    )
                    return False
                
                try:
                    message = "👀 I'll review this PR and provide feedback shortly."
                    await github_client.post_pr_comment(
                        owner,
                        repo_name,
                        pr_number,
                        message
                    )
                    logger.info("github_pr_comment_sent", pr_number=pr_number)
                    return True
                except Exception as e:
                    logger.warning(
                        "github_pr_comment_failed",
                        pr_number=pr_number,
                        error=str(e),
                        event_type=event_type
                    )
                    return False
        
        return False
        
    except Exception as e:
        logger.error("github_immediate_response_error", error=str(e))
        return False


def match_github_command(payload: dict, event_type: str) -> Optional[WebhookCommand]:
    """Match GitHub webhook payload to a command."""
    from core.command_matcher import is_bot_comment, extract_command

    sender = payload.get("sender", {})
    sender_login = sender.get("login", "")
    sender_type = sender.get("type", "")
    
    if is_bot_comment(sender_login, sender_type):
        logger.info(
            "github_skipped_bot_comment",
            sender=sender_login,
            sender_type=sender_type,
            event_type=event_type
        )
        return None

    text = ""
    if event_type.startswith("issue_comment"):
        text = payload.get("comment", {}).get("body", "")
        logger.debug(
            "github_comment_text_extracted",
            event_type=event_type,
            action=payload.get("action"),
            text_preview=text[:100] if text else "",
            comment_id=payload.get("comment", {}).get("id")
        )
    elif event_type.startswith("pull_request_review_comment"):
        text = payload.get("comment", {}).get("body", "")
    elif event_type.startswith("issues"):
        text = payload.get("issue", {}).get("body", "") or payload.get("issue", {}).get("title", "")
    elif event_type.startswith("pull_request"):
        text = payload.get("pull_request", {}).get("body", "") or payload.get("pull_request", {}).get("title", "")

    result = extract_command(text)

    if result is None:
        logger.debug(
            "github_no_agent_command",
            event_type=event_type,
            action=payload.get("action"),
            text_preview=text[:100] if text else "",
            sender=sender_login
        )
        return None

    command_name, user_content = result
    for cmd in GITHUB_WEBHOOK.commands:
        if cmd.name.lower() == command_name:
            payload["_user_content"] = user_content
            return cmd
        for alias in cmd.aliases:
            if alias.lower() == command_name:
                payload["_user_content"] = user_content
                return cmd

    logger.warning("github_command_not_configured", command=command_name)
    return None


async def create_github_task(
    command: WebhookCommand,
    payload: dict,
    db: AsyncSession,
    completion_handler: str
) -> str:
    """Create a task from GitHub webhook."""
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    
    base_message = render_template(command.prompt_template, payload, task_id=task_id)
    
    from core.webhook_engine import wrap_prompt_with_brain_instructions
    message = wrap_prompt_with_brain_instructions(base_message, task_id=task_id)
    
    webhook_session_id = f"webhook-{uuid.uuid4().hex[:12]}"
    session_db = SessionDB(
        session_id=webhook_session_id,
        user_id="webhook-system",
        machine_id="claude-agent-001",
        connected_at=datetime.now(timezone.utc),
    )
    db.add(session_db)
    
    agent_type_map = {
        "planning": AgentType.PLANNING,
        "executor": AgentType.EXECUTOR,
        "brain": AgentType.PLANNING,
    }
    agent_type = agent_type_map.get("brain", AgentType.PLANNING)
    
    routing = extract_github_metadata(payload)

    task_db = TaskDB(
        task_id=task_id,
        session_id=webhook_session_id,
        user_id="webhook-system",
        assigned_agent="brain",
        agent_type=agent_type,
        status=TaskStatus.QUEUED,
        input_message=message,
        source="webhook",
        source_metadata=json.dumps({
            "webhook_source": "github",
            "webhook_name": GITHUB_WEBHOOK.name,
            "command": command.name,
            "original_target_agent": command.target_agent,
            "routing": routing,
            "payload": payload,
            "completion_handler": completion_handler
        }),
    )
    db.add(task_db)
    await db.flush()
    
    from core.webhook_engine import generate_external_id, generate_flow_id
    external_id = generate_external_id("github", payload)
    flow_id = generate_flow_id(external_id)
    
    source_metadata = json.loads(task_db.source_metadata or "{}")
    source_metadata["flow_id"] = flow_id
    source_metadata["external_id"] = external_id
    task_db.source_metadata = json.dumps(source_metadata)
    task_db.flow_id = flow_id
    
    conversation_id = await create_webhook_conversation(task_db, db)
    if conversation_id:
        logger.info("github_conversation_created", conversation_id=conversation_id, task_id=task_id)
    
    try:
        from core.claude_tasks_sync import sync_task_to_claude_tasks
        claude_task_id = sync_task_to_claude_tasks(
            task_db=task_db,
            flow_id=flow_id,
            conversation_id=conversation_id
        )
        if claude_task_id:
            source_metadata = json.loads(task_db.source_metadata or "{}")
            source_metadata["claude_task_id"] = claude_task_id
            task_db.source_metadata = json.dumps(source_metadata)
    except Exception as sync_error:
        logger.warning(
            "github_claude_tasks_sync_failed",
            task_id=task_id,
            error=str(sync_error)
        )
    
    await db.commit()
    
    await redis_client.push_task(task_id)
    
    logger.info("github_task_created", task_id=task_id, command=command.name)
    
    return task_id


async def post_github_task_comment(
    payload: dict,
    message: str,
    success: bool,
    cost_usd: float = 0.0
) -> bool:
    """Post a comment to GitHub after task completion."""
    try:
        repo = payload.get("repository", {})
        owner = repo.get("owner", {}).get("login", "")
        repo_name = repo.get("name", "")
        
        if not owner or not repo_name:
            logger.debug("github_post_comment_no_repo", payload_keys=list(payload.keys()))
            return False
        
        if success:
            formatted_message = f"✅ {message}"
        else:
            formatted_message = f"❌ {message}"
        
        max_length = 8000 if not success else 4000
        if len(formatted_message) > max_length:
            truncated_message = formatted_message[:max_length]
            last_period = truncated_message.rfind(".")
            last_newline = truncated_message.rfind("\n")
            truncate_at = max(last_period, last_newline)
            if truncate_at > max_length * 0.8:
                truncated_message = truncated_message[:truncate_at + 1]
            formatted_message = truncated_message + "\n\n... (message truncated)"
        
        if success and cost_usd > 0:
            formatted_message += f"\n\n💰 Cost: ${cost_usd:.4f}"
        
        pr = payload.get("pull_request", {})
        issue = payload.get("issue", {})
        
        if pr and pr.get("number"):
            pr_number = pr.get("number")
            await github_client.post_pr_comment(owner, repo_name, pr_number, formatted_message)
            logger.info("github_pr_comment_posted", pr_number=pr_number)
            return True
        elif issue and issue.get("number"):
            if issue.get("pull_request"):
                pr_number = issue.get("number")
                await github_client.post_pr_comment(owner, repo_name, pr_number, formatted_message)
                logger.info("github_pr_comment_posted_from_issue", pr_number=pr_number)
                return True
            else:
                issue_number = issue.get("number")
                await github_client.post_issue_comment(owner, repo_name, issue_number, formatted_message)
                logger.info("github_issue_comment_posted", issue_number=issue_number)
                return True
        else:
            logger.warning("github_no_issue_or_pr_found", payload_keys=list(payload.keys()))
            return False
        
    except ValueError as e:
        logger.warning(
            "github_post_task_comment_skipped_no_token",
            error=str(e),
            message="GITHUB_TOKEN not configured - comment not posted"
        )
        return False
    except Exception as e:
        logger.error("github_post_task_comment_error", error=str(e))
        return False


async def send_slack_notification(
    task_id: str,
    webhook_source: str,
    command: str,
    success: bool,
    result: Optional[str] = None,
    error: Optional[str] = None
) -> bool:
    """Send Slack notification when webhook task completes."""
    if not os.getenv("SLACK_NOTIFICATIONS_ENABLED", "true").lower() == "true":
        return False
    
    from core.slack_client import slack_client
    
    status_emoji = "✅" if success else "❌"
    status_text = "Completed" if success else "Failed"
    
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{status_emoji} *Task {status_text}*\n*Source:* {webhook_source.title()}\n*Command:* {command}\n*Task ID:* `{task_id}`"
            }
        }
    ]
    
    if success and result:
        result_preview = result[:500] + "..." if len(result) > 500 else result
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Result:*\n```{result_preview}```"
            }
        })
    
    if error:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Error:*\n```{error}```"
            }
        })
    
    if success:
        channel = os.getenv("SLACK_CHANNEL_AGENTS", "#ai-agent-activity")
    else:
        channel = os.getenv("SLACK_CHANNEL_ERRORS", "#ai-agent-errors")
    text = f"{status_emoji} Task {status_text} - {webhook_source.title()} - {command}"
    
    try:
        await slack_client.post_message(
            channel=channel,
            text=text,
            blocks=blocks
        )
        logger.info("slack_notification_sent", task_id=task_id, success=success, channel=channel)
        return True
    except Exception as e:
        error_msg = str(e)
        if "channel_not_found" in error_msg.lower():
            env_var = "SLACK_CHANNEL_AGENTS" if success else "SLACK_CHANNEL_ERRORS"
            logger.warning(
                "slack_notification_channel_not_found",
                task_id=task_id,
                channel=channel,
                message=f"Slack notification skipped - channel does not exist. Set {env_var} to a valid channel or create the channel."
            )
        else:
            logger.error("slack_notification_failed", task_id=task_id, channel=channel, error=error_msg)
        return False
