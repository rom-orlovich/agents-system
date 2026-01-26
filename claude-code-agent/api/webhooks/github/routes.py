"""
GitHub Webhook Routes
Main route handler for GitHub webhooks.
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import json
import uuid
from datetime import datetime, timezone
import structlog

from core.database import get_session as get_db_session
from core.database.models import WebhookEventDB
from core.webhook_configs import GITHUB_WEBHOOK
from api.webhooks.github.validation import validate_github_webhook
from api.webhooks.github.utils import (
    verify_github_signature,
    send_github_immediate_response,
    match_github_command,
    create_github_task,
)

logger = structlog.get_logger()
router = APIRouter()


@router.post("/github")
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """GitHub webhook endpoint."""
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
        
        try:
            validation_result = validate_github_webhook(payload)
            
            if not validation_result.is_valid:
                logger.info(
                    "github_webhook_rejected_by_validation",
                    event_type=event_type,
                    repo=repo_info,
                    issue_number=issue_number,
                    reason=validation_result.error_message
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
