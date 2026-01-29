from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import json
import uuid
from datetime import datetime, timezone
import structlog
from pathlib import Path

from core.database import get_session as get_db_session
from core.database.models import WebhookEventDB
from core.webhook_configs import JIRA_WEBHOOK
from core.task_logger import TaskLogger
from core.config import settings
from api.webhooks.jira.utils import (
    send_slack_notification,
    extract_pr_url,
)
from api.webhooks.jira.handlers import JiraResponseHandler, JiraWebhookHandler
from api.webhooks.jira.metadata import extract_jira_routing
from api.webhooks.jira.models import JiraTaskCompletionPayload
from core.database.redis_client import redis_client
from api.webhooks.jira.constants import (
    PROVIDER_NAME,
    FIELD_WEBHOOK_EVENT,
    FIELD_ISSUE,
    FIELD_KEY,
    STATUS_PROCESSED,
    STATUS_REJECTED,
    STATUS_RECEIVED,
    STATUS_ERROR,
    MESSAGE_DOES_NOT_MEET_RULES,
    MESSAGE_NO_COMMAND_MATCHED,
    DEFAULT_EVENT_TYPE,
    DEFAULT_ISSUE_KEY,
)

from api.webhooks.common.utils import load_webhook_config_from_yaml

logger = structlog.get_logger()
router = APIRouter()

JIRA_CONFIG = load_webhook_config_from_yaml(Path(__file__).parent / "config.yaml")
COMPLETION_HANDLER = "api.webhooks.jira.routes.handle_jira_task_completion"
webhook_handler = JiraWebhookHandler(JIRA_CONFIG)


