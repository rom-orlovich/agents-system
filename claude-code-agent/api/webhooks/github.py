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
from datetime import datetime, timezone
from typing import Optional
import httpx
import structlog
import subprocess
from pathlib import Path

from core.config import settings
from core.database import get_session as get_db_session
from core.database.models import WebhookEventDB, SessionDB, TaskDB
from core.database.redis_client import redis_client
from core.webhook_configs import GITHUB_WEBHOOK, get_webhook_by_endpoint
from core.webhook_engine import render_template, create_webhook_conversation
from core.github_client import github_client
from core.routing_metadata import extract_github_metadata
from shared.machine_models import WebhookCommand
from shared import TaskStatus, AgentType

logger = structlog.get_logger()
router = APIRouter()


async def verify_github_signature(request: Request, body: bytes) -> None:
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
            issue = payload.get("issue", {})
            issue_number = issue.get("number")
            
            if comment_id and issue_number:
                reaction_url = f"https://api.github.com/repos/{owner}/{repo_name}/issues/comments/{comment_id}/reactions"
                github_token = os.getenv("GITHUB_TOKEN") or settings.github_token
                
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
    from core.command_matcher import is_bot_comment, extract_command

    sender = payload.get("sender", {})
    if is_bot_comment(sender.get("login", ""), sender.get("type", "")):
        logger.info("github_skipped_bot_comment", sender=sender.get("login"))
        return None

    is_comment_event = (
        event_type.startswith("issue_comment") or
        event_type.startswith("pull_request_review_comment")
    )

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
            # Store user content in payload for template rendering
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
    
    # Extract clean routing metadata for response posting
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
            "routing": routing,  # Clean routing info for response posting
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
    
    # Push to queue
    await redis_client.push_task(task_id)
    
    logger.info("github_task_created", task_id=task_id, command=command.name)
    
    return task_id


@router.post("/github")
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    repo_info = None
    issue_number = None
    task_id = None
    
    try:
        try:
            body = await request.body()
        except Exception as e:
            logger.error("github_webhook_body_read_failed", error=str(e))
            raise HTTPException(status_code=400, detail=f"Failed to read request body: {str(e)}")
        
        try:
            await verify_github_signature(request, body)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("github_signature_verification_error", error=str(e))
            raise HTTPException(status_code=401, detail=f"Signature verification failed: {str(e)}")
        
        try:
            payload = json.loads(body.decode())
            payload["provider"] = "github"
        except json.JSONDecodeError as e:
            logger.error("github_payload_parse_error", error=str(e))
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")
        except Exception as e:
            logger.error("github_payload_decode_error", error=str(e))
            raise HTTPException(status_code=400, detail=f"Failed to decode payload: {str(e)}")
        
        repo = payload.get("repository", {})
        repo_info = f"{repo.get('owner', {}).get('login', 'unknown')}/{repo.get('name', 'unknown')}"
        issue = payload.get("issue") or payload.get("pull_request")
        if issue:
            issue_number = issue.get("number")
        
        event_type = request.headers.get("X-GitHub-Event", "unknown")
        action = payload.get("action", "")
        if action:
            event_type = f"{event_type}.{action}"
        
        logger.info("github_webhook_received", event_type=event_type, repo=repo_info, issue_number=issue_number)
        
        # 5. Validate webhook input BEFORE processing (enforces strict activation rules)
        try:
            # Get project root directory
            project_root = Path(__file__).parent.parent.parent
            script_path = project_root / "scripts" / "validate-webhook-input.sh"
            
            if script_path.exists():
                validation_result = subprocess.run(
                    [str(script_path)],
                    input=json.dumps(payload),
                    text=True,
                    capture_output=True,
                    timeout=5,
                    cwd=str(project_root)
                )
            else:
                logger.warning("validation_script_not_found", script_path=str(script_path))
                validation_result = None
            
            if validation_result and validation_result.returncode != 0:
                logger.info(
                    "github_webhook_rejected_by_validation",
                    event_type=event_type,
                    repo=repo_info,
                    issue_number=issue_number,
                    reason=validation_result.stderr.strip()
                )
                return {"status": "rejected", "actions": 0, "message": "Does not meet activation rules"}
        except Exception as e:
            logger.error("github_webhook_validation_error", error=str(e), event_type=event_type)
        
        try:
            command = match_github_command(payload, event_type)
            if not command:
                logger.warning("github_no_command_matched", event_type=event_type, repo=repo_info, issue_number=issue_number)
                return {"status": "received", "actions": 0, "message": "No command matched"}
        except Exception as e:
            logger.error("github_command_matching_error", error=str(e), repo=repo_info, issue_number=issue_number)
            raise HTTPException(status_code=500, detail=f"Command matching failed: {str(e)}")
        
        immediate_response_sent = False
        try:
            immediate_response_sent = await send_github_immediate_response(payload, command, event_type)
        except Exception as e:
            logger.error("github_immediate_response_error", error=str(e), repo=repo_info, issue_number=issue_number, command=command.name)
        
        try:
            task_id = await create_github_task(command, payload, db)
            logger.info("github_task_created_success", task_id=task_id, repo=repo_info, issue_number=issue_number)
        except Exception as e:
            logger.error("github_task_creation_failed", error=str(e), error_type=type(e).__name__, repo=repo_info, issue_number=issue_number, command=command.name)
            raise HTTPException(status_code=500, detail=f"Task creation failed: {str(e)}")
        
        try:
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
                created_at=datetime.now(timezone.utc)
            )
            db.add(event_db)
            await db.commit()
            logger.info("github_event_logged", event_id=event_id, task_id=task_id, repo=repo_info, issue_number=issue_number)
        except Exception as e:
            logger.error("github_event_logging_failed", error=str(e), task_id=task_id, repo=repo_info, issue_number=issue_number)
            # Don't fail the whole request if event logging fails
        
        logger.info("github_webhook_processed", task_id=task_id, command=command.name, event_type=event_type, repo=repo_info, issue_number=issue_number)
        
        return {
            "status": "processed",
            "task_id": task_id,
            "command": command.name,
            "immediate_response_sent": immediate_response_sent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "github_webhook_error",
            error=str(e),
            error_type=type(e).__name__,
            repo=repo_info,
            issue_number=issue_number,
            task_id=task_id,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))
