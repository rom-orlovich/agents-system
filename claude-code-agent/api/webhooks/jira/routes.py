"""
Jira Webhook Routes
Main route handler for Jira webhooks.
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import json
import uuid
from datetime import datetime, timezone
import structlog

from core.database import get_session as get_db_session
from core.database.models import WebhookEventDB
from core.webhook_configs import JIRA_WEBHOOK
from api.webhooks.jira.validation import validate_jira_webhook
from api.webhooks.jira.utils import (
    verify_jira_signature,
    send_jira_immediate_response,
    match_jira_command,
    create_jira_task,
    is_assignee_changed_to_ai,
)

logger = structlog.get_logger()
router = APIRouter()


@router.post("/jira")
async def jira_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Jira webhook endpoint."""
    issue_key = None
    task_id = None
    
    try:
        try:
            body = await request.body()
        except Exception as e:
            logger.error("jira_webhook_body_read_failed", error=str(e))
            raise HTTPException(status_code=400, detail=f"Failed to read request body: {str(e)}")
        
        try:
            await verify_jira_signature(request, body)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("jira_signature_verification_error", error=str(e))
            raise HTTPException(status_code=401, detail=f"Signature verification failed: {str(e)}")
        
        try:
            payload = json.loads(body.decode())
            payload["provider"] = "jira"
        except json.JSONDecodeError as e:
            logger.error("jira_payload_parse_error", error=str(e))
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")
        except Exception as e:
            logger.error("jira_payload_decode_error", error=str(e))
            raise HTTPException(status_code=400, detail=f"Failed to decode payload: {str(e)}")
        
        issue_key = payload.get("issue", {}).get("key", "unknown")
        event_type = payload.get("webhookEvent", "unknown")
        
        logger.info("jira_webhook_received", event_type=event_type, issue_key=issue_key, payload_keys=list(payload.keys()))
        
        try:
            validation_result = validate_jira_webhook(payload)
            
            if not validation_result.is_valid:
                logger.info(
                    "jira_webhook_rejected_by_validation",
                    event_type=event_type,
                    issue_key=issue_key,
                    reason=validation_result.error_message
                )
                return {"status": "rejected", "actions": 0, "message": "Does not meet activation rules"}
        except Exception as e:
            logger.error("jira_webhook_validation_error", error=str(e), event_type=event_type)
        
        if not is_assignee_changed_to_ai(payload, event_type):
            logger.info(
                "jira_webhook_skipped_no_ai_assignee",
                event_type=event_type,
                issue_key=issue_key,
                message="Assignee not changed to AI Agent, skipping webhook processing"
            )
            return {
                "status": "skipped",
                "message": "Assignee not changed to AI Agent",
                "issue_key": issue_key
            }
        
        try:
            command = match_jira_command(payload, event_type)
            if not command:
                logger.warning("jira_no_command_matched", event_type=event_type, issue_key=issue_key, payload_sample=str(payload)[:500])
                return {"status": "received", "actions": 0, "message": "No command matched - requires assignee change to AI agent or @agent prefix"}
        except Exception as e:
            logger.error("jira_command_matching_error", error=str(e), issue_key=issue_key)
            raise HTTPException(status_code=500, detail=f"Command matching failed: {str(e)}")
        
        logger.info("jira_command_matched", command=command.name, event_type=event_type, issue_key=issue_key)
        
        immediate_response_sent = False
        try:
            immediate_response_sent = await send_jira_immediate_response(payload, command, event_type)
        except Exception as e:
            logger.error("jira_immediate_response_error", error=str(e), issue_key=issue_key, command=command.name)
        
        try:
            task_id = await create_jira_task(command, payload, db)
            logger.info("jira_task_created_success", task_id=task_id, issue_key=issue_key)
        except Exception as e:
            logger.error("jira_task_creation_failed", error=str(e), error_type=type(e).__name__, issue_key=issue_key, command=command.name)
            raise HTTPException(status_code=500, detail=f"Task creation failed: {str(e)}")
        
        try:
            event_id = f"evt-{uuid.uuid4().hex[:12]}"
            event_db = WebhookEventDB(
                event_id=event_id,
                webhook_id=JIRA_WEBHOOK.name,
                provider="jira",
                event_type=event_type,
                payload_json=json.dumps(payload),
                matched_command=command.name,
                task_id=task_id,
                response_sent=immediate_response_sent,
                created_at=datetime.now(timezone.utc)
            )
            db.add(event_db)
            await db.commit()
            logger.info("jira_event_logged", event_id=event_id, task_id=task_id, issue_key=issue_key)
        except Exception as e:
            logger.error("jira_event_logging_failed", error=str(e), task_id=task_id, issue_key=issue_key)
        
        logger.info("jira_webhook_processed", task_id=task_id, command=command.name, event_type=event_type, issue_key=issue_key)
        
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
            "jira_webhook_error",
            error=str(e),
            error_type=type(e).__name__,
            issue_key=issue_key,
            task_id=task_id,
            exc_info=True
        )
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "issue_key": issue_key
        }
