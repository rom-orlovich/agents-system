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
                try:
                    await github_client.add_reaction(
                        owner,
                        repo_name,
                        comment_id,
                        reaction="eyes"
                    )
                    logger.info("github_reaction_sent", comment_id=comment_id)
                    return True
                except Exception as e:
                    logger.warning("github_reaction_failed", comment_id=comment_id, error=str(e))
                    return False
        
        elif event_type.startswith("issues"):
            issue = payload.get("issue", {})
            issue_number = issue.get("number")
            
            if issue_number:
                message = "👀 I'll analyze this issue and get back to you shortly."
                await github_client.post_issue_comment(
                    owner,
                    repo_name,
                    issue_number,
                    message
                )
                logger.info("github_comment_sent", issue_number=issue_number)
                return True
        
        elif event_type.startswith("pull_request"):
            pr = payload.get("pull_request", {})
            pr_number = pr.get("number")
            
            if pr_number:
                message = "👀 I'll review this PR and provide feedback shortly."
                await github_client.post_pr_comment(
                    owner,
                    repo_name,
                    pr_number,
                    message
                )
                logger.info("github_pr_comment_sent", pr_number=pr_number)
                return True
        
        return False
        
    except Exception as e:
        logger.error("github_immediate_response_error", error=str(e))
        return False


def match_github_command(payload: dict, event_type: str) -> Optional[WebhookCommand]:
    """Match GitHub webhook payload to a command."""
    from core.command_matcher import is_bot_comment, extract_command

    sender = payload.get("sender", {})
    if is_bot_comment(sender.get("login", ""), sender.get("type", "")):
        logger.info("github_skipped_bot_comment", sender=sender.get("login"))
        return None

    text = ""
    if event_type.startswith("issue_comment"):
        text = payload.get("comment", {}).get("body", "")
    elif event_type.startswith("pull_request_review_comment"):
        text = payload.get("comment", {}).get("body", "")
    elif event_type.startswith("issues"):
        text = payload.get("issue", {}).get("body", "") or payload.get("issue", {}).get("title", "")
    elif event_type.startswith("pull_request"):
        text = payload.get("pull_request", {}).get("body", "") or payload.get("pull_request", {}).get("title", "")

    result = extract_command(text)

    if result is None:
        logger.debug("github_no_agent_command", event_type=event_type, text_preview=text[:100] if text else "")
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
    db: AsyncSession
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
            "payload": payload
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
