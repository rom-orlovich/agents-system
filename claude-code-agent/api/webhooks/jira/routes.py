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
    post_jira_task_comment,
    send_slack_notification,
)

logger = structlog.get_logger()
router = APIRouter()

COMPLETION_HANDLER = "api.webhooks.jira.routes.handle_jira_task_completion"


async def handle_jira_task_completion(
    payload: dict,
    message: str,
    success: bool,
    cost_usd: float = 0.0,
    task_id: str = None,
    command: str = None,
    result: str = None,
    error: str = None
) -> bool:
    """
    Handle Jira task completion callback.
    
    Called by task worker when task completes.
    
    Actions:
    1. Format message (clean error message for Jira)
    2. Post comment to Jira ticket with task result
    3. Send Slack notification (if enabled)
    
    Returns:
        True if comment posted successfully, False otherwise
    """
    from api.webhooks.jira.utils import extract_pr_url
    from api.webhooks.jira.models import JiraTaskCompletionPayload
    
    jira_payload = JiraTaskCompletionPayload(**payload)
    
    formatted_message = error if not success and error else message
    pr_url = extract_pr_url(result or message)
    
    ticket_key = jira_payload.get_ticket_key()
    user_request = jira_payload.get_user_request()
    
    comment_posted = await post_jira_task_comment(
        issue=jira_payload.issue,
        message=formatted_message,
        success=success,
        cost_usd=cost_usd,
        pr_url=pr_url
    )
    
    routing_metadata = {}
    if jira_payload.routing:
        routing_metadata = {"routing": jira_payload.routing}
    elif jira_payload.source_metadata:
        source_metadata = jira_payload.source_metadata
        if isinstance(source_metadata, dict):
            routing_metadata = {"routing": source_metadata.get("routing", {})}
        elif isinstance(source_metadata, str):
            import json
            try:
                source_metadata = json.loads(source_metadata)
                routing_metadata = {"routing": source_metadata.get("routing", {})}
            except:
                pass
    
    await send_slack_notification(
        task_id=task_id,
        webhook_source="jira",
        command=command,
        success=success,
        result=result,
        error=error,
        pr_url=pr_url,
        payload=routing_metadata if routing_metadata else None,
        cost_usd=cost_usd,
        user_request=user_request,
        ticket_key=ticket_key
    )
    
    return comment_posted


@router.post("/jira")
async def jira_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Jira webhook endpoint.
    
    Flow:
    1. Get webhook event
    2. Validate webhook
    3. Validate command
    4. Send immediate response (comment)
    5. Create task (with completion handler registered: handle_jira_task_completion)
    6. Put task in queue
    7. Log event
    8. Send back HTTP response
    
    After task completes (task worker calls handle_jira_task_completion):
    - handle_jira_task_completion() posts comment to Jira ticket
    - handle_jira_task_completion() sends Slack notification (if enabled)
    - Task worker updates conversation with result
    """
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
        
        try:
            command = await match_jira_command(payload, event_type)
            if not command:
                logger.warning("jira_no_command_matched", event_type=event_type, issue_key=issue_key, payload_sample=str(payload)[:500])
                return {"status": "received", "actions": 0, "message": "No command matched - requires assignee change to AI agent or @agent prefix"}
        except Exception as e:
            logger.error("jira_command_matching_error", error=str(e), issue_key=issue_key)
            raise HTTPException(status_code=500, detail=f"Command matching failed: {str(e)}")
        
        logger.info("jira_command_matched", command=command.name, event_type=event_type, issue_key=issue_key)
        
        immediate_response_sent = await send_jira_immediate_response(payload, command, event_type)
        
        task_id = await create_jira_task(command, payload, db, completion_handler=COMPLETION_HANDLER)
        logger.info("jira_task_created_success", task_id=task_id, issue_key=issue_key)
        
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
        
        logger.info(
            "jira_completion_handler_registered",
            task_id=task_id,
            handler=COMPLETION_HANDLER,
            message="Completion handler will be called by task worker when task completes"
        )
        
        logger.info("jira_webhook_processed", task_id=task_id, command=command.name, event_type=event_type, issue_key=issue_key)
        
        return {
            "status": "processed",
            "task_id": task_id,
            "command": command.name,
            "immediate_response_sent": immediate_response_sent,
            "completion_handler": COMPLETION_HANDLER
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
