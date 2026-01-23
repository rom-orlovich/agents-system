"""
GitHub Webhook Handler
Complete implementation: route + all supporting functions
Handles all GitHub events: issues, PRs, comments
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import hmac
import hashlib
import os
import json
import uuid
from datetime import datetime
from typing import Optional
import httpx
import structlog

from core.database import get_session as get_db_session
from core.database.models import WebhookEventDB, SessionDB, TaskDB
from core.database.redis_client import redis_client
from core.webhook_configs import GITHUB_WEBHOOK, get_webhook_by_endpoint
from core.webhook_engine import render_template, create_webhook_conversation
from core.github_client import github_client
from shared.machine_models import WebhookCommand
from shared import TaskStatus, AgentType

logger = structlog.get_logger()
router = APIRouter()


# ✅ Verification function (GitHub webhook ONLY)
async def verify_github_signature(request: Request, body: bytes) -> None:
    """Verify GitHub webhook signature ONLY."""
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret:
        logger.warning("GITHUB_WEBHOOK_SECRET not configured, skipping verification")
        return
    
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature header")
    
    # GitHub sends signature as "sha256=hash"
    if signature.startswith("sha256="):
        signature = signature[7:]
    
    # Compute expected signature
    expected_signature = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures (constant-time comparison)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")


# ✅ Immediate response function (GitHub webhook ONLY)
async def send_github_immediate_response(
    payload: dict,
    command: WebhookCommand,
    event_type: str
) -> bool:
    """Send immediate response for GitHub webhook ONLY."""
    try:
        # Extract repository info
        repo = payload.get("repository", {})
        owner = repo.get("owner", {}).get("login", "")
        repo_name = repo.get("name", "")
        
        if not owner or not repo_name:
            logger.warning("github_immediate_response_no_repo", payload=payload)
            return False
        
        # Determine event type and respond accordingly
        if event_type.startswith("issue_comment"):
            # React to comment
            comment = payload.get("comment", {})
            comment_id = comment.get("id")
            issue = payload.get("issue", {})
            issue_number = issue.get("number")
            
            if comment_id and issue_number:
                # Send reaction (eyes emoji)
                reaction_url = f"https://api.github.com/repos/{owner}/{repo_name}/issues/comments/{comment_id}/reactions"
                github_token = os.getenv("GITHUB_TOKEN")
                
                if github_token:
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            reaction_url,
                            headers={
                                "Authorization": f"token {github_token}",
                                "Accept": "application/vnd.github.v3+json"
                            },
                            json={"content": "eyes"},
                            timeout=10.0
                        )
                    logger.info("github_reaction_sent", comment_id=comment_id)
                    return True
        
        elif event_type.startswith("issues"):
            # Comment on issue
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
            # Comment on PR
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


# ✅ Command matching function (GitHub webhook ONLY)
def match_github_command(payload: dict, event_type: str) -> Optional[WebhookCommand]:
    """Match command for GitHub webhook ONLY. Handles all GitHub event types."""
    # Extract text from payload based on event type
    text = ""
    
    if event_type.startswith("issue_comment"):
        text = payload.get("comment", {}).get("body", "")
    elif event_type.startswith("issues"):
        text = payload.get("issue", {}).get("body", "") or payload.get("issue", {}).get("title", "")
    elif event_type.startswith("pull_request"):
        text = payload.get("pull_request", {}).get("body", "") or payload.get("pull_request", {}).get("title", "")
    
    if not text:
        # Use default command
        for cmd in GITHUB_WEBHOOK.commands:
            if cmd.name == GITHUB_WEBHOOK.default_command:
                return cmd
        return GITHUB_WEBHOOK.commands[0] if GITHUB_WEBHOOK.commands else None
    
    # Check prefix
    prefix = GITHUB_WEBHOOK.command_prefix.lower()
    text_lower = text.lower()
    
    if prefix not in text_lower:
        # Use default command
        for cmd in GITHUB_WEBHOOK.commands:
            if cmd.name == GITHUB_WEBHOOK.default_command:
                return cmd
        return GITHUB_WEBHOOK.commands[0] if GITHUB_WEBHOOK.commands else None
    
    # Find command by name or alias
    for cmd in GITHUB_WEBHOOK.commands:
        if cmd.name.lower() in text_lower:
            return cmd
        for alias in cmd.aliases:
            if alias.lower() in text_lower:
                return cmd
    
    # Fallback to default
    for cmd in GITHUB_WEBHOOK.commands:
        if cmd.name == GITHUB_WEBHOOK.default_command:
            return cmd
    
    return GITHUB_WEBHOOK.commands[0] if GITHUB_WEBHOOK.commands else None


# ✅ Task creation function (GitHub webhook ONLY)
async def create_github_task(
    command: WebhookCommand,
    payload: dict,
    db: AsyncSession
) -> str:
    """Create task for GitHub webhook ONLY. Handles all GitHub event types."""
    # Render template
    message = render_template(command.prompt_template, payload)
    
    # Create webhook session if needed
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
    agent_type = agent_type_map.get(command.target_agent, AgentType.PLANNING)
    
    # Create task
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    task_db = TaskDB(
        task_id=task_id,
        session_id=webhook_session_id,
        user_id="webhook-system",
        assigned_agent=command.target_agent,
        agent_type=agent_type,
        status=TaskStatus.QUEUED,
        input_message=message,
        source="webhook",
        source_metadata=json.dumps({
            "webhook_source": "github",
            "webhook_name": GITHUB_WEBHOOK.name,
            "command": command.name,
            "payload": payload
        }),
    )
    db.add(task_db)
    await db.flush()  # Flush to get task_db.id if needed
    
    # Create conversation immediately when task is created
    conversation_id = await create_webhook_conversation(task_db, db)
    if conversation_id:
        logger.info("github_conversation_created", conversation_id=conversation_id, task_id=task_id)
    
    await db.commit()
    
    # Push to queue
    await redis_client.push_task(task_id)
    
    logger.info("github_task_created", task_id=task_id, command=command.name)
    
    return task_id


# ✅ Route handler (GitHub webhook - handles all GitHub events)
@router.post("/github")
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Dedicated handler for GitHub webhook.
    Handles all GitHub events: issues, PRs, comments.
    All logic and functions in this file.
    """
    try:
        # 1. Read body
        body = await request.body()
        
        # 2. Verify signature
        await verify_github_signature(request, body)
        
        # 3. Parse payload
        payload = json.loads(body.decode())
        payload["provider"] = "github"
        
        # 4. Extract event type (issues.opened, pull_request.opened, issue_comment.created, etc.)
        event_type = request.headers.get("X-GitHub-Event", "unknown")
        action = payload.get("action", "")
        if action:
            event_type = f"{event_type}.{action}"
        
        logger.info("github_webhook_received", event_type=event_type)
        
        # 5. Match command based on event type and payload
        command = match_github_command(payload, event_type)
        if not command:
            return {"status": "received", "actions": 0, "message": "No command matched"}
        
        # 6. Send immediate response
        immediate_response_sent = await send_github_immediate_response(payload, command, event_type)
        
        # 7. Create task
        task_id = await create_github_task(command, payload, db)
        
        # 8. Log event
        event_id = f"evt-{uuid.uuid4().hex[:12]}"
        event_db = WebhookEventDB(
            event_id=event_id,
            webhook_id=GITHUB_WEBHOOK.name,
            provider="github",
            event_type=event_type,
            payload_json=json.dumps(payload),
            matched_command=command.name,
            task_id=task_id,
            response_sent=immediate_response_sent,
            created_at=datetime.utcnow()
        )
        db.add(event_db)
        await db.commit()
        
        logger.info("github_webhook_processed", task_id=task_id, command=command.name, event_type=event_type)
        
        return {
            "status": "processed",
            "task_id": task_id,
            "command": command.name,
            "immediate_response_sent": immediate_response_sent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("github_webhook_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