async def handle_jira_task_completion(
    payload: dict,
    message: str,
    success: bool,
    cost_usd: float = 0.0,
    task_id: str = None,
    command: str = None,
    result: str | list[str] | None = None,
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
    if isinstance(result, list):
        result = "\n".join(str(item) for item in result)
    elif result and not isinstance(result, str):
        result = str(result)

    jira_payload = JiraTaskCompletionPayload(**payload)
    
    formatted_message = error if not success and error else message
    pr_url = extract_pr_url(result or message)
    
    # Add PR URL and cost to formatted message
    if pr_url and success:
        formatted_message = f"{formatted_message}\n\n🔗 *Pull Request:* {pr_url}"
    
    max_length = 8000
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
    
    routing = extract_jira_routing(payload)
    
    # Post using handler
    handler = JiraResponseHandler()
    try:
        comment_posted, response = await handler.post_response(routing, formatted_message)
        
        # Track comment ID in Redis if available
        if comment_posted and response and isinstance(response, dict):
            comment_id = response.get("id")
            if comment_id:
                try:
                    key = f"jira:posted_comment:{comment_id}"
                    await redis_client._client.setex(key, 3600, "1")
                    logger.debug("jira_comment_id_tracked", comment_id=comment_id)
                except Exception as e:
                    logger.warning("jira_comment_id_tracking_failed", comment_id=comment_id, error=str(e))
    except Exception as e:
        logger.error("jira_handler_post_failed", error=str(e), task_id=task_id)
        comment_posted = False
    
    ticket_key = jira_payload.get_ticket_key()
    user_request = jira_payload.get_user_request()
    
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
        webhook_source=PROVIDER_NAME,
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
            await webhook_handler.verify_signature(request, body)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("jira_signature_verification_error", error=str(e))
            raise HTTPException(status_code=401, detail=f"Signature verification failed: {str(e)}")

        if JIRA_CONFIG is None:
            logger.error("jira_webhook_config_not_loaded")
            raise HTTPException(
                status_code=503,
                detail="Jira webhook configuration not loaded"
            )

        try:
            payload = webhook_handler.parse_payload(body, PROVIDER_NAME)
        except json.JSONDecodeError as e:
            logger.error("jira_payload_parse_error", error=str(e))
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")
        except Exception as e:
            logger.error("jira_payload_decode_error", error=str(e))
            raise HTTPException(status_code=400, detail=f"Failed to decode payload: {str(e)}")
        
        issue_key = payload.get(FIELD_ISSUE, {}).get(FIELD_KEY, DEFAULT_ISSUE_KEY)
        event_type = payload.get(FIELD_WEBHOOK_EVENT, DEFAULT_EVENT_TYPE)

        logger.info("jira_webhook_received", event_type=event_type, issue_key=issue_key, payload_keys=list(payload.keys()))

        webhook_events = []
        webhook_events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": "received",
            "event_type": event_type,
            "issue_key": issue_key
        })

        try:
            validation_result = await webhook_handler.validate_webhook(payload)

            webhook_events.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "stage": "validation",
                "status": "passed" if validation_result.is_valid else "failed",
                "reason": validation_result.error_message if not validation_result.is_valid else None
            })

            if not validation_result.is_valid:
                logger.info(
                    "jira_webhook_rejected_by_validation",
                    event_type=event_type,
                    issue_key=issue_key,
                    reason=validation_result.error_message
                )
                return {"status": STATUS_REJECTED, "actions": 0, "message": MESSAGE_DOES_NOT_MEET_RULES}
        except Exception as e:
            logger.error("jira_webhook_validation_error", error=str(e), event_type=event_type)
        
        try:
            command = await webhook_handler.match_command(payload, event_type)

            webhook_events.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "stage": "command_matching",
                "command": command.name if command else None,
                "matched": bool(command)
            })

            if not command:
                logger.warning("jira_no_command_matched", event_type=event_type, issue_key=issue_key, payload_sample=str(payload)[:500])
                return {"status": STATUS_RECEIVED, "actions": 0, "message": MESSAGE_NO_COMMAND_MATCHED}
        except Exception as e:
            logger.error("jira_command_matching_error", error=str(e), issue_key=issue_key)
            raise HTTPException(status_code=500, detail=f"Command matching failed: {str(e)}")

        logger.info("jira_command_matched", command=command.name, event_type=event_type, issue_key=issue_key)

        immediate_response_sent = await webhook_handler.send_immediate_response(payload, command, event_type)

        webhook_events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": "immediate_response",
            "action": command.immediate_response if hasattr(command, 'immediate_response') else None,
            "success": immediate_response_sent
        })

        actual_task_id = await webhook_handler.create_task(command, payload, db, COMPLETION_HANDLER)
        logger.info("jira_task_created_success", task_id=actual_task_id, issue_key=issue_key)

        webhook_events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": "task_created",
            "task_id": actual_task_id,
            "agent": command.target_agent if hasattr(command, 'target_agent') else None,
            "command": command.name
        })

        if settings.task_logs_enabled:
            try:
                task_logger = TaskLogger(actual_task_id, settings.task_logs_dir)

                for event in webhook_events:
                    task_logger.append_webhook_event(event)

                task_logger.write_metadata({
                    "task_id": actual_task_id,
                    "source": "webhook",
                    "provider": PROVIDER_NAME,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "status": "queued",
                    "assigned_agent": command.target_agent if hasattr(command, 'target_agent') else None,
                    "model": None
                })

                task_logger.write_input({
                    "message": f"Jira {event_type}: {issue_key}",
                    "source_metadata": {
                        "provider": PROVIDER_NAME,
                        "event_type": event_type,
                        "issue_key": issue_key,
                        "command": command.name
                    }
                })

                webhook_events.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "stage": "queue_push",
                    "task_id": actual_task_id,
                    "status": "queued"
                })
                task_logger.append_webhook_event(webhook_events[-1])

                logger.info("jira_webhook_logging_complete", task_id=actual_task_id, events_logged=len(webhook_events))
            except Exception as e:
                logger.warning("jira_webhook_logging_failed", task_id=actual_task_id, error=str(e))

        task_id = actual_task_id
        
        try:
            event_id = f"evt-{uuid.uuid4().hex[:12]}"
            event_db = WebhookEventDB(
                event_id=event_id,
                webhook_id=JIRA_WEBHOOK.name,
                provider=PROVIDER_NAME,
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
            "status": STATUS_PROCESSED,
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
            "status": STATUS_ERROR,
            "error": str(e),
            "error_type": type(e).__name__,
            "issue_key": issue_key
        }
